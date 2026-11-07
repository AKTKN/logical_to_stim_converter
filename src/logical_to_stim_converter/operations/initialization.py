"""Basis initialization followed by an explicit positive number of SE rounds."""

from dataclasses import dataclass

import stimflow as sf

from ..core.code_backend import validate_basis
from ..core.code_spec import positive_int
from ..core.module_fragment import ModuleFragment
from .base import OperationModule


@dataclass(frozen=True)
class LogicalInit(OperationModule):
    basis: str
    rounds: int

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_basis(self.basis)
        positive_int(self.rounds, "rounds")

    def build(self, backend, block, logical_id, module_id) -> ModuleFragment:
        result = ModuleFragment(
            module_id,
            self.operation_type,
            logical_id,
            block.block_id,
            (
                backend.initialization(block, logical_id, self.basis),
                sf.ChunkLoop([backend.syndrome_round(block, logical_id)], repetitions=self.rounds),
            ),
            noise=self.noise,
            frame_transition="initialize",
        )
        result.verify()
        return result
