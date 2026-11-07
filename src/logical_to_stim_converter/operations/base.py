"""Common interface for code-independent logical operation objects."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..core.code_backend import CodeBackend
from ..core.logical_block import LogicalBlock
from ..core.module_fragment import ModuleFragment
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

    @abstractmethod
    def build(
        self, backend: CodeBackend, block: LogicalBlock, logical_id: str, module_id: str
    ) -> ModuleFragment:
        """Build one target's ideal physical fragment; do not insert noise."""
