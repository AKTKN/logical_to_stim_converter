"""Known logical-state ports, transported by Stim and composed only by stimflow.

Ports remain unlabelled until a deterministic local readout. In particular, Bell
correlations are retained instead of being discarded when local X/Z values are
individually unknown. Backend primitives still verify both logical Pauli actions.
"""

import json

import stim
import stimflow as sf

from ..core.code_frame import transformed_pauli


def detector_metadata(flow):
    if flow.obs_name is not None:
        return sf.FlowMetadata()
    anchors = [f for f in flow.flags if isinstance(f, tuple) and f[0] == "anchor"]
    if not anchors:
        raise ValueError("Completed detector flow has no semantic check anchor")
    _, _, block, check = max(anchors)
    return sf.FlowMetadata(tag="check:" + json.dumps((block, check), separators=(",", ":")))


def check_maps(backend, block, logical, orientation):
    code = backend.stabilizer_code(block, logical, orientation)
    at = {block.position(c.ancilla): c.check_id for c in block.layout.checks}
    return {tile.to_pauli_map(): at[tile.measure_qubit] for tile in code.tiles}


def prepare_part(chunk, fragment, backend, blocks, sequence):
    flows = []
    lookup = {}
    for logical, block_id, orientation in zip(
        fragment.logical_ids, fragment.block_ids, fragment.orientations_before, strict=True
    ):
        lookup.update(
            {
                p: (block_id, check)
                for p, check in check_maps(backend, blocks[block_id], logical, orientation).items()
            }
        )
    for flow in chunk.flows:
        if flow.obs_name is not None:
            if fragment.operation_type == "LogicalMeasure":
                flows.append(flow)
            continue
        flags = flow.flags
        if fragment.operation_type in ("LogicalInit", "SyndromeExtraction", "LogicalMeasure"):
            key = flow.start if flow.start else flow.end
            block, check = lookup[key]
            flags |= {("anchor", sequence, block, check)}
        flows.append(flow.with_edits(flags=flags))
    return chunk.with_edits(
        flows=flows,
        discarded_inputs=[p for p in chunk.discarded_inputs if p.obs_name is None],
        discarded_outputs=[p for p in chunk.discarded_outputs if p.obs_name is None],
    )


class LogicalFlowTracker:
    def __init__(self, backend, context):
        self.backend = backend
        self.context = context
        self.ports = set()
        self.active = set()
        self.orientations = dict.fromkeys(context.logical_to_block, 0)
        # Follow physical component time, rather than the already-staged end of a
        # parallel group (e.g. readout A concurrently with H on B). Affine signs
        # stay in CompilerContext; they do not change this stabilizer basis.
        self.logical_state = stim.TableauSimulator()
        self.logical_state.set_num_qubits(len(context.observable_ids))
        self.q2i = {q: i for i, q in enumerate(sf.sorted_complex(context.site_positions.values()))}

    def lift(self, logical_pauli):
        result = sf.PauliMap()
        for logical, index in self.context.observable_ids.items():
            if logical_pauli[index]:
                block = self.context.block_for(logical)
                basis = "_XYZ"[logical_pauli[index]]
                result *= self.backend.logical_pauli(
                    block, logical, basis, self.orientations[logical]
                )
        return result

    def before_readout(self, compiler, fragments):
        selected = {f.logical_id for f in fragments if f.operation_type == "LogicalMeasure"}
        if not selected:
            return
        remaining = self.active - selected
        old = compiler.cur_end_interface()
        if old.discards:
            raise ValueError("Readout encountered unresolved stabilizer initialization ports")
        checks = []
        for logical in sorted(self.active):
            block = self.context.block_for(logical)
            checks.extend(check_maps(self.backend, block, logical, self.orientations[logical]))
        selected_ports = []
        for logical in sorted(selected):
            block = self.context.block_for(logical)
            basis = self.context.measurement_bases[logical]
            selected_ports.append(
                self.backend.logical_pauli(
                    block, logical, basis, self.orientations[logical]
                ).with_obs_name((logical, basis))
            )
        remaining_indices = {self.context.observable_ids[q] for q in remaining}
        remaining_ports = []
        for stabilizer in self.logical_state.canonical_stabilizers():
            support = {i for i in range(len(stabilizer)) if stabilizer[i]}
            if support and support <= remaining_indices:
                remaining_ports.append(self.lift(stabilizer))
        if len(remaining_ports) != len(remaining):
            raise ValueError("Cannot separate the requested deterministic logical readout")
        out2in = {p: [p] for p in checks}
        out2in.update({p: "auto" for p in selected_ports + remaining_ports})
        reflow = sf.ChunkReflow.from_auto_rewrite(inputs=sorted(old.ports), out2in=out2in)
        reflow.verify(expected_in=old)
        compiler.append(reflow)
        self.ports = set(remaining_ports)
        self.active -= selected

    def through(self, parts):
        managed = set(self.ports)
        unitary = stim.Circuit()
        for chunk, fragment in parts:
            if fragment.operation_type in ("TransversalH", "TransversalCNOT", "LogicalPauli"):
                sf.append_reindexed_content_to_circuit(
                    content=chunk.circuit,
                    out_circuit=unitary,
                    qubit_i2i={i: self.q2i[q] for q, i in chunk.q2i.items()},
                    obs_i2i={},
                    rewrite_detector_time_coordinates=False,
                )
                indices = [self.context.observable_ids[q] for q in fragment.logical_ids]
                if fragment.logical_action == "CX":
                    self.logical_state.cx(*indices)
                elif fragment.logical_action == "H":
                    self.logical_state.h(*indices)
                else:
                    getattr(self.logical_state, fragment.logical_action.lower())(*indices)
        flows = []
        new_ports = set()
        for start in sorted(self.ports):
            end, sign = transformed_pauli(start, unitary, self.q2i)
            flows.append(sf.Flow(start=start, end=end, sign=sign, center=None))
            new_ports.add(end)
        for chunk, fragment in parts:
            if fragment.operation_type == "LogicalInit" and chunk.circuit.num_measurements == 0:
                logical = fragment.logical_id
                block = self.context.block_for(logical)
                basis = self.context.prepared_basis[logical]
                end = self.backend.logical_pauli(block, logical, basis)
                flows.append(sf.Flow(end=end, sign=False, center=None))
                new_ports.add(end)
                self.active.add(logical)
                index = self.context.observable_ids[logical]
                self.logical_state.reset(index)
                if basis == "X":
                    self.logical_state.h(index)
            for logical, orientation in zip(
                fragment.logical_ids, fragment.orientations_after, strict=True
            ):
                self.orientations[logical] = orientation
        self.ports = new_ports
        return flows, managed
