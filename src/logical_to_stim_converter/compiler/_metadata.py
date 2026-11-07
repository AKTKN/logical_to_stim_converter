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
from ..core.protocol import CheckHistory, LogicalReadout, PreparationInfo, SuppressedDetector
from ._parallel import moments

ANNOTATIONS = {"QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS"}


def extract_metadata(
    circuit: stim.Circuit, context: CompilerContext, fragments: tuple[ModuleFragment, ...], backend
):
    final_coords = circuit.get_final_qubit_coordinates()
    position_to_index = {complex(*coords[:2]): i for i, coords in final_coords.items()}
    physical_map = {site: position_to_index[pos] for site, pos in context.site_positions.items()}
    index_to_site = {i: site for site, i in physical_map.items()}
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
                    fragment = by_module[instruction.tag]
                    logical_id = fragment.logical_ids[fragment.block_ids.index(block_id)]
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
                            key, len(measurements), logical_id, basis, instruction.tag, layer_index,
                            fragment.stage,
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
                    block_id, check_id, module_id = json.loads(
                        instruction.tag.removeprefix("check:"))
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
                            by_module[module_id].stage,
                            ordered_stages(measurements[i].stage_id for i in indices),
                            len({measurements[i].stage_id for i in indices}) > 1,
                            module_id,
                        )
                    )
                else:
                    observables[int(instruction.gate_args_copy()[0])] ^= indices
        layers.append(
            TimeLayer(layer_index, tuple(sorted(active)), operation_by_block, frozenset(used))
        )
        active -= retiring
    observable_info = []
    for logical, index in sorted(context.output_ids.items(), key=lambda item: item[1]):
        block_id = context.readout_blocks[logical]
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
            context.frames[logical], preparation_syndromes=tuple(dict.fromkeys(
                context.frames[logical].preparation_syndromes
                + tuple(preparation_syndromes[logical])))
        )
        for logical in context.logical_to_block
    }
    return physical_map, tuple(observable_info)


def protocol_metadata(context, fragments, backend):
    preparations, readouts = [], []
    for f in fragments:
        if f.operation_type not in ("LogicalInit", "LogicalMeasure"):
            continue
        block = context.blocks[f.block_id]
        orientation = f.orientations_before[0]
        data = block.layout.data_ids
        at = {block.position(q): q for q in data}
        logical_supports = [tuple(at[q] for q in backend.logical_pauli(
            block, f.logical_id, axis, orientation)) for axis in "XZ"]
        records = [m for m in context.measurements if m.module_id == f.module_id]
        checks = tuple(CheckHistory(
            c.check_id, ("Z" if c.basis == "X" else "X") if orientation else c.basis,
            c.support, tuple(m.key for m in records if m.key.local_id == c.ancilla))
            for c in block.layout.checks)
        if f.operation_type == "LogicalInit":
            preparations.append(PreparationInfo(
                f.module_id, f.block_id, f.logical_id, f.stage,
                context.prepared_basis[f.logical_id], orientation, data, checks,
                *logical_supports))
        else:
            from ..core.compiler_context import ParityExpression

            basis = records[0].basis
            by_local = {m.key.local_id: m.key for m in records}
            readouts.append(LogicalReadout(
                f.module_id, f.logical_id, f.block_id, basis, orientation,
                f.readout_mode, f.stage, tuple(by_local[q] for q in data),
                ParityExpression(tuple(by_local[q] for q in logical_supports[basis == "Z"])),
                checks))
    return tuple(preparations), tuple(readouts)


def ordered_stages(stages):
    """Stable source ordering, including the ordinary un-staged region."""
    return tuple(sorted(set(stages), key=lambda s: (s is not None, s or "")))


def stage_separated_circuit(circuit, detectors):
    """Derive the legacy annotation view without changing physical instructions.

    The returned circuit has local detector numbering. The retained global IDs
    are returned separately. No independent stage DEM or fault slicing is implied.
    """
    result = stim.Circuit()
    retained = []
    detector_index = 0
    for inst in circuit:
        if inst.name == "DETECTOR":
            if not detectors[detector_index].crosses_decoder_boundary:
                result.append(inst)
                retained.append(detector_index)
            detector_index += 1
        else:
            result.append(inst)
    return result, tuple(retained)


def detector_boundary_candidates(detectors):
    return tuple(SuppressedDetector(d.index, d.measurement_indices, d.source_stage_ids)
                 for d in detectors if d.crosses_decoder_boundary)


def separate_detector_regions(circuit, fragments):
    """M5 compatibility helper: explicitly derive a view; never used by compile."""
    stages = {f.module_id: f.stage for f in fragments}
    records = []
    detectors = []
    for inst in circuit:
        if stim.gate_data(inst.name).produces_measurements:
            records.extend([stages[inst.tag]] * inst.num_measurements)
        if inst.name == "DETECTOR":
            indices = tuple(sorted({len(records) + t.value for t in inst.targets_copy()}))
            source_stages = ordered_stages(records[i] for i in indices)
            detectors.append(DetectorInfo(
                len(detectors), (), indices, (), "", "", source_stage_ids=source_stages,
                crosses_decoder_boundary=len(source_stages) > 1))
    view, _ = stage_separated_circuit(circuit, detectors)
    return view, detector_boundary_candidates(detectors)


def validate_detector_regions(detectors, measurements):
    for detector in detectors:
        stages = {measurements[i].stage_id for i in detector.measurement_indices}
        if len(stages) > 1 or (stages and detector.stage_id not in stages):
            raise ValueError("Detector crosses an explicit stage boundary")


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
