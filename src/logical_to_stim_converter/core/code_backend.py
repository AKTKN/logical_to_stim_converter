"""Backend contract for the three memory primitives."""

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
    def syndrome_round(self, block: LogicalBlock, logical_id: str) -> sf.Chunk:
        """One ideal physical stabilizer-measurement cycle."""

    @abstractmethod
    def measurement(self, block: LogicalBlock, logical_id: str, basis: str) -> sf.Chunk:
        """Destructive readout with terminal reconstructable-check/logical flows."""
