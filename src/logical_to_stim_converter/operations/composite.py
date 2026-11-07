"""Composite contracts expand into ordinary, independently verified primitives."""

from dataclasses import dataclass

from .base import OperationModule


@dataclass(frozen=True)
class CompositeStep:
    operations: tuple[OperationModule, ...]
    stage: str


class CompositeOperation(OperationModule):
    @property
    def coupled(self):
        return True

    def _build(self, backend, operands, context):
        raise ValueError("Composite operations must be expanded by CircuitCompiler")

    def expand(self, context) -> tuple[CompositeStep, ...]:
        raise NotImplementedError
