"""Common interface for code-independent logical operation objects."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field

from ..core.code_backend import CodeBackend
from ..core.logical_block import LogicalBlock
from ..core.module_fragment import ModuleFragment, OperationContext
from ..noise.model import NoiseOverride


@dataclass(frozen=True)
class OperationModule(ABC):
    targets: tuple[str, ...] | str
    noise: NoiseOverride | None = field(default=None, kw_only=True)
    operation_id: str | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        targets = (self.targets,) if isinstance(self.targets, str) else tuple(self.targets)
        if (
            not targets
            or any(not isinstance(t, str) or not t for t in targets)
            or len(set(targets)) != len(targets)
        ):
            raise ValueError("targets must contain distinct nonempty logical IDs")
        if self.operation_id is not None and (
            not isinstance(self.operation_id, str) or not self.operation_id
        ):
            raise ValueError("operation_id must be a nonempty string")
        if self.noise is not None and not isinstance(self.noise, NoiseOverride):
            raise ValueError("noise must be a NoiseOverride")
        object.__setattr__(self, "targets", targets)

    @property
    def operation_type(self) -> str:
        return type(self).__name__

    @property
    def coupled(self) -> bool:
        return False

    def build(
        self,
        backend: CodeBackend,
        operands: Mapping[str, LogicalBlock] | LogicalBlock,
        context: OperationContext | str,
        module_id: str | None = None,
    ) -> ModuleFragment:
        """Ordered operand API, plus the original single-block build compatibility form.

        The compiler desugars independent multi-target operations into concurrent
        single-block fragments; coupled operations receive all ordered operands.
        """
        if isinstance(operands, LogicalBlock):
            operands = {context: operands}
            context = OperationContext(module_id, {context: 0})
        if not isinstance(context, OperationContext):
            raise ValueError("build requires an OperationContext")
        if (self.coupled and tuple(operands) != self.targets) or (
            not self.coupled and (len(operands) != 1 or next(iter(operands)) not in self.targets)
        ):
            raise ValueError("Incorrect ordered operands for operation")
        positions = [
            block.position(q) for block in operands.values() for q in block.layout.qubit_ids
        ]
        if len(set(positions)) != len(positions):
            raise ValueError("Operation operands overlap physical sites")
        fragment = self._build(backend, operands, context)
        if (
            fragment.logical_ids != tuple(operands)
            or fragment.block_ids != tuple(block.block_id for block in operands.values())
            or fragment.module_id != context.module_id
            or not fragment.interface_positions <= set(positions)
        ):
            raise ValueError("Fragment identity or physical scope disagrees with its operands")
        fragment.verify()
        return fragment

    @abstractmethod
    def _build(
        self, backend: CodeBackend, operands: Mapping[str, LogicalBlock], context: OperationContext
    ) -> ModuleFragment:
        """Build verified ideal physical components without noise or state mutation."""
