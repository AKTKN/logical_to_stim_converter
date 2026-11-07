"""Repeated ideal stabilizer measurement, preserving logical Pauli flows."""

from dataclasses import dataclass

import stimflow as sf

from ..core.code_spec import positive_int
from ..core.module_fragment import ModuleFragment
from .base import OperationModule


@dataclass(frozen=True)
class SyndromeExtraction(OperationModule):
    rounds: int

    def __post_init__(self) -> None:
        super().__post_init__()
        positive_int(self.rounds, "rounds")

    def build(self, backend, block, logical_id, module_id) -> ModuleFragment:
        result = ModuleFragment(
            module_id,
            self.operation_type,
            logical_id,
            block.block_id,
            (sf.ChunkLoop([backend.syndrome_round(block, logical_id)], repetitions=self.rounds),),
            noise=self.noise,
        )
        result.verify()
        return result
