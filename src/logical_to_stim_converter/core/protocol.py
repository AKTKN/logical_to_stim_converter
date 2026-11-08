"""Decoder-independent preparation, readout, stage, and relocation contracts."""

from dataclasses import dataclass

import numpy as np

from .code_frame import validate_orientation
from .compiler_context import MeasurementKey, ParityExpression, PauliFrame
from .lifecycle import BlockUseId


@dataclass(frozen=True)
class CheckHistory:
    """Physical check support/basis and its per-use ordered raw measurement keys."""
    check_id: str
    basis: str
    support: tuple[str, ...]
    measurements: tuple[MeasurementKey, ...]


@dataclass(frozen=True)
class PhysicalPauliFrame:
    """A selected physical correction at an explicit preparation boundary.

    None supports mean unresolved. Empty supports mean a resolved identity.
    Supports use physical local data IDs, never Stim indices. Choosing these
    vectors is a decoder responsibility, separate from Clifford propagation.
    block_use_id scopes the physical correction to one reset interval; old
    measurement sources remain historical even after these sites are reset.
    """

    block_id: str
    orientation: int
    preparation_module_id: str
    stage_id: str | None
    source_syndromes: tuple[MeasurementKey, ...]
    x_support: tuple[str, ...] | None = None
    z_support: tuple[str, ...] | None = None
    logical_contribution: PauliFrame = PauliFrame()
    block_use_id: BlockUseId | None = None

    def __post_init__(self):
        validate_orientation(self.orientation)
        if self.block_use_id is not None and (
                not isinstance(self.block_use_id, BlockUseId)
                or self.block_use_id.block_id != self.block_id):
            raise ValueError("Physical frame use disagrees with its physical block")
        object.__setattr__(self, "source_syndromes", tuple(self.source_syndromes))
        if (self.x_support is None) != (self.z_support is None):
            raise ValueError("Both physical correction supports must be resolved together")
        for name in ("x_support", "z_support"):
            value = getattr(self, name)
            if value is not None:
                value = tuple(value)
                if len(set(value)) != len(value):
                    raise ValueError("Physical correction supports must have unique data IDs")
                object.__setattr__(self, name, value)

    @property
    def resolved(self):
        """Whether an external caller has selected both physical Pauli supports."""
        return self.x_support is not None


@dataclass(frozen=True)
class PreparationInfo:
    """Historical reset/SE preparation, addressable after its logical owner retires."""
    module_id: str
    block_id: str
    logical_id: str
    stage_id: str | None
    basis: str
    orientation: int
    data_ids: tuple[str, ...]
    checks: tuple[CheckHistory, ...]
    logical_x: tuple[str, ...]
    logical_z: tuple[str, ...]
    block_use_id: BlockUseId | None = None

    @property
    def rounds(self):
        """Number of physical syndrome rounds in this preparation primitive."""
        return len(self.checks[0].measurements)

    @property
    def gauge_measurements(self):
        """First-round conjugate-basis outcomes; these are random sector labels."""
        return tuple(c.measurements[0] for c in self.checks if c.basis != self.basis)

    @property
    def unresolved_frame(self):
        """External correction boundary tied to this preparation's final checks."""
        return PhysicalPauliFrame(self.block_id, self.orientation, self.module_id,
                                  self.stage_id, tuple(c.measurements[-1] for c in self.checks),
                                  block_use_id=self.block_use_id)

    def check_matrix(self, basis):
        """Return binary check rows in physical data_ids column order."""
        return np.array([[q in c.support for q in self.data_ids]
                         for c in self.checks if c.basis == basis], dtype=np.uint8)

    def resolve(self, x, z):
        """Wrap an external hypothesis; this does not prove its syndrome or correctness."""
        vectors = []
        for vector in (x, z):
            a = np.asarray(vector)
            if a.shape != (len(self.data_ids),) or not np.isin(a, (0, 1)).all():
                raise ValueError("Correction must be a binary physical-data vector")
            vectors.append(tuple(q for q, bit in zip(self.data_ids, a, strict=True) if bit))
        xs, zs = vectors
        logical = PauliFrame(x_constant=bool(len(set(xs) & set(self.logical_z)) % 2),
                             z_constant=bool(len(set(zs) & set(self.logical_x)) % 2))
        return PhysicalPauliFrame(self.block_id, self.orientation, self.module_id,
                                  self.stage_id, self.unresolved_frame.source_syndromes,
                                  xs, zs, logical, self.block_use_id)


