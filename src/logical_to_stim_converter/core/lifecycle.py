"""Immutable identities and history for explicitly reused physical code patches.

Block IDs name fixed qubits/layouts. Logical IDs name states, including temporary
resources. A use begins with a real reset; binding alone only reserves a patch.
Module IDs name executed primitives, while stages name semantic protocol regions.
"""

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class BlockUseId:
    """One reset-to-destructive-readout occupancy of a fixed physical patch.

    ``epoch`` is a per-patch generation starting at zero, independent of physical
    qubit indices, syndrome rounds, stages and physical TICK intervals.
    """

    block_id: str
    epoch: int = 0

    def __post_init__(self):
        if not isinstance(self.block_id, str) or not self.block_id:
            raise ValueError("A block use requires a nonempty physical block ID")
        if type(self.epoch) is not int or self.epoch < 0:
            raise ValueError("epoch must be a nonnegative integer occupancy generation")


@dataclass(frozen=True)
class PatchBindingEvent:
    """Zero-duration reservation; previous_use is absent before the first reset."""

    event_id: str
    logical_id: str
    block_id: str
    previous_use: BlockUseId | None = None


@dataclass(frozen=True)
class UseOwnerEvent:
    """Initial owner or teleportation rename at a primitive/composite boundary."""

    event_id: str
    logical_id: str


@dataclass(frozen=True)
class BlockUseInfo:
    """Immutable physical occupancy history, including open uses.

    Measurement and TimeLayer intervals are zero-based and half-open. The end
    is None for an active use. Owner events preserve temporary resource names
    when teleportation transfers a persistent logical state onto their patch.
    """

    use_id: BlockUseId
    reset_module_id: str
    terminal_module_id: str | None = None
    logical_owner_history: tuple[UseOwnerEvent, ...] = ()
    measurement_start: int = 0
    measurement_stop: int | None = None
    time_layer_start: int = 0
    time_layer_stop: int | None = None
