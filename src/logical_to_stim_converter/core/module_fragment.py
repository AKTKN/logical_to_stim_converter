"""A thin flow-component wrapper; no duplicate flow-composition engine."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import stimflow as sf

if TYPE_CHECKING:
    from ..noise.model import NoiseOverride
    from .compiler_context import MeasurementInfo


@dataclass(frozen=True)
class ModuleFragment:
    module_id: str
    operation_type: str
    logical_id: str
    block_id: str
    components: tuple[sf.Chunk | sf.ChunkLoop, ...]
    noise: "NoiseOverride | None" = None
    stage: str | None = None
    frame_transition: str = "preserve"
    operation_id: str | None = None
    measurement_records: tuple["MeasurementInfo", ...] = ()

    @property
    def input_logicals(self) -> tuple[str, ...]:
        return () if self.frame_transition == "initialize" else (self.logical_id,)

    @property
    def output_logicals(self) -> tuple[str, ...]:
        return () if self.frame_transition == "terminate" else (self.logical_id,)

    def verify(self) -> None:
        for component in self.components:
            component.verify()

    def chunks(self) -> tuple[sf.Chunk, ...]:
        """Expand loops only for synchronous layer/measurement provenance assembly."""

        def expand(component):
            if isinstance(component, sf.Chunk):
                yield component
            else:
                for _ in range(component.repetitions):
                    for child in component.chunks:
                        yield from expand(child)

        return tuple(c for component in self.components for c in expand(component))
