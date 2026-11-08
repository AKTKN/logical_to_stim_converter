"""Reusable linear offline Clifford feedback, with caller-owned batch state."""

from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from ..core.code_frame import validate_orientation
from ..core.lifecycle import BlockUseId
from .errors import DecoderViewError, SourceMismatchError
from .records import GF2Map, binary_batch


def readonly(values):
    """Freeze a binary batch in immutable owned storage, independent of the caller."""
    a = np.asarray(values, dtype=np.bool_)
    return np.frombuffer(a.tobytes(), dtype=np.bool_).reshape(a.shape)


@dataclass(frozen=True)
class CorrectionBatch:
    """External hypotheses in a unique module's physical/record ordering.

    Optional block_use_id/input_ids make occupancy and column ordering explicit;
    omitted fields retain the existing module-bound API and declared plan order.
    """

    source_fingerprint: str
    boundary_id: str
    bits: np.ndarray
    block_use_id: BlockUseId | None = None
    input_ids: tuple[str, ...] | None = None

    def __post_init__(self):
        if not self.source_fingerprint or not self.boundary_id:
            raise DecoderViewError("Corrections need source and boundary provenance")
        a = np.asarray(self.bits)
        if a.ndim != 2:
            raise DecoderViewError("Corrections must be a binary batch")
        object.__setattr__(self, "bits", readonly(binary_batch(a, a.shape[1], "corrections")))
        if self.block_use_id is not None and not isinstance(self.block_use_id, BlockUseId):
            raise DecoderViewError("Correction use must be a BlockUseId")
        if self.input_ids is not None:
            ids = tuple(self.input_ids)
            if (len(ids) != a.shape[1]
                    or any(not isinstance(i, str) or not i for i in ids)
                    or len(set(ids)) != len(ids)):
                raise DecoderViewError("Correction input IDs must label every column uniquely")
            object.__setattr__(self, "input_ids", ids)


@dataclass(frozen=True)
class FrameBoundary:
    """One historical module/use correction map in fixed physical data/record order."""
    boundary_id: str
    kind: str
    block_id: str
    orientation: int
    data_ids: tuple[str, ...]
    input_ids: tuple[str, ...]
    record_map: GF2Map
    final_x_map: GF2Map
    final_z_map: GF2Map
    block_use_id: BlockUseId | None = None

    def __post_init__(self):
        validate_orientation(self.orientation)
        if self.block_use_id is not None and (
                not isinstance(self.block_use_id, BlockUseId)
                or self.block_use_id.block_id != self.block_id):
            raise DecoderViewError("Frame boundary physical use disagrees with its block")
        data = tuple(self.data_ids)
        if (not data or any(not isinstance(q, str) or not q for q in data)
                or len(set(data)) != len(data)):
            raise DecoderViewError("Frame boundary needs distinct physical data IDs")
        if self.kind not in ("physical", "readout"):
            raise DecoderViewError("Frame boundary must describe physical or readout hypotheses")
        expected = (tuple(f"{axis}:{q}" for axis in "XZ" for q in data)
                    if self.kind == "physical" else tuple(f"record:{q}" for q in data))
        if tuple(self.input_ids) != expected:
            raise DecoderViewError("Frame boundary X/Z or record ordering disagrees")
        if any(m.input_size != len(expected)
               for m in (self.record_map, self.final_x_map, self.final_z_map)):
            raise DecoderViewError("Frame boundary maps disagree with their physical input order")
        object.__setattr__(self, "data_ids", data)
        object.__setattr__(self, "input_ids", expected)


