"""Independent mathematical three-patch Knill protocol and physical role spec.

This research oracle imports no installed converter construction or noise code.
The dual-grid geometry is the independently authored golden-memory geometry.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from validation.golden_memory.reference_same_schedule import Geometry, geometry

Coord = tuple[int, int]
Site = tuple[str, Coord]
RecordKey = tuple
PATCHES = ("D", "A", "B")
DIRECTIONS = {
    "X": ((-1, 1), (-1, -1), (1, 1), (1, -1)),
    "Z": ((-1, 1), (1, 1), (-1, -1), (1, -1)),
}
OPERATION_TYPES = MappingProxyType(
    {
        "D.init": "LogicalInit",
        "A.prep": "LogicalInit",
        "B.prep": "LogicalInit",
        "Bell.entangle": "TransversalCNOT",
        "Bell.measure.cnot": "TransversalCNOT",
        "D.bell_readout": "LogicalMeasure",
        "A.bell_readout": "LogicalMeasure",
        "B.readout": "LogicalMeasure",
    }
)


@dataclass(frozen=True)
class Action:
    gate: str
    targets: tuple[Site, ...]
    operation: str
    keys: tuple[RecordKey, ...] = ()


@dataclass(frozen=True)
class ReferenceMoment:
    actions: tuple[Action, ...]
    active_patches: tuple[str, ...]
    stage: str
    operations: Mapping[str, str]

    def __post_init__(self):
        object.__setattr__(self, "operations", MappingProxyType(dict(self.operations)))

    @property
    def used_sites(self):
        return frozenset(s for a in self.actions for s in a.targets)


def absolute_coordinate(distance: int, patch: str, coordinate: Coord) -> Coord:
    return (coordinate[0] + PATCHES.index(patch) * (2 * distance + 2), coordinate[1])


def protocol_geometry(distance: int) -> Geometry:
    return geometry(distance)


def check_key(patch: str, check, round_index: int) -> RecordKey:
    return ("check", patch, check.basis, check.coordinate, round_index)


def readout_key(patch: str, basis: str, coordinate: Coord) -> RecordKey:
    return ("readout", patch, basis, coordinate)
