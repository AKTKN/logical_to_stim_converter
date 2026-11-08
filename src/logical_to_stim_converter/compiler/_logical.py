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
    """Preserve the latest check's module/block identity in a Stim detector tag."""
    if flow.obs_name is not None:
        return sf.FlowMetadata()
    anchors = [f for f in flow.flags if isinstance(f, tuple) and f[0] == "anchor"]
    if not anchors:
        raise ValueError("Completed detector flow has no semantic check anchor")
    _, _, block, check, module = max(anchors)
    return sf.FlowMetadata(tag="check:" + json.dumps((block, check, module), separators=(",", ":")))


def check_maps(backend, block, logical, orientation):
    """Map physical stabilizer supports to local check IDs in the current basis."""
    code = backend.stabilizer_code(block, logical, orientation)
    at = {block.position(c.ancilla): c.check_id for c in block.layout.checks}
    return {tile.to_pauli_map(): at[tile.measure_qubit] for tile in code.tiles}


def prepare_part(chunk, fragment, backend, blocks, sequence):
    """Attach check anchors and defer logical-state flow management to the tracker."""
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
            if (fragment.operation_type == "LogicalMeasure"
                    and fragment.readout_mode == "deterministic"):
                flows.append(flow)
            continue
        flags = flow.flags
        if fragment.operation_type in ("LogicalInit", "SyndromeExtraction", "LogicalMeasure"):
            key = flow.start if flow.start else flow.end
            block, check = lookup[key]
            flags |= {("anchor", sequence, block, check, fragment.module_id)}
        flows.append(flow.with_edits(flags=flags))
    return chunk.with_edits(
        flows=flows,
        discarded_inputs=[p for p in chunk.discarded_inputs if p.obs_name is None],
        discarded_outputs=[p for p in chunk.discarded_outputs if p.obs_name is None],
    )


class LogicalFlowTracker:
    """Bounded intended-state tableau and actual physical known-state ports.

    Persistent logical slots survive relocation. Fresh aliases reset retired
    slots before reuse, so destroyed state information cannot enter new ports.
    """
    def __init__(self, backend, context):
        """Allocate one internal logical tableau slot per registered physical patch."""
        self.backend = backend
        self.context = context
        self.ports = set()
        self.pending_readout = []
        self.measurement_flows = []
        self.discarded_readout_ports = set()
        self.active = set()
        self.orientations = dict.fromkeys(context.logical_to_block, 0)
        # Follow physical component time, rather than the already-staged end of a
        # parallel group (e.g. readout A concurrently with H on B). Affine signs
        # stay in CompilerContext; they do not change this stabilizer basis.
        self.logical_state = stim.TableauSimulator()
        self.logical_state.set_num_qubits(context.num_logical_slots)
        self.q2i = {q: i for i, q in enumerate(sf.sorted_complex(context.site_positions.values()))}

    def lift(self, logical_pauli):
        """Lift active logical-slot Pauli support onto fixed physical patch sites."""
        result = sf.PauliMap()
        for logical in sorted(self.active):
            index = self.context.observable_ids[logical]
            if logical_pauli[index]:
                block = self.context.block_for(logical)
                basis = "_XYZ"[logical_pauli[index]]
                result *= self.backend.logical_pauli(
                    block, logical, basis, self.orientations[logical]
                )
        return result

    def before_readout(self, compiler, fragments):
        """Separate named deterministic outputs or project random Bell readouts."""
        selected = {f.logical_id for f in fragments if f.operation_type == "LogicalMeasure"}
        if not selected:
            return
        if any(f.readout_mode == "random" for f in fragments
               if f.operation_type == "LogicalMeasure"):
            self._random_readout(compiler, fragments, selected)
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

    def _random_readout(self, compiler, fragments, selected):
        """Project a known joint state without declaring random bits deterministic.

        Rebase the surviving commuting state generators with public reflows.
        Their physical measurement-mediated flows are solved and signed by Stim
        in the parallel adapter. Generators destroyed by measurement are consumed
        explicitly; all surviving conditional quantum information is retained.
        """
        old = compiler.cur_end_interface()
        if old.discards:
            raise ValueError("Readout encountered unresolved stabilizer initialization ports")
        measured = []
        named = []
        for f in fragments:
            if f.operation_type != "LogicalMeasure":
                continue
            q = f.logical_id
            basis = self.context.measurement_bases[q]
            measured.append(self.backend.logical_pauli(
                self.context.blocks[f.block_id], q, basis, self.orientations[q]))
            if f.readout_mode == "deterministic":
                named.append(measured[-1].with_obs_name((q, basis)))
            p = stim.PauliString(self.context.num_logical_slots)
            p[self.context.observable_ids[q]] = basis
            expectation = self.logical_state.peek_observable_expectation(p)
            self.logical_state.postselect_observable(p, desired_value=expectation == -1)
            self.logical_state.reset(self.context.observable_ids[q])
        remaining = self.active - selected
        remaining_indices = {self.context.observable_ids[q] for q in remaining}
        ends = []
        for p in self.logical_state.canonical_stabilizers():
            support = {i for i in range(len(p)) if p[i]}
            if support and support <= remaining_indices:
                ends.append(self.lift(p))
        if len(ends) != len(remaining):
            raise ValueError("Incomplete conditional state after destructive measurement")
        solve = sf.ChunkReflow.from_auto_rewrite(
            inputs=sorted(old.ports) + measured, out2in={p: "auto" for p in ends})
        out2in = {p: [p] for q in sorted(self.active) for p in check_maps(
            self.backend, self.context.block_for(q), q, self.orientations[q])}
        pending = []
        for end, factors in solve.out2in.items():
            start = sf.PauliMap()
            for p in factors:
                if p not in measured:
                    start *= p
            out2in[start] = "auto"
            pending.append((start, end))
        out2in.update({p: "auto" for p in named})
        required = set(out2in)
        # Pinned ChunkReflow requires a square, invertible generator change.
        # Complete the basis, then consume the measurement-destroyed generators
        # as explicit discarded inputs of the physical measurement chunk.
        for p in sorted(old.ports):
            try:
                sf.ChunkReflow.from_auto_rewrite(inputs=list(out2in), out2in={p: "auto"})
            except ValueError:
                out2in[p] = "auto"
        reflow = sf.ChunkReflow.from_auto_rewrite(inputs=sorted(old.ports), out2in=out2in)
        reflow.verify(expected_in=old)
        compiler.append(reflow)
        self.discarded_readout_ports = set(out2in) - required
        self.pending_readout = pending
        self.ports = set(ends)
        self.active = remaining

    def through(self, parts):
        """Transport signed ports through one concurrent physical component layer."""
        managed = (set(self.ports) | {p for p, _ in self.pending_readout}
                   | self.discarded_readout_ports)
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
        pending_ends = {p for _, p in self.pending_readout}
        for start in sorted(self.ports):
            end, sign = transformed_pauli(start, unitary, self.q2i)
            if start not in pending_ends:
                flows.append(sf.Flow(start=start, end=end, sign=sign, center=None))
            new_ports.add(end)
        self.measurement_flows = [
            (start, transformed_pauli(end, unitary, self.q2i)[0])
            for start, end in self.pending_readout
        ]
        self.pending_readout = []
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