@dataclass(frozen=True)
class OfflineFramePlan:
    """Immutable affine transducer, built once, with no decoder or shot state.

    Bell byproducts are provisional linear feedback from interpreted records.
    Later readout hypotheses update that feedback by XOR delta exactly once.
    physical boundary inputs are X(data_ids), then Z(data_ids); readout inputs
    are measurement flips in LogicalReadout.records order. Virtual Paulis are
    an affine constant. All maps include the actual later H/CX pairings.
    """

    source_fingerprint: str
    raw_record_map: GF2Map
    constant_records: tuple[bool, ...]
    raw_final_x_map: GF2Map
    raw_final_z_map: GF2Map
    constant_final_x: tuple[bool, ...]
    constant_final_z: tuple[bool, ...]
    boundaries: tuple[FrameBoundary, ...]

    def __post_init__(self):
        boundaries = tuple(self.boundaries)
        nm, nq = len(self.constant_records), len(self.constant_final_x)
        if (not self.source_fingerprint or self.raw_record_map.input_size != nm
                or len(self.raw_record_map.supports) != nm
                or len(self.constant_final_z) != nq
                or len({b.boundary_id for b in boundaries}) != len(boundaries)):
            raise DecoderViewError("Frame plan source, records or boundary identities disagree")
        for m in (self.raw_final_x_map, self.raw_final_z_map):
            if m.input_size != nm or len(m.supports) != nq:
                raise DecoderViewError("Frame plan physical output dimensions disagree")
        for b in boundaries:
            if (len(b.record_map.supports) != nm or len(b.final_x_map.supports) != nq
                    or len(b.final_z_map.supports) != nq):
                raise DecoderViewError("Frame boundary output dimensions disagree with the source")
        object.__setattr__(self, "boundaries", boundaries)

    @property
    def boundary_by_id(self):
        """Unique module IDs retain boundaries from every physical occupancy."""
        return MappingProxyType({b.boundary_id: b for b in self.boundaries})

    def start(self, raw, *, source_fingerprint):
        """Start isolated offline interpretation of one immutable physical sample batch."""
        if source_fingerprint != self.source_fingerprint:
            raise SourceMismatchError("Frame plan belongs to a different physical source")
        return OfflineFrameBatch(self, raw)


class OfflineFrameBatch:
    """One caller-owned analysis, with original records preserved and isolated."""

    def __init__(self, plan, raw):
        """Apply provisional classical Bell feedback without modifying physical samples."""
        self.plan = plan
        self.raw_measurements = readonly(binary_batch(raw, plan.raw_record_map.input_size))
        self._records = plan.raw_record_map.apply(self.raw_measurements) ^ plan.constant_records
        self._x = plan.raw_final_x_map.apply(self.raw_measurements) ^ plan.constant_final_x
        self._z = plan.raw_final_z_map.apply(self.raw_measurements) ^ plan.constant_final_z
        self._applied = set()

    @property
    def interpreted_measurements(self):
        """Immutable current records after all selected software corrections."""
        return readonly(self._records)

    @property
    def final_x(self):
        """Residual physical X support in global Stim wire order, after real resets."""
        return readonly(self._x)

    @property
    def final_z(self):
        """Residual physical Z support in global Stim wire order, after real resets."""
        return readonly(self._z)

    def apply(self, correction):
        """Apply one source/use/ordering-checked hypothesis exactly once at its module."""
        if not isinstance(correction, CorrectionBatch):
            raise DecoderViewError("Expected a source-bound CorrectionBatch")
        if correction.source_fingerprint != self.plan.source_fingerprint:
            raise SourceMismatchError("Correction belongs to a different physical source")
        boundary = self.plan.boundary_by_id.get(correction.boundary_id)
        if boundary is None or boundary.boundary_id in self._applied:
            raise DecoderViewError("Unknown or already applied correction boundary")
        if correction.block_use_id is not None and correction.block_use_id != boundary.block_use_id:
            raise DecoderViewError("Correction belongs to a different physical use")
        if correction.input_ids is not None and correction.input_ids != boundary.input_ids:
            raise DecoderViewError("Correction X/Z or record input ordering disagrees")
        bits = binary_batch(correction.bits, len(boundary.input_ids), "correction bits")
        if len(bits) != len(self.raw_measurements):
            raise DecoderViewError("Correction shot count disagrees")
        self._records ^= boundary.record_map.apply(bits)
        self._x ^= boundary.final_x_map.apply(bits)
        self._z ^= boundary.final_z_map.apply(bits)
        self._applied.add(boundary.boundary_id)

    def events(self, view):
        """Recompute from current interpreted records, never stale physical events."""
        return view.events_from_raw(self._records, source_fingerprint=self.plan.source_fingerprint)
