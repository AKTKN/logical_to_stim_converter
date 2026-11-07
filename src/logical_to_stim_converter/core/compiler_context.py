"""Per-compilation lifecycle, symbolic records, frames, and physical-time metadata."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from .logical_block import GlobalSiteId, LogicalBlock


class BlockStatus(str, Enum):
    UNINITIALIZED = "uninitialized"
    ACTIVE = "active"
    MEASURED = "measured"


@dataclass(frozen=True)
class MeasurementKey:
    block_id: str
    local_id: str
    kind: str
    round_index: int | None = None


@dataclass(frozen=True)
class MeasurementInfo:
    key: MeasurementKey
    index: int
    logical_id: str
    basis: str
    module_id: str
    time_layer: int


@dataclass(frozen=True)
class DetectorInfo:
    index: int
    coordinates: tuple[float, ...]
    measurement_indices: tuple[int, ...]
    measurement_keys: tuple[MeasurementKey, ...]
    block_id: str
    check_id: str


@dataclass(frozen=True)
class ObservableInfo:
    index: int
    logical_id: str
    block_id: str
    basis: str
    measurement_indices: tuple[int, ...]


@dataclass(frozen=True)
class PauliFrame:
    """Memory preserves logical frame; preparation syndromes are retained, not corrected.

    Empty logical terms denote no assumed logical Pauli correction. The first
    conjugate-basis check outcomes label the random initial stabilizer sector.
    No decoder-dependent physical or logical correction is inferred from them.
    """

    x_terms: tuple[MeasurementKey, ...] = ()
    z_terms: tuple[MeasurementKey, ...] = ()
    preparation_syndromes: tuple[MeasurementKey, ...] = ()


@dataclass(frozen=True)
class TimeLayer:
    index: int
    active_blocks: tuple[str, ...]
    operation_by_block: Mapping[str, str]
    used_qubits: frozenset[int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "operation_by_block", MappingProxyType(dict(self.operation_by_block))
        )


class CompilerContext:
    """Fresh state for each compile; one logical slot per physical memory block."""

    def __init__(
        self, blocks: Sequence[LogicalBlock], logical_to_block: Mapping[str, str] | None = None
    ):
        self.blocks = {b.block_id: b for b in blocks}
        if not blocks or len(self.blocks) != len(blocks):
            raise ValueError("Register at least one block, with distinct block IDs")
        self.logical_to_block = (
            dict(logical_to_block)
            if logical_to_block is not None
            else {b.block_id: b.block_id for b in blocks}
        )
        if (
            not self.logical_to_block
            or any(not isinstance(k, str) or not k for k in self.logical_to_block)
            or set(self.logical_to_block.values()) != set(self.blocks)
            or len(self.logical_to_block) != len(self.blocks)
        ):
            raise ValueError("Memory requires a one-to-one logical ID to registered block mapping")
        self.site_positions: dict[GlobalSiteId, complex] = {}
        for block in blocks:
            if block.code.k != 1:
                raise ValueError("Memory currently supports one logical slot per block")
            for local in block.layout.qubit_ids:
                self.site_positions[block.global_site(local)] = block.position(local)
        if len(set(self.site_positions.values())) != len(self.site_positions):
            raise ValueError("Registered patches have overlapping physical coordinates")
        self.status = dict.fromkeys(self.blocks, BlockStatus.UNINITIALIZED)
        self.prepared_basis: dict[str, str] = {}
        self.observable_ids = {
            logical: i for i, logical in enumerate(sorted(self.logical_to_block))
        }
        self.frames = {logical: PauliFrame() for logical in self.logical_to_block}
        self.measurements: tuple[MeasurementInfo, ...] = ()
        self.detectors: tuple[DetectorInfo, ...] = ()
        self.layers: tuple[TimeLayer, ...] = ()

    def block_for(self, logical_id: str) -> LogicalBlock:
        if logical_id not in self.logical_to_block:
            raise ValueError(f"Unknown logical qubit {logical_id!r}")
        return self.blocks[self.logical_to_block[logical_id]]

    def transition(self, operation_type: str, logical_id: str, basis: str | None) -> None:
        block = self.block_for(logical_id)
        status = self.status[block.block_id]
        if operation_type == "LogicalInit":
            if status != BlockStatus.UNINITIALIZED:
                raise ValueError("LogicalInit requires an uninitialized block")
            self.status[block.block_id] = BlockStatus.ACTIVE
            self.prepared_basis[logical_id] = basis
        elif operation_type in ("SyndromeExtraction", "LogicalMeasure"):
            if status != BlockStatus.ACTIVE:
                raise ValueError(f"{operation_type} requires an active initialized block")
            if operation_type == "LogicalMeasure":
                if basis != self.prepared_basis[logical_id]:
                    raise ValueError("Memory readout basis must match its preparation basis")
                self.status[block.block_id] = BlockStatus.MEASURED
        else:
            raise ValueError(f"Unsupported memory operation {operation_type!r}")
