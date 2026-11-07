"""Independent consistency checks for canonical global mappings and causal edges."""

import json
from collections import defaultdict

import stim

from ..core.compiler_context import MeasurementKey
from ._metadata import detector_boundary_candidates, ordered_stages
from ._parallel import moments


def validate_metadata(compiled):
    circuit = compiled.ideal_circuit
    measurements = compiled.measurements
    detectors = compiled.detectors
    fragments = {f.module_id: f for f in compiled.fragments}
    if (len(measurements) != circuit.num_measurements
            or tuple(m.index for m in measurements) != tuple(range(len(measurements)))
            or len({m.key for m in measurements}) != len(measurements)):
        raise ValueError("Invalid global measurement indices or semantic keys")
    if (len(detectors) != circuit.num_detectors
            or tuple(d.index for d in detectors) != tuple(range(len(detectors)))):
        raise ValueError("Invalid global detector indices")
    sites = {i: site for site, i in compiled.physical_qubit_map.items()}
    blocks = {b.block_id: b for b in compiled._compiler.blocks}
    coords = circuit.get_detector_coordinates()
    rounds = defaultdict(int)
    cursor = detector_index = 0
    observables = defaultdict(set)
    for layer_index, instructions in enumerate(moments(circuit)):
        for inst in instructions:
            if stim.gate_data(inst.name).produces_measurements:
                fragment = fragments[inst.tag]
                for target in inst.targets_copy():
                    bid, local = sites[target.value]
                    is_check = local in blocks[bid].layout.ancilla_ids
                    round_index = rounds[(bid, local)] if is_check else None
                    if is_check:
                        rounds[(bid, local)] += 1
                    key = MeasurementKey(bid, local, "syndrome" if is_check else "readout",
                                         round_index)
                    m = measurements[cursor]
                    if (m.key != key or m.module_id != inst.tag or m.stage_id != fragment.stage
                            or m.time_layer != layer_index
                            or m.basis != ("X" if inst.name == "MX" else "Z")
                            or m.logical_id != fragment.logical_ids[fragment.block_ids.index(bid)]):
                        raise ValueError("Measurement physical/stage attribution disagrees")
                    cursor += 1
            if inst.name not in ("DETECTOR", "OBSERVABLE_INCLUDE"):
                continue
            parity = set()
            for t in inst.targets_copy():
                i = cursor + t.value
                if not t.is_measurement_record_target or not 0 <= i < cursor:
                    raise ValueError("Invalid global annotation record index")
                parity.symmetric_difference_update((i,))
            if inst.name == "OBSERVABLE_INCLUDE":
                observables[int(inst.gate_args_copy()[0])] ^= parity
                continue
            d = detectors[detector_index]
            indices = tuple(sorted(parity))
            keys = tuple(measurements[i].key for i in indices)
            stages = ordered_stages(measurements[i].stage_id for i in indices)
            if d.measurement_indices != indices or d.measurement_keys != keys:
                raise ValueError("Detector global record parity disagrees")
            anchor = json.loads(inst.tag.removeprefix("check:"))
            if (anchor != [d.block_id, d.check_id, d.anchor_module_id]
                    or d.stage_id != fragments[d.anchor_module_id].stage
                    or d.source_stage_ids != stages
                    or d.crosses_decoder_boundary != (len(stages) > 1)):
                raise ValueError("Detector anchor/stage attribution disagrees")
            if (d.supporting_block_ids != tuple(sorted({k.block_id for k in keys}))
                    or d.coordinates != tuple(coords[detector_index])):
                raise ValueError("Detector physical provenance disagrees")
            f = fragments[d.anchor_module_id]
            orientation = f.orientations_before[f.block_ids.index(d.block_id)]
            check = blocks[d.block_id].layout.check_for_ancilla(d.check_id)
            basis = ("Z" if check.basis == "X" else "X") if orientation else check.basis
            support = set()
            for k in keys:
                layout = blocks[k.block_id].layout
                data = (layout.check_for_ancilla(k.local_id).support
                        if k.kind == "syndrome" else (k.local_id,))
                support.update((k.block_id, q) for q in data)
            if d.basis != basis or d.physical_support != tuple(sorted(support)):
                raise ValueError("Detector check basis or data support disagrees")
            detector_index += 1
    if (tuple(o.index for o in compiled.observables) != tuple(range(circuit.num_observables))
            or any(o.measurement_indices != tuple(sorted(observables[o.index]))
                   for o in compiled.observables)):
        raise ValueError("Observable global record parity disagrees")
    if compiled.detector_boundary_candidates != detector_boundary_candidates(detectors):
        raise ValueError("Detector boundary candidate provenance disagrees")
    validate_ancestry(compiled)


