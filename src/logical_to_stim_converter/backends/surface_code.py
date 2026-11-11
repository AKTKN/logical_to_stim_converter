"""Rotated-surface memory and Clifford circuits using pinned public stimflow APIs."""

import numpy as np
import stimflow as sf

from ..core.code_backend import CodeBackend, validate_basis
from ..core.code_frame import frame_position, transformed_pauli, validate_orientation
from ..core.logical_block import LogicalBlock
from ..core.physical_layout import PhysicalLayout


class RotatedSurfaceCodeBackend(CodeBackend):
    def stabilizer_code(
        self, block: LogicalBlock, logical_id: str, orientation: int = 0
    ) -> sf.StabilizerCode:
        """Both logical Paulis are declared, even when a boundary discards one."""
        standard = PhysicalLayout.rotated_surface(block.code)
        if (
            dict(block.layout.coordinates) != dict(standard.coordinates)
            or block.layout.data_ids != standard.data_ids
            or block.layout.checks != standard.checks
        ):
            raise ValueError(
                "Backend requires standard local geometry; use block.origin for placement"
            )
        validate_orientation(orientation)
        tiles = [
            sf.Tile(
                data_qubits=[block.position(q) for q in c.support],
                bases=("Z" if c.basis == "X" else "X") if orientation else c.basis,
                measure_qubit=block.position(c.ancilla),
            )
            for c in block.layout.checks
        ]
        logicals = []
        for basis, matrix in [("X", block.code.L_X), ("Z", block.code.L_Z)]:
            logicals.append(
                sf.PauliMap(
                    {
                        frame_position(block, block.layout.data_ids[i], orientation): basis
                        for i in np.flatnonzero(matrix[0])
                    },
                    obs_name=(logical_id, basis),
                )
            )
        result = sf.StabilizerCode(sf.Patch(tiles), logicals=[tuple(logicals)])
        result.verify()
        return result

    def initialization(self, block: LogicalBlock, logical_id: str, basis: str) -> sf.Chunk:
        validate_basis(basis)
        code = self.stabilizer_code(block, logical_id)
        chunk = code.transversal_init_chunk(basis=basis)
        # All physical layers are kept separate, including data and ancilla reset.
        return self._signed(chunk.with_edits(wants_to_merge_with_next=False))

    def syndrome_round(
        self, block: LogicalBlock, logical_id: str, orientation: int = 0
    ) -> sf.Chunk:
        code = self.stabilizer_code(block, logical_id, orientation)
        builder = sf.ChunkBuilder(
            allowed_qubits=[block.position(q) for q in block.layout.qubit_ids]
        )
        for basis in "XZ":
            builder.append(
                f"R{basis}",
                [
                    block.position(c.ancilla)
                    for c in block.layout.checks
                    if (c.basis == basis) != bool(orientation)
                ],
            )
        builder.append("TICK")
        for layer in block.layout.cnot_layers:
            builder.append(
                "CX",
                [
                    (block.position(b), block.position(a))
                    if orientation
                    else (block.position(a), block.position(b))
                    for a, b in layer
                ],
            )
            builder.append("TICK")
        for basis in "XZ":
            builder.append(
                f"M{basis}",
                [
                    block.position(c.ancilla)
                    for c in block.layout.checks
                    if (c.basis == basis) != bool(orientation)
                ],
            )
        for tile in code.tiles:
            builder.add_flow(start=tile, measurements=[tile.measure_qubit], sign=False)
            builder.add_flow(end=tile, measurements=[tile.measure_qubit], sign=False)
        for logical in code.flat_logicals:
            builder.add_flow(start=logical, end=logical, sign=False)
        chunk = builder.finish_chunk()
        chunk.verify()
        return chunk

    def measurement(
        self, block: LogicalBlock, logical_id: str, basis: str, orientation: int = 0
    ) -> sf.Chunk:
        validate_basis(basis)
        code = self.stabilizer_code(block, logical_id, orientation)
        return self._signed(
            code.transversal_measure_chunk(basis=basis).with_edits(wants_to_merge_with_prev=False)
        )

    @staticmethod
    def _signed(chunk: sf.Chunk) -> sf.Chunk:
        # Verify signs, not only unsigned Pauli support relations.
        chunk = chunk.with_edits(flows=[f.with_edits(sign=False) for f in chunk.flows])
        chunk.verify()
        return chunk

    def logical_pauli(self, block, logical_id, basis, orientation=0):
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Logical Pauli must be X, Y, or Z")
        code = self.stabilizer_code(block, logical_id, orientation)
        lx, lz = code.flat_logicals
        if basis == "X":
            return lx.with_obs_name(None)
        if basis == "Z":
            return lz.with_obs_name(None)
        return sf.PauliMap(lx) * sf.PauliMap(lz)

    def hadamard(self, block, logical_id, orientation=0):
        old = self.stabilizer_code(block, logical_id, orientation)
        builder = sf.ChunkBuilder(allowed_qubits=old.data_set)
        builder.append("H", old.data_set)
        physical = builder.finish_chunk()
        chunk = self._unitary_flows(physical, [old])
        new = self.stabilizer_code(block, logical_id, 1 - orientation)
        expected = [
            new.flat_logicals[1 - i].with_obs_name(p.obs_name)
            for i, p in enumerate(old.flat_logicals)
        ]
        self._verify_logical_action(chunk, new.tiles, expected)
        return chunk

    def hadamard_corrections(self, block, logical_id, orientation=0):
        """Old check sectors required by the canonical quarter-rotated logical basis."""
        old = self.stabilizer_code(block, logical_id, orientation)
        new = self.stabilizer_code(block, logical_id, 1 - orientation)
        chunk = self.hadamard(block, logical_id, orientation)
        stable = [tile.to_pauli_map() for tile in old.tiles]
        check_at = {block.position(c.ancilla): c.check_id for c in block.layout.checks}
        lookup = {tile.to_pauli_map(): check_at[tile.measure_qubit] for tile in old.tiles}
        result = {}
        for index, basis in enumerate("XZ"):
            previous = sf.PauliMap(old.flat_logicals[1 - index])
            backward, _ = transformed_pauli(
                sf.PauliMap(new.flat_logicals[index]), chunk.circuit, chunk.q2i, inverse=True
            )
            reflow = sf.ChunkReflow.from_auto_rewrite_transitions_using_stable(
                stable=stable, transitions=[(backward, previous)]
            )
            reflow.verify()
            result[basis] = tuple(lookup[p] for p in reflow.out2in[previous] if p != backward)
        return result

    def cnot_pairs(self, control, target, control_orientation=0, target_orientation=0):
        validate_orientation(control_orientation)
        validate_orientation(target_orientation)
        if control.block_id == target.block_id or control.code.d != target.code.d:
            raise ValueError("CNOT requires distinct compatible equal-distance blocks")
        self.stabilizer_code(control, "control", control_orientation)
        self.stabilizer_code(target, "target", target_orientation)
        a = [frame_position(control, q, control_orientation) for q in control.layout.data_ids]
        b = [frame_position(target, q, target_orientation) for q in target.layout.data_ids]
        if set(a) & set(b):
            raise ValueError("CNOT data sites overlap")
        return tuple(zip(a, b, strict=True))

    def transversal_cnot(
        self, control, target, control_id, target_id, control_orientation=0, target_orientation=0
    ):
        codes = [
            self.stabilizer_code(control, control_id, control_orientation),
            self.stabilizer_code(target, target_id, target_orientation),
        ]
        pairs = self.cnot_pairs(control, target, control_orientation, target_orientation)
        builder = sf.ChunkBuilder(allowed_qubits=[q for pair in pairs for q in pair])
        builder.append("CX", pairs)
        chunk = self._unitary_flows(builder.finish_chunk(), codes)
        inputs = [f.end for f in chunk.flows if f.obs_name is None]
        outputs = [tile.to_pauli_map() for code in codes for tile in code.tiles]
        reflow = sf.ChunkReflow.from_auto_rewrite(
            inputs=inputs, out2in={p: "auto" for p in outputs}
        )
        reflow.verify()
        cx, cz = codes[0].flat_logicals
        tx, tz = codes[1].flat_logicals
        expected = [
            (sf.PauliMap(cx) * sf.PauliMap(tx)).with_obs_name(cx.obs_name),
            cz,
            tx,
            (sf.PauliMap(cz) * sf.PauliMap(tz)).with_obs_name(tz.obs_name),
        ]
        self._verify_logical_action(
            chunk, [tile for code in codes for tile in code.tiles], expected
        )
        return chunk, reflow

    def pauli(self, block, logical_id, basis, orientation=0):
        code = self.stabilizer_code(block, logical_id, orientation)
        representative = self.logical_pauli(block, logical_id, basis, orientation)
        builder = sf.ChunkBuilder(allowed_qubits=code.data_set)
        for axis in "XYZ":
            builder.append(axis, [q for q, b in representative.items() if b == axis])
        return self._unitary_flows(builder.finish_chunk(), [code])

    def transversal_pauli(self, block, logical_id, basis, orientation=0):
        """Apply an odd-distance rotated-code Pauli on every fixed data site.

        Stim verifies signed check/logical conjugation, including Y. Even check
        weights and odd logical weights give the intended encoded Pauli action.
        """
        if basis not in ("X", "Y", "Z"):
            raise ValueError("Logical Pauli must be X, Y, or Z")
        code = self.stabilizer_code(block, logical_id, orientation)
        builder = sf.ChunkBuilder(allowed_qubits=code.data_set)
        builder.append(basis, code.data_set)
        return self._unitary_flows(builder.finish_chunk(), [code])

    @staticmethod
    def _verify_logical_action(chunk, output_tiles, expected_logicals):
        actual = [f.end for f in chunk.flows if f.obs_name is not None]
        stable = [tile.to_pauli_map() for tile in output_tiles]
        transition = sf.ChunkReflow.from_auto_rewrite_transitions_using_stable(
            stable=stable, transitions=list(zip(actual, expected_logicals, strict=True))
        )
        transition.verify()

    @staticmethod
    def _unitary_flows(chunk, codes):
        flows = []
        for code in codes:
            for tile in code.tiles:
                start = tile.to_pauli_map()
                end, sign = transformed_pauli(start, chunk.circuit, chunk.q2i)
                flows.append(sf.Flow(start=start, end=end, sign=sign, center=None))
            for start in code.flat_logicals:
                end, sign = transformed_pauli(start, chunk.circuit, chunk.q2i)
                flows.append(sf.Flow(start=start, end=end, sign=sign, center=None))
        result = chunk.with_edits(flows=flows)
        result.verify()
        return result
