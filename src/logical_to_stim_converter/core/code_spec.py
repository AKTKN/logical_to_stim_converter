"""Immutable mathematical CSS definitions, independent of physical sites and noise."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from numpy.typing import ArrayLike, NDArray


def positive_int(value: int, name: str, minimum: int = 1) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def gf2_rank(matrix: ArrayLike) -> int:
    """Rank over GF(2), rather than over the reals."""
    a = np.array(matrix, dtype=np.uint8, copy=True)
    rank = 0
    for col in range(a.shape[1]):
        pivots = np.flatnonzero(a[rank:, col])
        if not len(pivots):
            continue
        pivot = rank + pivots[0]
        a[[rank, pivot]] = a[[pivot, rank]]
        for row in range(rank + 1, len(a)):
            if a[row, col]:
                a[row] ^= a[rank]
        rank += 1
    return rank


def _matrix(value: ArrayLike, n: int, name: str) -> NDArray[np.uint8]:
    a = np.asarray(value)
    if a.ndim != 2 or a.shape[1] != n or not np.all((a == 0) | (a == 1)):
        raise ValueError(f"{name} must be a binary matrix with {n} columns")
    # Bytes backing prevents callers from re-enabling writes on a shared array.
    return np.frombuffer(a.astype(np.uint8).tobytes(), dtype=np.uint8).reshape(a.shape)


@dataclass(frozen=True, eq=False)
class CodeSpec:
    """CSS checks and logical basis. The general constructor validates algebra.

    Distance is a declared parameter, not a computed general-code distance proof.
    The rotated-surface factory uses the known [[d*d, 1, d]] family.
    """

    name: str
    n: int
    k: int
    d: int
    H_X: ArrayLike
    H_Z: ArrayLike
    L_X: ArrayLike
    L_Z: ArrayLike
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        positive_int(self.n, "n")
        positive_int(self.k, "k", minimum=0)
        positive_int(self.d, "d")
        if not isinstance(self.name, str) or not self.name or self.k > self.n:
            raise ValueError("Invalid code name or encoded-qubit count")
        for name in ("H_X", "H_Z", "L_X", "L_Z"):
            object.__setattr__(self, name, _matrix(getattr(self, name), self.n, name))
        if self.L_X.shape[0] != self.k or self.L_Z.shape[0] != self.k:
            raise ValueError("Each logical matrix must contain k rows")
        for left, right in ((self.H_X, self.H_Z), (self.H_X, self.L_Z), (self.H_Z, self.L_X)):
            if np.any((left @ right.T) % 2):
                raise ValueError("CSS checks and logical operators must commute")
        if not np.array_equal((self.L_X @ self.L_Z.T) % 2, np.eye(self.k, dtype=int)):
            raise ValueError("Logical X/Z pairing must equal the identity over GF(2)")
        if gf2_rank(self.H_X) + gf2_rank(self.H_Z) != self.n - self.k:
            raise ValueError("Stabilizer ranks do not give the declared k")
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.metadata.items()):
            raise ValueError("Code metadata must map strings to strings")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def rotated_surface(cls, distance: int) -> "CodeSpec":
        """Odd square distance; mathematical columns run north then east.

        Logical X follows the southern row; logical Z follows the western column.
        No physical indices or ancilla schedule are included in the definition.
        """
        positive_int(distance, "distance", minimum=3)
        if distance % 2 != 1:
            raise ValueError("Rotated surface distance must be odd")
        d = distance
        checks = []
        for basis in "XZ":
            rows = []
            xs = range(0, 2 * d + 1, 2) if basis == "X" else range(2, 2 * d, 2)
            for x in xs:
                ys = range(2 + x % 4, 2 * d, 4) if basis == "X" else range(x % 4, 2 * d + 1, 4)
                for y in ys:
                    row = np.zeros(d * d, dtype=np.uint8)
                    for dx in (-1, 1):
                        for dy in (-1, 1):
                            a, b = x + dx, y + dy
                            if 0 < a < 2 * d and 0 < b < 2 * d:
                                row[(a // 2) * d + b // 2] = 1
                    rows.append(row)
            checks.append(rows)
        lx = np.zeros((1, d * d), dtype=np.uint8)
        lz = np.zeros_like(lx)
        lx[0, ::d] = 1
        lz[0, :d] = 1
        return cls(
            f"rotated_surface_d{d}",
            d * d,
            1,
            d,
            *checks,
            lx,
            lz,
            metadata={"family": "rotated_surface"},
        )
