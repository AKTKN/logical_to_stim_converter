"""Decoder-independent preparation, readout, stage, and relocation contracts."""

from dataclasses import dataclass

import numpy as np

from .code_frame import validate_orientation
from .compiler_context import MeasurementKey, ParityExpression, PauliFrame


@dataclass(frozen=True)
class CheckHistory:
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
    """

    block_id: str
    orientation: int
    preparation_module_id: str
    stage_id: str | None
    source_syndromes: tuple[MeasurementKey, ...]
    x_support: tuple[str, ...] | None = None
    z_support: tuple[str, ...] | None = None
    logical_contribution: PauliFrame = PauliFrame()

    def __post_init__(self):
        validate_orientation(self.orientation)
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
        return self.x_support is not None


@dataclass(frozen=True)
class PreparationInfo:
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

    @property
    def rounds(self):
        return len(self.checks[0].measurements)

    @property
    def gauge_measurements(self):
        return tuple(c.measurements[0] for c in self.checks if c.basis != self.basis)

    @property
    def unresolved_frame(self):
        return PhysicalPauliFrame(self.block_id, self.orientation, self.module_id,
                                  self.stage_id, tuple(c.measurements[-1] for c in self.checks))

    def check_matrix(self, basis):
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
                                  xs, zs, logical)


@dataclass(frozen=True)
class LogicalReadout:
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

    def check_matrix(self, basis):
        return np.array([[k.local_id in c.support for k in self.records]
                         for c in self.checks if c.basis == basis], dtype=np.uint8)


@dataclass(frozen=True)
class BellMeasurementResult:
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

    @property
    def raw_x_records(self):
        return self.x_readout.records

    @property
    def raw_z_records(self):
        return self.z_readout.records


@dataclass(frozen=True)
class RelocationRecord:
    composite_id: str
    logical_id: str
    source_block_id: str
    output_block_id: str
    retired_logical_ids: tuple[str, ...]


@dataclass(frozen=True)
class CompositeInfo:
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
    """

    event_id: str
    operation_type: str
    input_block_ids: tuple[str, ...]
    output_block_ids: tuple[str, ...]
    preparation_dependencies: tuple[str, ...]


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
        return self.original_index

    @property
    def source_stage_ids(self):
        return self.stage_ids


# M5 import compatibility; no detectors are suppressed in the canonical circuit.
SuppressedDetector = DetectorBoundaryCandidate
