"""Recover final indices from the assembled circuit, after stimflow reindexing."""

from collections import defaultdict

import stim

from ..core.compiler_context import (
    CompilerContext,
    DetectorInfo,
    MeasurementInfo,
    MeasurementKey,
    ObservableInfo,
    PauliFrame,
    TimeLayer,
)
from ..core.module_fragment import ModuleFragment
from ._parallel import moments

ANNOTATIONS = {"QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS"}


def extract_metadata(
    circuit: stim.Circuit, context: CompilerContext, fragments: tuple[ModuleFragment, ...]
):
    final_coords = circuit.get_final_qubit_coordinates()
    position_to_index = {complex(*coords[:2]): i for i, coords in final_coords.items()}
    physical_map = {site: position_to_index[pos] for site, pos in context.site_positions.items()}
    index_to_site = {i: site for site, i in physical_map.items()}
    logical_for_block = {block: logical for logical, block in context.logical_to_block.items()}
    by_module = {f.module_id: f for f in fragments}
    checks_by_position = {
        b.position(c.ancilla): (b.block_id, c.check_id)
        for b in context.blocks.values()
        for c in b.layout.checks
    }
    measurements = []
    detectors = []
    observables = defaultdict(set)
    rounds = defaultdict(int)
    layers = []
    active = set()
    preparation_syndromes = defaultdict(list)
    detector_coords = circuit.get_detector_coordinates()
    for layer_index, instructions in enumerate(moments(circuit)):
        operation_by_block = {}
        used = set()
        retiring = set()
        for instruction in instructions:
            if instruction.name not in ANNOTATIONS:
                fragment = by_module[instruction.tag]
                operation_by_block[fragment.block_id] = fragment.module_id
                used.update(t.value for t in instruction.targets_copy())
                if fragment.operation_type == "LogicalInit":
                    active.add(fragment.block_id)
                if fragment.operation_type == "LogicalMeasure":
                    retiring.add(fragment.block_id)
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
                    block_id, check_id = checks_by_position[complex(*coords[:2])]
                    keys = tuple(measurements[i].key for i in sorted(indices))
                    if any(key.block_id != block_id for key in keys):
                        raise ValueError("Detector connects records from independent blocks")
                    detectors.append(
                        DetectorInfo(
                            len(detectors), coords, tuple(sorted(indices)), keys, block_id, check_id
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
        observable_info.append(
            ObservableInfo(
                index,
                logical,
                block_id,
                context.prepared_basis[logical],
                tuple(sorted(observables[index])),
            )
        )
    context.measurements = tuple(measurements)
    context.detectors = tuple(detectors)
    context.layers = tuple(layers)
    context.frames = {
        logical: PauliFrame(preparation_syndromes=tuple(preparation_syndromes[logical]))
        for logical in context.logical_to_block
    }
    return physical_map, tuple(observable_info)
