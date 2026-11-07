"""Small public-API adapter for simultaneous, disjoint physical chunks.

StimCircuitLoom requires matching instruction sequences. Mixed-basis reset/readout
chunks do not satisfy that contract. Here only physical layers are aligned; flow
composition and detector construction remain entirely in stimflow.
"""

from collections.abc import Iterable

import stim
import stimflow as sf

from ..core.module_fragment import ModuleFragment


def moments(circuit: stim.Circuit) -> list[list[stim.CircuitInstruction]]:
    result = [[]]
    for instruction in circuit:
        if isinstance(instruction, stim.CircuitRepeatBlock):
            raise ValueError("Layer assembly expects expanded physical chunks")
        if instruction.name == "TICK":
            result.append([])
        else:
            result[-1].append(instruction)
    return result


def parallel_chunk(
    parts: Iterable[tuple[sf.Chunk, ModuleFragment]],
    interface: sf.ChunkInterface,
    *,
    extra_flows=(),
    managed_ports=frozenset(),
    measurement_flows=(),
    discarded_readout_ports=(),
) -> sf.Chunk:
    parts = list(parts)
    occupied: set[complex] = set()
    for chunk, _ in parts:
        if occupied & chunk.q2i.keys():
            raise ValueError("Parallel chunks overlap physical sites")
        occupied.update(chunk.q2i)
    # Pass through only untouched blocks, never a missing flow on an operated block.
    passive = [
        p
        for p in interface.ports | interface.discards
        if not occupied & p.keys() and p not in managed_ports
    ]
    coords = (
        occupied
        | {q for p in passive for q in p.keys()}
        | {q for flow in extra_flows for p in (flow.start, flow.end) for q in p.keys()}
        | {q for pair in measurement_flows for p in pair for q in p.keys()}
    )
    q2i = {q: i for i, q in enumerate(sf.sorted_complex(coords))}
    layers = [moments(c.circuit) for c, _ in parts]
    measurement_maps: list[list[int]] = [[] for _ in parts]
    out = stim.Circuit()
    measurement_count = 0
    for layer_index in range(max(map(len, layers))):
        used: set[int] = set()
        for part_index, (chunk, fragment) in enumerate(parts):
            if layer_index >= len(layers[part_index]):
                continue
            i2q = {i: q for q, i in chunk.q2i.items()}
            for instruction in layers[part_index][layer_index]:
                if instruction.name == "QUBIT_COORDS":
                    continue
                if instruction.name not in (
                    "R",
                    "RX",
                    "RY",
                    "M",
                    "MX",
                    "MY",
                    "CX",
                    "H",
                    "X",
                    "Y",
                    "Z",
                ):
                    raise ValueError(f"Unexpected memory-chunk instruction {instruction.name}")
                targets = [q2i[i2q[t.value]] for t in instruction.targets_copy()]
                if len(set(targets)) != len(targets) or used & set(targets):
                    raise ValueError("A physical qubit is used twice in a composed time layer")
                used.update(targets)
                if stim.gate_data(instruction.name).produces_measurements:
                    measurement_maps[part_index].extend(
                        range(measurement_count, measurement_count + len(targets))
                    )
                    measurement_count += len(targets)
                out.append(
                    instruction.name, targets, instruction.gate_args_copy(), tag=fragment.module_id
                )
        if layer_index < max(map(len, layers)) - 1:
            out.append("TICK")
    flows = list(extra_flows)
    for start, end in measurement_flows:
        pin = start.to_stim_pauli_string(q2i)
        pout = end.to_stim_pauli_string(q2i)
        relation = stim.Flow(input=pin, output=pout)
        records = out.solve_flow_measurements([relation])[0]
        if records is None:
            raise ValueError("Conditional logical flow is not realized by physical readout")
        relation = stim.Flow(input=pin, output=pout, measurements=records)
        negative = not out.has_flow(relation)
        if negative:
            pout.sign *= -1
            if not out.has_flow(stim.Flow(input=pin, output=pout, measurements=records)):
                raise ValueError("Conditional readout has no signed physical flow")
        flows.append(sf.Flow(start=start, end=end, measurement_indices=records,
                             sign=negative, center=None))
    for (chunk, _), mapping in zip(parts, measurement_maps, strict=True):
        for flow in chunk.flows:
            flows.append(
                flow.with_edits(measurement_indices=[mapping[m] for m in flow.measurement_indices])
            )
    # A pass-through has no new check location. Inferring its support centroid
    # would cause stimflow to average and move a boundary detector's coordinates.
    flows.extend(sf.Flow(start=p, end=p, sign=False, center=None) for p in passive)
    result = sf.Chunk(
        out,
        q2i=q2i,
        flows=flows,
        discarded_inputs=[p for c, _ in parts for p in c.discarded_inputs]
        + list(discarded_readout_ports),
        discarded_outputs=[p for c, _ in parts for p in c.discarded_outputs],
    )
    result.verify()
    return result
