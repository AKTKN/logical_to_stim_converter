"""Backend contract for ideal memory and logical Clifford primitives."""

from abc import ABC, abstractmethod

import stimflow as sf

from .logical_block import LogicalBlock


def validate_basis(basis: str) -> None:
    if basis not in ("X", "Z"):
        raise ValueError("basis must be 'X' or 'Z'")


class CodeBackend(ABC):
    @abstractmethod
    def initialization(self, block: LogicalBlock, logical_id: str, basis: str) -> sf.Chunk:
        """Transversal data reset with correct deterministic/discarded flow boundary."""

    @abstractmethod
    def syndrome_round(
        self, block: LogicalBlock, logical_id: str, orientation: int = 0
    ) -> sf.Chunk:
        """One ideal physical stabilizer-measurement cycle."""

    @abstractmethod
    def measurement(
        self, block: LogicalBlock, logical_id: str, basis: str, orientation: int = 0
    ) -> sf.Chunk:
        """Destructive readout with terminal reconstructable-check/logical flows."""

    def hadamard(self, block, logical_id, orientation=0):
        raise ValueError("Backend does not support logical Hadamard")

    def transversal_cnot(
        self, control, target, control_id, target_id, control_orientation=0, target_orientation=0
    ):
        raise ValueError("Backend does not support logical CNOT")

    def pauli(self, block, logical_id, basis, orientation=0):
        raise ValueError("Backend does not support logical Paulis")
