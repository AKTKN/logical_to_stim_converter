"""Multi-operand wrappers around verified public stimflow components."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

import stimflow as sf

from .lifecycle import BlockUseId

if TYPE_CHECKING:
    from ..noise.model import NoiseOverride
    from .compiler_context import MeasurementInfo


@dataclass(frozen=True)
class OperationContext:
    """Primitive module identity and logical-to-physical code orientations."""
    module_id: str
    orientations: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.module_id, str) or not self.module_id:
            raise ValueError("OperationContext requires a nonempty module ID")
        object.__setattr__(self, "orientations", MappingProxyType(dict(self.orientations)))


@dataclass(frozen=True)
class ModuleFragment:
    """Verified physical primitives and historical ordered operand/use identities."""
    module_id: str
    operation_type: str
    logical_ids: tuple[str, ...]
    block_ids: tuple[str, ...]
    components: tuple[sf.Chunk | sf.ChunkLoop | sf.ChunkReflow, ...]
    noise: "NoiseOverride | None" = None
    stage: str | None = None
    frame_transition: str = "preserve"
    operation_id: str | None = None
    measurement_records: tuple["MeasurementInfo", ...] = ()
    orientations_before: tuple[int, ...] = ()
    orientations_after: tuple[int, ...] = ()
    logical_action: str = "I"
    readout_mode: str = "deterministic"
    composite_ids: tuple[str, ...] = ()
    block_use_ids: tuple[BlockUseId, ...] = ()

    def __post_init__(self):
        # Scalar construction remains accepted for the original one-block wrappers.
        for name in ("logical_ids", "block_ids"):
            value = getattr(self, name)
            object.__setattr__(self, name, (value,) if isinstance(value, str) else tuple(value))
        if (
            not self.logical_ids
            or len(self.logical_ids) != len(self.block_ids)
            or len(set(self.logical_ids)) != len(self.logical_ids)
            or len(set(self.block_ids)) != len(self.block_ids)
        ):
            raise ValueError("Fragments require distinct, corresponding logical and block operands")

    @property
    def logical_id(self) -> str:
        """Single logical operand; multi-block callers use logical_ids."""
        if len(self.logical_ids) != 1:
            raise ValueError("A multi-operand fragment has logical_ids, not one logical_id")
        return self.logical_ids[0]

    @property
    def block_id(self) -> str:
        """Single fixed physical patch; independent of its current epoch."""
        if len(self.block_ids) != 1:
            raise ValueError("A multi-operand fragment has block_ids, not one block_id")
        return self.block_ids[0]

    @property
    def input_logicals(self) -> tuple[str, ...]:
        """State identities consumed or transported by this primitive."""
        return () if self.frame_transition == "initialize" else self.logical_ids

    @property
    def output_logicals(self) -> tuple[str, ...]:
        """State identities created or transported by this primitive."""
        return () if self.frame_transition == "terminate" else self.logical_ids

    @property
    def interface_positions(self) -> frozenset[complex]:
        """Physical coordinates declared by flow interfaces, including passive sites."""
        return frozenset(q for step in self.steps() if isinstance(step, sf.Chunk) for q in step.q2i)

    @property
    def physical_positions(self) -> frozenset[complex]:
        """Sites with actual gates, distinct from qubits declared in a flow port."""
        positions = set()
        for chunk in self.chunks():
            i2q = {i: q for q, i in chunk.q2i.items()}
            for instruction in chunk.circuit:
                if instruction.name in (
                    "QUBIT_COORDS",
                    "DETECTOR",
                    "OBSERVABLE_INCLUDE",
                    "SHIFT_COORDS",
                    "TICK",
                ):
                    continue
                positions.update(
                    i2q[t.value]
                    for t in instruction.targets_copy()
                    if t.is_qubit_target or t.is_x_target or t.is_y_target or t.is_z_target
                )
        return frozenset(positions)

    def verify(self) -> None:
        """Verify each physical flow/reflow with the pinned public stimflow API."""
        for component in self.components:
            component.verify()

    def steps(self):
        """Expand loops in execution order without changing primitive identity."""
        def expand(component):
            """Recursively expand nested repetitions without duplicating wrappers."""
            if isinstance(component, sf.ChunkLoop):
                for _ in range(component.repetitions):
                    for child in component.chunks:
                        yield from expand(child)
            else:
                yield component

        return tuple(step for component in self.components for step in expand(component))

    def chunks(self) -> tuple[sf.Chunk, ...]:
        """Return physical chunks in order, omitting zero-duration reflows."""
        return tuple(step for step in self.steps() if isinstance(step, sf.Chunk))
