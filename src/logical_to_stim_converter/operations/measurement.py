"""Destructive basis readout and terminal stabilizer/logical flow consumption."""

from dataclasses import dataclass

from ..core.code_backend import validate_basis
from ..core.module_fragment import ModuleFragment
from .base import OperationModule


@dataclass(frozen=True)
class LogicalMeasure(OperationModule):
    basis: str
    mode: str = "deterministic"

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_basis(self.basis)
        if self.mode not in ("deterministic", "random"):
            raise ValueError("Measurement mode must be deterministic or random")

    def _build(self, backend, operands, context) -> ModuleFragment:
        logical_id, block = next(iter(operands.items()))
        module_id = context.module_id
        orientation = context.orientations.get(logical_id, 0)
        result = ModuleFragment(
            module_id,
            self.operation_type,
            logical_id,
            block.block_id,
            (backend.measurement(block, logical_id, self.basis, orientation),),
            orientations_before=(orientation,),
            orientations_after=(orientation,),
            noise=self.noise,
            frame_transition="terminate",
            readout_mode=self.mode,
        )
        result.verify()
        return result
