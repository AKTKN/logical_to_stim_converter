"""Logical X/Y/Z execution, or a zero-duration virtual logical Pauli update."""

from dataclasses import dataclass

from ..core.module_fragment import ModuleFragment
from .base import OperationModule


@dataclass(frozen=True)
class LogicalPauli(OperationModule):
    pauli: str
    mode: str = "physical"

    def __post_init__(self):
        super().__post_init__()
        if self.pauli not in ("X", "Y", "Z") or self.mode not in (
            "physical",
            "frame",
            "transversal",
        ):
            raise ValueError("LogicalPauli requires X/Y/Z and physical/frame/transversal mode")

    def _build(self, backend, operands, context):
        logical, block = next(iter(operands.items()))
        orientation = context.orientations.get(logical, 0)
        components = (
            ()
            if self.mode == "frame"
            else (
                (
                    backend.transversal_pauli(block, logical, self.pauli, orientation)
                    if self.mode == "transversal"
                    else backend.pauli(block, logical, self.pauli, orientation)
                ),
            )
        )
        return ModuleFragment(
            context.module_id,
            self.operation_type,
            (logical,),
            (block.block_id,),
            components,
            noise=self.noise,
            orientations_before=(orientation,),
            orientations_after=(orientation,),
            logical_action=self.pauli,
            frame_transition=self.mode,
        )