def validate_ancestry(compiled):
    fragments = {f.module_id: f for f in compiled.fragments}
    preps = {p.module_id: p for p in compiled.preparations}
    bells = {b.composite_id: b for b in compiled.bell_measurements}
    relocations = {r.composite_id: r for r in compiled.relocation_history}
    histories = {}
    seen_fragments, seen_bells = [], []
    for event in compiled.ancestry_events:
        if event.operation_type == "KnillEC":
            bell = bells[event.event_id]
            r = relocations[event.event_id]
            inputs = (bell.data_block_id, bell.first_resource_block_id, bell.output_block_id)
            outputs = (bell.output_block_id,)
            if (r.logical_id, r.source_block_id, r.output_block_id) != (
                    bell.logical_id, inputs[0], outputs[0]):
                raise ValueError("Relocation ancestry disagrees with Bell metadata")
            seen_bells.append(event.event_id)
        else:
            f = fragments[event.event_id]
            if event.operation_type != f.operation_type:
                raise ValueError("Ancestry operation disagrees with physical fragment")
            inputs = () if f.operation_type == "LogicalInit" else f.block_ids
            outputs = () if f.operation_type == "LogicalMeasure" else f.block_ids
            seen_fragments.append(f.module_id)
        if (event.input_block_ids, event.output_block_ids) != (inputs, outputs):
            raise ValueError("Ancestry edge disagrees with actual operands")
        if not inputs:
            prep = preps[event.event_id]
            f = fragments[event.event_id]
            if (prep.block_id, prep.logical_id, prep.stage_id) != (
                    f.block_id, f.logical_id, f.stage):
                raise ValueError("Preparation event identity disagrees")
            dependencies = (event.event_id,)
        else:
            if any(b not in histories for b in inputs):
                raise ValueError("Ancestry edge precedes its source preparation")
            dependencies = tuple(sorted({p for b in inputs for p in histories[b]}))
        if event.preparation_dependencies != dependencies:
            raise ValueError("Ancestry dependencies disagree with causal inputs")
        for b in outputs:
            histories[b] = dependencies
        if event.operation_type == "KnillEC":
            sources = tuple(k for p in dependencies
                            for k in preps[p].unresolved_frame.source_syndromes)
            gauges = tuple(k for p in dependencies for k in preps[p].gauge_measurements)
            if (bell.preparation_dependencies != dependencies
                    or bell.physical_output_frame.source_syndromes != sources
                    or bell.logical_output_frame.preparation_syndromes != gauges):
                raise ValueError("Bell preparation ancestry disagrees")
    if (seen_fragments != list(fragments) or seen_bells != list(bells)
            or histories != dict(compiled.block_preparation_dependencies)):
        raise ValueError("Incomplete or reordered preparation ancestry events")
    expected = {q: histories[b] for q, b in compiled.logical_to_block.items() if b in histories}
    if dict(compiled.preparation_dependencies) != expected:
        raise ValueError("Final logical preparation ancestry disagrees")
    for q, frame in compiled.frames.items():
        gauges = tuple(k for p in expected.get(q, ()) for k in preps[p].gauge_measurements)
        if frame.preparation_syndromes != gauges:
            raise ValueError("Final frame preparation ancestry disagrees")
