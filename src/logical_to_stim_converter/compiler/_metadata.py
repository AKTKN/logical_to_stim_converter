"""Recover final indices from the assembled circuit, after stimflow reindexing."""

import json
from collections import defaultdict
from dataclasses import replace

import stim

from ..core.compiler_context import (
    CompilerContext,
    DetectorInfo,
    MeasurementInfo,
    MeasurementKey,
    ObservableInfo,
    TimeLayer,
)
from ..core.module_fragment import ModuleFragment
from ._parallel import moments

ANNOTATIONS = {"QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS"}


def extract_metadata(
    circuit: stim.Circuit, context: CompilerContext, fragments: tuple[ModuleFragment, ...], backend
):
    final_coords = circuit.get_final_qubit_coordinates()
    position_to_index = {complex(*coords[:2]): i for i, coords in final_coords.items()}
    physical_map = {site: position_to_index[pos] for site, pos in context.site_positions.items()}
    index_to_site = {i: site for site, i in physical_map.items()}
    logical_for_block = {block: logical for logical, block in context.logical_to_block.items()}
    by_module = {f.module_id: f for f in fragments}
    measurements = []
    detectors = []
    observables = defaultdict(set)
    rounds = defaultdict(int)
    layers = []
    active = set()
    preparation_syndromes = defaultdict(list)
    detector_coords = circuit.get_detector_coordinates()
    causal_graph = {block: {block} for block in context.blocks}
    for layer_index, instructions in enumerate(moments(circuit)):
        operation_by_block = {}
        used = set()
        retiring = set()
        for instruction in instructions:
            if instruction.name not in ANNOTATIONS:
                fragment = by_module[instruction.tag]
                for block_id in fragment.block_ids:
                    operation_by_block[block_id] = fragment.module_id
                used.update(t.value for t in instruction.targets_copy())
                if fragment.operation_type == "LogicalInit":
                    active.update(fragment.block_ids)
                if fragment.operation_type == "LogicalMeasure":
                    retiring.update(fragment.block_ids)
                if fragment.operation_type == "TransversalCNOT":
                    c, t = fragment.block_ids
                    connected = causal_graph[c] | causal_graph[t]
                    for block in connected:
                        causal_graph[block] = set(connected)
            if stim.gate_data(instruction.name).produces_measurements:
                for target in instruction.targets_copy():
                    block_id, local_id = index_to_site[target.value]
                    block = context.blocks[block_id]
                    logical_id = logical_for_block[block_id]
                    basis = "X" if instruction.name == "MX" else "Z"
                    if local_id in block.layout.ancilla_ids:
                        kind = "syndrome"
                        round_index = rounds[(block_id, local_id)]
                        rounds[(block_id, local_id)] += 1
                    else:
                        kind, round_index = "readout", None
                    key = MeasurementKey(block_id, local_id, kind, round_index)
                    measurements.append(
                        MeasurementInfo(
                            key, len(measurements), logical_id, basis, instruction.tag, layer_index
                        )
                    )
                    if (
                        kind == "syndrome"
                        and round_index == 0
                        and basis != context.prepared_basis[logical_id]
                    ):
                        preparation_syndromes[logical_id].append(key)
            if instruction.name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
                indices = {len(measurements) + t.value for t in instruction.targets_copy()}
                if any(i < 0 or i >= len(measurements) for i in indices):
                    raise ValueError("Invalid measurement record in compiled annotation")
                if instruction.name == "DETECTOR":
                    coords = tuple(detector_coords[len(detectors)])
                    if not instruction.tag.startswith("check:"):
                        raise ValueError("Detector has no validated semantic check anchor")
                    block_id, check_id = json.loads(instruction.tag.removeprefix("check:"))
                    if block_id not in context.blocks:
                        raise ValueError("Unknown detector anchor block")
                    context.blocks[block_id].layout.check_for_ancilla(check_id)
                    keys = tuple(measurements[i].key for i in sorted(indices))
                    support = tuple(sorted({key.block_id for key in keys}))
                    if block_id not in support or not set(support) <= causal_graph[block_id]:
                        raise ValueError("Detector records have invalid cross-block provenance")
                    detectors.append(
                        DetectorInfo(
                            len(detectors),
                            coords,
                            tuple(sorted(indices)),
                            keys,
                            block_id,
                            check_id,
                            support,
                        )
                    )
                else:
                    observables[int(instruction.gate_args_copy()[0])] ^= indices
        layers.append(
            TimeLayer(layer_index, tuple(sorted(active)), operation_by_block, frozenset(used))
        )
        active -= retiring
    observable_info = []
    for logical, index in sorted(context.observable_ids.items(), key=lambda item: item[1]):
        block_id = context.logical_to_block[logical]
        if index not in observables:
            raise ValueError(f"Missing logical observable for {logical!r}")
        frame = context.readout_frames[logical]
        correction = frame.x if context.measurement_bases[logical] == "Z" else frame.z
        block = context.blocks[block_id]
        representative = backend.logical_pauli(
            block,
            logical,
            context.measurement_bases[logical],
            context.readout_orientations[logical],
        )
        positions = {block.position(q): q for q in block.layout.data_ids}
        readout = {
            m.key.local_id: m.index
            for m in measurements
            if m.key.block_id == block_id and m.key.kind == "readout"
        }
        readout_indices = tuple(sorted(readout[positions[q]] for q in representative))
        observable_info.append(
            ObservableInfo(
                index,
                logical,
                block_id,
                context.measurement_bases[logical],
                tuple(sorted(observables[index])),
                readout_indices,
                correction,
                context.expected_outputs[logical],
            )
        )
    context.measurements = tuple(measurements)
    context.detectors = tuple(detectors)
    context.layers = tuple(layers)
    context.frames = {
        logical: replace(
            context.frames[logical], preparation_syndromes=tuple(preparation_syndromes[logical])
        )
        for logical in context.logical_to_block
    }
    return physical_map, tuple(observable_info)


def finalize_observables(circuit, context, observables):
    """Include symbolic frame parity in each observable, with a signed Stim proof.

    stimflow constructs the physical transport observable. Classical frame
    interpretation may add measured check parities. Constants stay in metadata:
    they change a reported bit, not detector-error-model fault correlations.
    """
    key_to_index = {record.key: record.index for record in context.measurements}
    result = []
    for observable in observables:
        desired = set(observable.readout_measurement_indices)
        desired.symmetric_difference_update(
            key_to_index[key] for key in observable.frame_correction.terms
        )
        difference = desired ^ set(observable.measurement_indices)
        if difference:
            circuit.append(
                "OBSERVABLE_INCLUDE",
                [stim.target_rec(index - circuit.num_measurements) for index in sorted(difference)],
                observable.index,
                tag="logical-frame",
            )
        expected = observable.expected_value ^ observable.frame_correction.constant
        identity = stim.PauliString(circuit.num_qubits)
        output = identity.copy()
        if expected:
            output.sign = -1
        relation = stim.Flow(input=identity, output=output, measurements=sorted(desired))
        if not circuit.has_flow(relation):
            raise ValueError("Logical readout/frame parity does not realize the intended state")
        result.append(replace(observable, measurement_indices=tuple(sorted(desired))))
    circuit.detector_error_model()
    return tuple(result)
