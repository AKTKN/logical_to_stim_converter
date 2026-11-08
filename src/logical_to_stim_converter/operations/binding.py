"""Explicit logical reservations, separate from executable quantum operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BindPatch:
    """Reserve a specified available patch for a fresh logical-state handle.

    Both arguments are nonempty string IDs. This compile-time directive has no
    physical duration, reset, measurement, noise or ModuleId. LogicalInit starts
    the actual occupancy epoch. Retired logical names cannot be reused.
    """

    logical_id: str
    physical_block_id: str

    def __post_init__(self):
        for value in (self.logical_id, self.physical_block_id):
            if not isinstance(value, str) or not value:
                raise ValueError("BindPatch requires nonempty logical and physical block IDs")
