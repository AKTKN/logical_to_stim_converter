"""Pure batched GF(2) maps and caller-defined software record frames."""

from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import csr_matrix

from .errors import DecoderViewError, SourceMismatchError


def binary_batch(value, width, name="samples"):
    a = np.asarray(value)
    if (
        a.ndim != 2
        or a.shape[1] != width
        or a.dtype.kind not in "biu"
        or not np.isin(a, (0, 1)).all()
    ):
        raise DecoderViewError(f"{name} must be a binary (shots, {width}) matrix; no bit packing")
    return a.astype(np.bool_, copy=False)


def ordered_ids(values, size, name):
    values = tuple(values)
    if any(
        isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or not 0 <= v < size
        for v in values
    ):
        raise DecoderViewError(f"Invalid global {name} ID; expected integers in [0, {size})")
    values = tuple(int(v) for v in values)
    if len(set(values)) != len(values):
        raise DecoderViewError(f"Duplicate {name} IDs")
    return values


@dataclass(frozen=True)
class GF2Map:
    """An immutable sparse map, with one tuple of input indices per output bit.

    apply maps (shots, input_size) to (shots, len(supports)). Multiplication is
    integer arithmetic reduced modulo two, including more than 255 input bits.
    The public incidence_matrix property returns a copy, never internal storage.
    """

    input_size: int
    supports: tuple[tuple[int, ...], ...]
    _matrix: csr_matrix = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.input_size) is not int or self.input_size < 0:
            raise DecoderViewError("GF2Map input_size must be a nonnegative integer")
        supports = tuple(ordered_ids(s, self.input_size, "GF(2) input") for s in self.supports)
        object.__setattr__(self, "supports", supports)
        rows = [i for s in supports for i in s]
        cols = [j for j, s in enumerate(supports) for _ in s]
        matrix = csr_matrix(
            (np.ones(len(rows), dtype=np.uint8), (rows, cols)),
            shape=(self.input_size, len(supports)),
            dtype=np.uint8,
        )
        for a in (matrix.data, matrix.indices, matrix.indptr):
            a.flags.writeable = False
        object.__setattr__(self, "_matrix", matrix)

    @classmethod
    def from_matrix(cls, matrix):
        """Wrap a binary (input_bits, output_bits) matrix."""
        a = np.asarray(matrix)
        if a.ndim != 2:
            raise DecoderViewError("GF(2) matrix must have two dimensions")
        a = binary_batch(a, a.shape[1], "GF(2) matrix")
        return cls(a.shape[0], tuple(tuple(np.flatnonzero(a[:, j])) for j in range(a.shape[1])))

    @property
    def incidence_matrix(self):
        return self._matrix.copy()

    def apply(self, values):
        a = binary_batch(values, self.input_size)
        return np.asarray(a.astype(np.uint8) @ self._matrix, dtype=np.uint8) % 2 != 0


def apply_record_flips(raw_measurements, flips):
    """XOR global record masks into a new array; shared 1D masks may broadcast."""
    raw = np.asarray(raw_measurements)
    if raw.ndim != 2:
        raise DecoderViewError("Raw measurements must be a matrix")
    raw = binary_batch(raw, raw.shape[1], "raw measurements")
    f = np.asarray(flips)
    if f.ndim == 1:
        f = f[None, :]
    f = binary_batch(f, raw.shape[1], "record flips")
    if f.shape[0] not in (1, raw.shape[0]):
        raise DecoderViewError("Record flips and raw measurements have different shot counts")
    return raw ^ f


@dataclass(frozen=True)
class RecordFlipMap:
    """External correction bits -> global raw-record flips, with source identity.

    The map is supplied by the caller, never inferred by a decoder in this
    package. input_ids identifies each correction bit; map supports identify the
    input bits flipping each global measurement. It contains no per-shot state.
    """

    source_fingerprint: str
    input_ids: tuple[str, ...]
    transform: GF2Map

    def __post_init__(self):
        ids = tuple(self.input_ids)
        if (
            not self.source_fingerprint
            or len(ids) != self.transform.input_size
            or len(set(ids)) != len(ids)
            or any(not isinstance(i, str) or not i for i in ids)
        ):
            raise DecoderViewError(
                "Record map requires distinct input IDs and a source fingerprint"
            )
        object.__setattr__(self, "input_ids", ids)

    def apply(self, raw_measurements, correction_bits, *, source_fingerprint):
        if source_fingerprint != self.source_fingerprint:
            raise SourceMismatchError("Record correction map belongs to a different source")
        raw = binary_batch(raw_measurements, len(self.transform.supports), "raw measurements")
        bits = binary_batch(correction_bits, len(self.input_ids), "correction bits")
        if len(bits) != len(raw):
            raise DecoderViewError("Correction bits and measurements have different shot counts")
        return apply_record_flips(raw, self.transform.apply(bits))
