"""Direct Stim oracle. No converter imports, circuits, metadata or noise factories.

Coordinates, plaquettes, logical strings and the written 20-moment schedule are
constructed here from elementary geometry. This module is also usable when the
converter is unavailable.
"""

from dataclasses import dataclass

import stim

Coord = tuple[int, int]


@dataclass(frozen=True)
class Check:
    basis: str
    coordinate: Coord
    support: tuple[Coord, ...]


@dataclass(frozen=True)
class Geometry:
    distance: int
    data: tuple[Coord, ...]
    checks: tuple[Check, ...]

    @property
    def sites(self):
        return self.data + tuple(c.coordinate for c in self.checks)

    def logical(self, basis):
        return tuple(q for q in self.data if q[basis == "X"] == 1)


def geometry(distance: int) -> Geometry:
    if type(distance) is not int or distance not in (3, 5):
        raise ValueError("Golden memory covers only distances 3 and 5")
    d = distance
    data = tuple((2 * col + 1, 2 * row + 1) for col in range(d) for row in range(d))
    checks = []
    # Colour every vertex of the dual square grid. X boundaries are vertical;
    # Z boundaries are horizontal. Corners and the other boundary colour are absent.
    for col in range(d + 1):
        for row in range(d + 1):
            basis = "X" if (col + row) % 2 else "Z"
            if basis == "X" and not 0 < row < d:
                continue
            if basis == "Z" and not 0 < col < d:
                continue
            center = (2 * col, 2 * row)
            support = tuple(q for q in data if all(abs(q[k] - center[k]) == 1 for k in (0, 1)))
            checks.append(Check(basis, center, support))
    return Geometry(d, data, tuple(sorted(checks, key=lambda c: (c.basis, c.coordinate))))


@dataclass(frozen=True)
class ReferenceNoise:
    reset: float = 0
    one_qubit: float = 0
    two_qubit: float = 0
    measurement: float = 0
    idle: float = 0


FULL_NOISE = ReferenceNoise(0.01, 0.02, 0.03, 0.04, 0.05)


def build_reference(distance: int, basis: str, noise: ReferenceNoise = ReferenceNoise()):
    """Author exactly three rounds, including manual per-target idle channels."""
    if basis not in ("X", "Z"):
        raise ValueError("Memory basis must be X or Z")
    g = geometry(distance)
    indices = {q: i for i, q in enumerate(g.sites)}
    circuit = stim.Circuit()
    for q, index in indices.items():
        circuit.append("QUBIT_COORDS", [index], q)
    records = {}
    measurement_count = 0

    def moment(actions, *, final=False):
        nonlocal measurement_count
        used = set()
        for gate, coordinates, keys in actions:
            targets = [indices[q] for q in coordinates]
            if used.intersection(coordinates):
                raise AssertionError("Independent schedule has overlapping gates")
            used.update(coordinates)
            args = [noise.measurement] if gate in ("M", "MX") and noise.measurement else []
            circuit.append(gate, targets, args)
            if gate in ("R", "RX") and noise.reset:
                circuit.append("X_ERROR" if gate == "R" else "Z_ERROR", targets, noise.reset)
            if gate == "CX" and noise.two_qubit:
                circuit.append("DEPOLARIZE2", targets, noise.two_qubit)
            for key in keys:
                records[key] = measurement_count
                measurement_count += 1
        if noise.idle:
            circuit.append(
                "DEPOLARIZE1", [indices[q] for q in g.sites if q not in used], noise.idle
            )
        if not final:
            circuit.append("TICK")

    moment([("RX" if basis == "X" else "R", g.data, ())])
    # Specified displacements from ancilla, independent of production scheduling code.
    directions = {
        "X": ((-1, 1), (-1, -1), (1, 1), (1, -1)),
        "Z": ((-1, 1), (1, 1), (-1, -1), (1, -1)),
    }
    for round_index in (1, 2, 3):
        moment(
            [
                (
                    "RX" if b == "X" else "R",
                    tuple(c.coordinate for c in g.checks if c.basis == b),
                    (),
                )
                for b in "XZ"
            ]
        )
        for layer in range(4):
            pairs = []
            for check in g.checks:
                dx, dy = directions[check.basis][layer]
                q = (check.coordinate[0] + dx, check.coordinate[1] + dy)
                if q in check.support:
                    pairs.extend(
                        (check.coordinate, q) if check.basis == "X" else (q, check.coordinate)
                    )
            moment([("CX", pairs, ())])
        moment(
            [
                (
                    "MX" if b == "X" else "M",
                    tuple(c.coordinate for c in g.checks if c.basis == b),
                    tuple(
                        ("check", b, c.coordinate, round_index) for c in g.checks if c.basis == b
                    ),
                )
                for b in "XZ"
            ]
        )
    moment(
        [("MX" if basis == "X" else "M", g.data, tuple(("readout", basis, q) for q in g.data))],
        final=True,
    )
    # Append independently defined parities using absolute records, never production rec offsets.
    for check in g.checks:
        for t in (1, 2, 3, 4):
            if t in (1, 4) and check.basis != basis:
                continue
            keys = [("check", check.basis, check.coordinate, min(t, 3))]
            if t in (2, 3):
                keys.append(("check", check.basis, check.coordinate, t - 1))
            if t == 4:
                keys.extend(("readout", basis, q) for q in check.support)
            circuit.append(
                "DETECTOR",
                [stim.target_rec(records[k] - measurement_count) for k in keys],
                [*check.coordinate, t],
            )
    circuit.append(
        "OBSERVABLE_INCLUDE",
        [
            stim.target_rec(records[("readout", basis, q)] - measurement_count)
            for q in g.logical(basis)
        ],
        0,
    )
    return circuit
