"""Local rotated-surface geometry and the four-layer N/Z CNOT schedule."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from .code_spec import CodeSpec, gf2_rank

INTERACTION_ORDER = MappingProxyType(
    {
        "X": ("NW", "SW", "NE", "SE"),
        "Z": ("NW", "NE", "SW", "SE"),
    }
)
DIRECTIONS = MappingProxyType({"NW": -1 + 1j, "SW": -1 - 1j, "NE": 1 + 1j, "SE": 1 - 1j})


@dataclass(frozen=True)
class Check:
    check_id: str
    basis: str
    ancilla: str
    support: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "support", tuple(self.support))


@dataclass(frozen=True)
class PhysicalLayout:
    """Local keys are scoped to a block; data_ids order defines code columns."""

    data_ids: tuple[str, ...]
    checks: tuple[Check, ...]
    coordinates: Mapping[str, complex]
    cnot_layers: tuple[tuple[tuple[str, str], ...], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_ids", tuple(self.data_ids))
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "coordinates", MappingProxyType(dict(self.coordinates)))
        object.__setattr__(
            self,
            "cnot_layers",
            tuple(tuple(tuple(pair) for pair in layer) for layer in self.cnot_layers),
        )
        ids = self.qubit_ids
        if not ids or len(set(ids)) != len(ids) or set(ids) != set(self.coordinates):
            raise ValueError("Every distinct local site must have exactly one coordinate")
        if len(set(self.coordinates.values())) != len(ids) or any(
            not np.isfinite(complex(q).real) or not np.isfinite(complex(q).imag)
            for q in self.coordinates.values()
        ):
            raise ValueError("Local coordinates must be finite and distinct")
        if len({c.check_id for c in self.checks}) != len(self.checks):
            raise ValueError("Check identifiers must be distinct")
        expected = Counter()
        for c in self.checks:
            if (
                c.basis not in ("X", "Z")
                or not c.support
                or len(set(c.support)) != len(c.support)
                or not set(c.support) <= set(self.data_ids)
            ):
                raise ValueError("Invalid check basis or data support")
            for data in c.support:
                expected[(c.ancilla, data) if c.basis == "X" else (data, c.ancilla)] += 1
        if len(self.cnot_layers) != 4:
            raise ValueError("A syndrome round must have four CNOT layers")
        actual = Counter(pair for layer in self.cnot_layers for pair in layer)
        if actual != expected:
            raise ValueError("CNOT schedule does not implement each check support exactly once")
        for layer_index, layer in enumerate(self.cnot_layers):
            used = [q for pair in layer for q in pair]
            if len(set(used)) != len(used):
                raise ValueError("A qubit participates in two CNOTs within one layer")
            for control, target in layer:
                c = next(c for c in self.checks if c.ancilla in (control, target))
                data = target if c.basis == "X" else control
                delta = self.coordinates[data] - self.coordinates[c.ancilla]
                if delta != DIRECTIONS[INTERACTION_ORDER[c.basis][layer_index]]:
                    raise ValueError("CNOT schedule must follow the N/Z interaction order")

    @property
    def ancilla_ids(self) -> tuple[str, ...]:
        return tuple(c.ancilla for c in self.checks)

    @property
    def qubit_ids(self) -> tuple[str, ...]:
        return self.data_ids + self.ancilla_ids

    @property
    def connectivity(self) -> frozenset[tuple[str, str]]:
        return frozenset((c.ancilla, q) for c in self.checks for q in c.support)

    def data_column(self, local_id: str) -> int:
        try:
            return self.data_ids.index(local_id)
        except ValueError as ex:
            raise KeyError(local_id) from ex

    def check_for_ancilla(self, local_id: str) -> Check:
        for check in self.checks:
            if check.ancilla == local_id:
                return check
        raise KeyError(local_id)

    def validate_code(self, code: CodeSpec) -> None:
        if len(self.data_ids) != code.n:
            raise ValueError("Layout data count does not match CodeSpec")
        for basis, matrix in (("X", code.H_X), ("Z", code.H_Z)):
            checks = [c for c in self.checks if c.basis == basis]
            if len(checks) != len(matrix) or gf2_rank(matrix) != len(matrix):
                raise ValueError("Layout requires one ancilla per independent check")
            for check, row in zip(checks, matrix, strict=True):
                support = {self.data_ids[i] for i in np.flatnonzero(row)}
                if support != set(check.support):
                    raise ValueError("Layout support does not match mathematical checks")

    @classmethod
    def rotated_surface(cls, code: CodeSpec) -> "PhysicalLayout":
        d = code.d
        reference = CodeSpec.rotated_surface(d)
        if any(
            not np.array_equal(getattr(code, key), getattr(reference, key))
            for key in ("H_X", "H_Z", "L_X", "L_Z")
        ) or (code.n, code.k) != (d * d, 1):
            raise ValueError("Backend requires the factory's rotated-surface logical basis")
        data = tuple(f"D{i + 1}" for i in range(d * d))
        coords = {
            data[x * d + y]: complex(2 * x + 1, 2 * y + 1) for x in range(d) for y in range(d)
        }
        checks = []
        for basis in "XZ":
            positions = (
                [complex(x, y) for x in range(0, 2 * d + 1, 2) for y in range(2 + x % 4, 2 * d, 4)]
                if basis == "X"
                else [complex(x, y) for x in range(2, 2 * d, 2) for y in range(x % 4, 2 * d + 1, 4)]
            )
            for index, pos in enumerate(positions):
                anc = f"{basis}{index + 1}"
                support = tuple(q for q in data if coords[q] - pos in DIRECTIONS.values())
                checks.append(Check(anc, basis, anc, support))
                coords[anc] = pos
        layers = []
        for layer in range(4):
            pairs = []
            for c in checks:
                delta = DIRECTIONS[INTERACTION_ORDER[c.basis][layer]]
                for q in c.support:
                    if coords[q] == coords[c.ancilla] + delta:
                        pairs.append((c.ancilla, q) if c.basis == "X" else (q, c.ancilla))
            layers.append(tuple(pairs))
        result = cls(data, tuple(checks), coords, tuple(layers))
        result.validate_code(code)
        return result
