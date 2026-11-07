"""Rotated-surface memory circuits using the pinned stimflow public API."""

import numpy as np
import stimflow as sf

from ..core.code_backend import CodeBackend, validate_basis
from ..core.logical_block import LogicalBlock
from ..core.physical_layout import PhysicalLayout


class RotatedSurfaceCodeBackend(CodeBackend):
    def stabilizer_code(self, block: LogicalBlock, logical_id: str) -> sf.StabilizerCode:
        """Both logical Paulis are declared, even when a boundary discards one."""
        PhysicalLayout.rotated_surface(block.code)
        tiles = [
            sf.Tile(
                data_qubits=[block.position(q) for q in c.support],
                bases=c.basis,
                measure_qubit=block.position(c.ancilla),
            )
            for c in block.layout.checks
        ]
        logicals = []
        for basis, matrix in [("X", block.code.L_X), ("Z", block.code.L_Z)]:
            logicals.append(
                sf.PauliMap(
                    {
                        block.position(block.layout.data_ids[i]): basis
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

    def syndrome_round(self, block: LogicalBlock, logical_id: str) -> sf.Chunk:
        code = self.stabilizer_code(block, logical_id)
        builder = sf.ChunkBuilder(
            allowed_qubits=[block.position(q) for q in block.layout.qubit_ids]
        )
        for basis in "XZ":
            builder.append(
                f"R{basis}",
                [block.position(c.ancilla) for c in block.layout.checks if c.basis == basis],
            )
        builder.append("TICK")
        for layer in block.layout.cnot_layers:
            builder.append("CX", [(block.position(a), block.position(b)) for a, b in layer])
            builder.append("TICK")
        for basis in "XZ":
            builder.append(
                f"M{basis}",
                [block.position(c.ancilla) for c in block.layout.checks if c.basis == basis],
            )
        for tile in code.tiles:
            builder.add_flow(start=tile, measurements=[tile.measure_qubit], sign=False)
            builder.add_flow(end=tile, measurements=[tile.measure_qubit], sign=False)
        for logical in code.flat_logicals:
            builder.add_flow(start=logical, end=logical, sign=False)
        chunk = builder.finish_chunk()
        chunk.verify()
        return chunk

    def measurement(self, block: LogicalBlock, logical_id: str, basis: str) -> sf.Chunk:
        validate_basis(basis)
        code = self.stabilizer_code(block, logical_id)
        return self._signed(
            code.transversal_measure_chunk(basis=basis).with_edits(wants_to_merge_with_prev=False)
        )

    @staticmethod
    def _signed(chunk: sf.Chunk) -> sf.Chunk:
        # Verify signs, not only unsigned Pauli support relations.
        chunk = chunk.with_edits(flows=[f.with_edits(sign=False) for f in chunk.flows])
        chunk.verify()
        return chunk
