"""Ordered multi-block CNOT and code-frame-aware physical Hadamard layers."""

from dataclasses import dataclass

from ..core.module_fragment import ModuleFragment
from ..noise.model import NoiseOverride
from .base import OperationModule


@dataclass(frozen=True)
class TransversalH(OperationModule):
    def _build(self, backend, operands, context):
        logical, block = next(iter(operands.items()))
        orientation = context.orientations.get(logical, 0)
        return ModuleFragment(
            context.module_id,
            self.operation_type,
            (logical,),
            (block.block_id,),
            (backend.hadamard(block, logical, orientation),),
            noise=self.noise,
            orientations_before=(orientation,),
            orientations_after=(1 - orientation,),
            logical_action="H",
            frame_transition="H",
        )


@dataclass(frozen=True, init=False)
class TransversalCNOT(OperationModule):
    def __init__(
        self,
        control: str,
        target: str,
        *,
        noise: NoiseOverride | None = None,
        operation_id: str | None = None,
    ):
        object.__setattr__(self, "targets", (control, target))
        object.__setattr__(self, "noise", noise)
        object.__setattr__(self, "operation_id", operation_id)
        self.__post_init__()

    @property
    def control(self):
        return self.targets[0]

    @property
    def target(self):
        return self.targets[1]

    @property
    def coupled(self):
        return True

    def _build(self, backend, operands, context):
        c, t = (operands[logical] for logical in self.targets)
        orientations = tuple(context.orientations.get(logical, 0) for logical in self.targets)
        components = backend.transversal_cnot(c, t, self.control, self.target, *orientations)
        return ModuleFragment(
            context.module_id,
            self.operation_type,
            self.targets,
            (c.block_id, t.block_id),
            components,
            noise=self.noise,
            orientations_before=orientations,
            orientations_after=orientations,
            logical_action="CX",
            frame_transition="CX",
        )
