"""Reusable linear offline Clifford feedback, with caller-owned batch state."""

from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from .errors import DecoderViewError, SourceMismatchError
from .records import GF2Map, binary_batch


def readonly(values):
    a = np.asarray(values, dtype=np.bool_)
    return np.frombuffer(a.tobytes(), dtype=np.bool_).reshape(a.shape)


@dataclass(frozen=True)
class CorrectionBatch:
    """External hypotheses in a plan boundary's declared physical/record ordering."""

    source_fingerprint: str
    boundary_id: str
    bits: np.ndarray

    def __post_init__(self):
        if not self.source_fingerprint or not self.boundary_id:
            raise DecoderViewError("Corrections need source and boundary provenance")
        a = np.asarray(self.bits)
        if a.ndim != 2:
            raise DecoderViewError("Corrections must be a binary batch")
        object.__setattr__(self, "bits", readonly(binary_batch(a, a.shape[1], "corrections")))


@dataclass(frozen=True)
class FrameBoundary:
    boundary_id: str
    kind: str
    block_id: str
    orientation: int
    data_ids: tuple[str, ...]
    input_ids: tuple[str, ...]
    record_map: GF2Map
    final_x_map: GF2Map
    final_z_map: GF2Map


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

    @property
    def boundary_by_id(self):
        return MappingProxyType({b.boundary_id: b for b in self.boundaries})

    def start(self, raw, *, source_fingerprint):
        if source_fingerprint != self.source_fingerprint:
            raise SourceMismatchError("Frame plan belongs to a different physical source")
        return OfflineFrameBatch(self, raw)


class OfflineFrameBatch:
    """One caller-owned analysis, with original records preserved and isolated."""

    def __init__(self, plan, raw):
        self.plan = plan
        self.raw_measurements = readonly(binary_batch(raw, plan.raw_record_map.input_size))
        self._records = plan.raw_record_map.apply(self.raw_measurements) ^ plan.constant_records
        self._x = plan.raw_final_x_map.apply(self.raw_measurements) ^ plan.constant_final_x
        self._z = plan.raw_final_z_map.apply(self.raw_measurements) ^ plan.constant_final_z
        self._applied = set()

    @property
    def interpreted_measurements(self):
        return readonly(self._records)

    @property
    def final_x(self):
        return readonly(self._x)

    @property
    def final_z(self):
        return readonly(self._z)

    def apply(self, correction):
        if not isinstance(correction, CorrectionBatch):
            raise DecoderViewError("Expected a source-bound CorrectionBatch")
        if correction.source_fingerprint != self.plan.source_fingerprint:
            raise SourceMismatchError("Correction belongs to a different physical source")
        boundary = self.plan.boundary_by_id.get(correction.boundary_id)
        if boundary is None or boundary.boundary_id in self._applied:
            raise DecoderViewError("Unknown or already applied correction boundary")
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