@dataclass(frozen=True)
class LogicalReadout:
    """Historical destructive readout with raw keys from exactly one patch use."""
    module_id: str
    logical_id: str
    block_id: str
    basis: str
    orientation: int
    mode: str
    stage_id: str | None
    records: tuple[MeasurementKey, ...]
    logical_parity: ParityExpression
    checks: tuple[CheckHistory, ...]
    block_use_id: BlockUseId | None = None

    def check_matrix(self, basis):
        """Return readout check incidence in records order for the requested basis."""
        return np.array([[k.local_id in c.support for k in self.records]
                         for c in self.checks if c.basis == basis], dtype=np.uint8)


@dataclass(frozen=True)
class BellMeasurementResult:
    """Raw Bell outcomes and frame/ancestry snapshots at one teleportation."""
    composite_id: str
    logical_id: str
    data_block_id: str
    first_resource_block_id: str
    output_block_id: str
    x_readout: LogicalReadout
    z_readout: LogicalReadout
    preparation_dependencies: tuple[str, ...]
    incoming_frame: PauliFrame
    raw_byproduct: PauliFrame
    output_orientation: int
    logical_output_frame: PauliFrame
    physical_output_frame: PhysicalPauliFrame
    data_use_id: BlockUseId | None = None
    first_resource_use_id: BlockUseId | None = None
    output_use_id: BlockUseId | None = None

    @property
    def raw_x_records(self):
        """Physical X-readout keys on the consumed data use."""
        return self.x_readout.records

    @property
    def raw_z_records(self):
        """Physical Z-readout keys on the consumed first-resource use."""
        return self.z_readout.records


@dataclass(frozen=True)
class RelocationRecord:
    """Persistent logical state moves from a measured use onto an active output."""
    composite_id: str
    logical_id: str
    source_block_id: str
    output_block_id: str
    retired_logical_ids: tuple[str, ...]
    source_use_id: BlockUseId | None = None
    output_use_id: BlockUseId | None = None


@dataclass(frozen=True)
class CompositeInfo:
    """Semantic composite contract and the unique executed child-operation IDs."""
    composite_id: str
    operation_type: str
    logical_inputs: tuple[str, ...]
    logical_outputs: tuple[str, ...]
    child_operation_ids: tuple[str, ...]


@dataclass(frozen=True)
class PreparationDependencyEvent:
    """A causal edge at a primitive operation or semantic relocation boundary.

    Preparation modules are historical sources, not live logical identities.
    Only actual operand histories are joined. Consumed blocks have no outputs.
    input_use_ids/output_use_ids scope these edges to specific reset intervals;
    bare block IDs are retained for the existing physical-site audit API.
    """

    event_id: str
    operation_type: str
    input_block_ids: tuple[str, ...]
    output_block_ids: tuple[str, ...]
    preparation_dependencies: tuple[str, ...]
    input_use_ids: tuple[BlockUseId, ...] = ()
    output_use_ids: tuple[BlockUseId, ...] = ()


@dataclass(frozen=True)
class DetectorBoundaryCandidate:
    """A present global detector omitted only from an explicit stage view.

    Field names retain M5 compatibility. They always refer to canonical indices.
    """

    original_index: int
    measurement_indices: tuple[int, ...]
    stage_ids: tuple[str | None, ...]
    reason: str = "cross_stage_boundary"

    @property
    def global_index(self):
        """Canonical detector ID, including in a derived annotation view."""
        return self.original_index

    @property
    def source_stage_ids(self):
        """Semantic source regions; unrelated to TICK intervals or block epochs."""
        return self.stage_ids


# M5 import compatibility; no detectors are suppressed in the canonical circuit.
SuppressedDetector = DetectorBoundaryCandidate
