"""Destructive basis readout and terminal stabilizer/logical flow consumption."""

from dataclasses import dataclass

from ..core.code_backend import validate_basis
from ..core.module_fragment import ModuleFragment
from .base import OperationModule


@dataclass(frozen=True)
class LogicalMeasure(OperationModule):
    basis: str

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_basis(self.basis)

    def build(self, backend, block, logical_id, module_id) -> ModuleFragment:
        result = ModuleFragment(
            module_id,
            self.operation_type,
            logical_id,
            block.block_id,
            (backend.measurement(block, logical_id, self.basis),),
            noise=self.noise,
            frame_transition="terminate",
        )
        result.verify()
        return result
