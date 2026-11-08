"""Per-compilation lifecycle, symbolic records, frames, and physical-time metadata."""

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType

import numpy as np
import stim

from .lifecycle import BlockUseId, BlockUseInfo, PatchBindingEvent, UseOwnerEvent
from .logical_block import GlobalSiteId, LogicalBlock


class BlockStatus(str, Enum):
    """Last physical-use state; MEASURED remains until a fresh use is reserved."""
    UNINITIALIZED = "uninitialized"
    ACTIVE = "active"
    MEASURED = "measured"


@dataclass(frozen=True)
class MeasurementKey:
    """Raw-record identity within one patch occupancy, independent of rec offset."""

    block_id: str
    local_id: str
    kind: str
    round_index: int | None = None
    epoch: int = 0

    def __post_init__(self):
        BlockUseId(self.block_id, self.epoch)

    @property
    def block_use_id(self):
        """Return the reset interval that produced this physical measurement."""
        return BlockUseId(self.block_id, self.epoch)


@dataclass(frozen=True)
class ParityExpression:
    """Affine GF(2) value over symbolic measurement keys, never guessed shot values."""

    terms: tuple[MeasurementKey, ...] = ()
    constant: bool = False

    def __post_init__(self):
        if type(self.constant) not in (bool, int) or self.constant not in (0, 1):
            raise ValueError("A parity constant must be a binary value")
        parity = set()
        for term in self.terms:
            if not isinstance(term, MeasurementKey):
                raise ValueError("Parity terms must be symbolic MeasurementKey values")
            parity.symmetric_difference_update((term,))
        object.__setattr__(self, "terms", tuple(sorted(parity, key=repr)))
        object.__setattr__(self, "constant", bool(self.constant))

    def __xor__(self, other):
        """Combine symbolic classical parities, cancelling repeated raw keys."""
        if isinstance(other, (bool, int)):
            other = ParityExpression(constant=other)
        if not isinstance(other, ParityExpression):
            return NotImplemented
        return ParityExpression(self.terms + other.terms, self.constant ^ other.constant)

    def evaluate(self, measurements, key_to_index):
        """Evaluate a bit or batch parity using explicit semantic-to-record indices."""
        samples = np.asarray(measurements, dtype=np.bool_)
        result = np.full(samples.shape[:-1], self.constant, dtype=np.bool_)
        for key in self.terms:
            result ^= samples[..., key_to_index[key]]
        return result


@dataclass(frozen=True)
class MeasurementInfo:
    """Historical raw measurement and its absolute zero-based Stim record index."""
    key: MeasurementKey
    index: int
    logical_id: str
    basis: str
    module_id: str
    time_layer: int
    stage_id: str | None = None


@dataclass(frozen=True)
class DetectorInfo:
    """Canonical deterministic parity with physical and semantic provenance."""
    index: int
    coordinates: tuple[float, ...]
    measurement_indices: tuple[int, ...]
    measurement_keys: tuple[MeasurementKey, ...]
    block_id: str
    check_id: str
    supporting_block_ids: tuple[str, ...] = ()
    stage_id: str | None = None
    source_stage_ids: tuple[str | None, ...] = ()
    crosses_decoder_boundary: bool = False
    anchor_module_id: str = ""
    basis: str = ""
    physical_support: tuple[GlobalSiteId, ...] = ()

    @property
    def anchor_block_id(self):
        """Physical patch whose latest check anchors this deterministic relation."""
        return self.block_id

    @property
    def anchor_check_id(self):
        """Local check ID at the semantic detector anchor."""
        return self.check_id


@dataclass(frozen=True)
class ObservableInfo:
    """Deterministic logical readout, independent of subsequent patch occupancy."""
    index: int
    logical_id: str
    block_id: str
    basis: str
    measurement_indices: tuple[int, ...]
    readout_measurement_indices: tuple[int, ...] = ()
    frame_correction: ParityExpression = ParityExpression()
    expected_value: int = 0
    block_use_id: BlockUseId | None = None


@dataclass(frozen=True)
class PauliFrame:
    """Affine logical X/Z correction, with preserved preparation-sector provenance.

    Corrections account for virtual Pauli updates and the syndrome dependence of
    a code-frame representative change. They are not decoder predictions.
    """

    x_terms: tuple[MeasurementKey, ...] = ()
    z_terms: tuple[MeasurementKey, ...] = ()
    preparation_syndromes: tuple[MeasurementKey, ...] = ()
    x_constant: bool = False
    z_constant: bool = False

    def __post_init__(self):
        x, z = (
            ParityExpression(self.x_terms, self.x_constant),
            ParityExpression(self.z_terms, self.z_constant),
        )
        object.__setattr__(self, "x_terms", x.terms)
        object.__setattr__(self, "z_terms", z.terms)
        object.__setattr__(self, "x_constant", x.constant)
        object.__setattr__(self, "z_constant", z.constant)
        object.__setattr__(self, "preparation_syndromes", tuple(self.preparation_syndromes))

    @property
    def x(self):
        """Classical parity controlling the logical X correction."""
        return ParityExpression(self.x_terms, self.x_constant)

    @property
    def z(self):
        """Classical parity controlling the logical Z correction."""
        return ParityExpression(self.z_terms, self.z_constant)

    def with_parities(self, x, z):
        """Replace correction parities while retaining preparation provenance."""
        return replace(
            self, x_terms=x.terms, z_terms=z.terms, x_constant=x.constant, z_constant=z.constant
        )


@dataclass(frozen=True)
class TimeLayer:
    """One physical TICK interval; its integer index is not a protocol stage."""
    index: int
    active_blocks: tuple[str, ...]
    operation_by_block: Mapping[str, str]
    used_qubits: frozenset[int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "operation_by_block", MappingProxyType(dict(self.operation_by_block))
        )


class CompilerContext:
    """Per-compilation ownership, historical aliases and bounded logical slots.

    Measured final aliases remain in logical_to_block for compatibility until
    their physical site is rebound. retired_logicals prevents their execution.
    observable_ids is the historical name-to-tableau-slot map, not output IDs;
    retired slots can be reset and reused without growing the tableau dimension.
    """

    def __init__(
        self, blocks: Sequence[LogicalBlock], logical_to_block: Mapping[str, str] | None = None
    ):
        """Register fixed patches and optional injective logical reservations."""
        self.blocks = {b.block_id: b for b in blocks}
        if not blocks or len(self.blocks) != len(blocks):
            raise ValueError("Register at least one block, with distinct block IDs")
        self.logical_to_block = (
            dict(logical_to_block)
            if logical_to_block is not None
            else {b.block_id: b.block_id for b in blocks}
        )
        if (
            any(not isinstance(k, str) or not k for k in self.logical_to_block)
            or not set(self.logical_to_block.values()) <= set(self.blocks)
            or len(set(self.logical_to_block.values())) != len(self.logical_to_block)
        ):
            raise ValueError("Logical IDs require a one-to-one mapping into registered blocks")
        self.site_positions: dict[GlobalSiteId, complex] = {}
        for block in blocks:
            if block.code.k != 1:
                raise ValueError("Memory currently supports one logical slot per block")
            for local in block.layout.qubit_ids:
                self.site_positions[block.global_site(local)] = block.position(local)
        if len(set(self.site_positions.values())) != len(self.site_positions):
            raise ValueError("Registered patches have overlapping physical coordinates")
        self.status = dict.fromkeys(self.blocks, BlockStatus.UNINITIALIZED)
        self.retired_logicals = frozenset()
        self.epochs = dict.fromkeys(self.blocks, -1)
        self.block_uses = {}
        self.binding_history = ()
        self.num_logical_slots = len(self.blocks)
        self.prepared_basis: dict[str, str] = {}
        self.observable_ids = {
            logical: i for i, logical in enumerate(sorted(self.logical_to_block))
        }
        self.frames = {logical: PauliFrame() for logical in self.logical_to_block}
        self.orientations = dict.fromkeys(self.logical_to_block, 0)
        self.syndromes: dict[tuple[str, str], ParityExpression] = {}
        self.round_counts: dict[tuple[str, str], int] = {}
        self.measurement_bases = {}
        self.expected_outputs = {}
        self.readout_frames = {}
        self.readout_orientations = {}
        self.readout_blocks = {}
        self.readout_modes = {}
        self.readout_uses = {}
        self.output_ids = {}
        self.logical_state = stim.TableauSimulator()
        self.logical_state.set_num_qubits(self.num_logical_slots)
        self.measurements: tuple[MeasurementInfo, ...] = ()
        self.detectors: tuple[DetectorInfo, ...] = ()
        self.layers: tuple[TimeLayer, ...] = ()

    def block_for(self, logical_id: str) -> LogicalBlock:
        """Resolve a current/historical alias for assembly; execution validates liveness."""
        if logical_id not in self.logical_to_block:
            raise ValueError(f"Unknown logical qubit {logical_id!r}")
        return self.blocks[self.logical_to_block[logical_id]]

    def validate_operand(self, logical_id):
        """Reject stale aliases even when a different state now occupies their patch."""
        if logical_id in self.retired_logicals:
            raise ValueError(f"Unknown live logical qubit {logical_id!r}: "
                             "Retired logical handle; bind a fresh logical ID")
        return self.block_for(logical_id)

    def validate_operation(self, operation_type, logical_ids):
        """Validate reset/active-state requirements before building physical gates."""
        blocks = [self.validate_operand(q) for q in logical_ids]
        expected = (BlockStatus.UNINITIALIZED if operation_type == "LogicalInit"
                    else BlockStatus.ACTIVE)
        if any(self.status[b.block_id] != expected for b in blocks):
            raise ValueError(f"{operation_type} operands must be {expected.value}")
        return blocks

    @property
    def available_blocks(self):
        """Unreserved patches eligible for an explicit binding, in stable ID order."""
        reserved = {b for q, b in self.logical_to_block.items() if q not in self.retired_logicals}
        return tuple(sorted(set(self.blocks) - reserved))

    def bind_patch(self, directive, event_id):
        """Atomically reserve exactly the caller's patch, without starting an epoch."""
        logical, bid = directive.logical_id, directive.physical_block_id
        if bid not in self.blocks:
            raise ValueError(f"Unknown physical block ID {bid!r}")
        if logical in self.observable_ids:
            state = "retired" if logical in self.retired_logicals else "live"
            raise ValueError(f"Logical ID {logical!r} is already {state}; use a fresh logical ID")
        if any(b == bid and q not in self.retired_logicals
               for q, b in self.logical_to_block.items()):
            raise ValueError(f"Physical block {bid!r} is active or reserved")
        trial = self.copy()
        trial.logical_to_block = {q: b for q, b in trial.logical_to_block.items() if b != bid}
        trial.logical_to_block[logical] = bid
        occupied = {slot for q, slot in trial.observable_ids.items()
                    if q not in trial.retired_logicals}
        slot = next(i for i in range(trial.num_logical_slots) if i not in occupied)
        trial.observable_ids[logical] = slot
        trial.frames[logical] = PauliFrame()
        trial.orientations[logical] = 0
        trial.status[bid] = BlockStatus.UNINITIALIZED
        previous = BlockUseId(bid, trial.epochs[bid]) if trial.epochs[bid] >= 0 else None
        trial.binding_history += (PatchBindingEvent(event_id, logical, bid, previous),)
        return trial

    def transition(self, operation_type: str, logical_id: str, basis: str | None) -> None:
        """Legacy memory-only status validation; compilation uses advanced instead."""
        block = self.block_for(logical_id)
        status = self.status[block.block_id]
        if operation_type == "LogicalInit":
            if status != BlockStatus.UNINITIALIZED:
                raise ValueError("LogicalInit requires an uninitialized block")
            self.status[block.block_id] = BlockStatus.ACTIVE
            self.prepared_basis[logical_id] = basis
        elif operation_type in ("SyndromeExtraction", "LogicalMeasure"):
            if status != BlockStatus.ACTIVE:
                raise ValueError(f"{operation_type} requires an active initialized block")
            if operation_type == "LogicalMeasure":
                if basis != self.prepared_basis[logical_id]:
                    raise ValueError("Memory readout basis must match its preparation basis")
                self.status[block.block_id] = BlockStatus.MEASURED
        else:
            raise ValueError(f"Unsupported memory operation {operation_type!r}")

    def copy(self):
        """Copy mutable compile registries and the intended-state tableau atomically."""
        result = copy.copy(self)
        for name, value in vars(self).items():
            if isinstance(value, dict):
                setattr(result, name, dict(value))
        result.logical_state = self.logical_state.copy()
        return result

    def propagate_frames(self, action, logical_ids, corrections=None):
        """Transport affine logical X/Z parities through physical H or CNOT."""
        if action == "H":
            logical = logical_ids[0]
            old = self.frames[logical]
            x_extra, z_extra = corrections or (ParityExpression(), ParityExpression())
            self.frames[logical] = old.with_parities(old.z ^ x_extra, old.x ^ z_extra)
        elif action == "CX":
            c, t = logical_ids
            fc, ft = self.frames[c], self.frames[t]
            self.frames[c] = fc.with_parities(fc.x, fc.z ^ ft.z)
            self.frames[t] = ft.with_parities(ft.x ^ fc.x, ft.z)
        else:
            raise ValueError("Unknown Clifford frame action")

    def advanced(self, operation, fragment, backend):
        """Validate/build before returning a new atomic operation state."""
        trial = self.copy()
        logical_ids = fragment.logical_ids
        kind = operation.operation_type
        blocks = trial.validate_operation(kind, logical_ids)
        indices = [trial.observable_ids[q] for q in logical_ids]
        if kind == "LogicalInit":
            for logical, block, index in zip(logical_ids, blocks, indices, strict=True):
                trial.status[block.block_id] = BlockStatus.ACTIVE
                bid = block.block_id
                trial.epochs[bid] += 1
                use = BlockUseId(bid, trial.epochs[bid])
                trial.block_uses[use] = BlockUseInfo(
                    use, fragment.module_id,
                    logical_owner_history=(UseOwnerEvent(fragment.module_id, logical),))
                trial.round_counts = {k: v for k, v in trial.round_counts.items() if k[0] != bid}
                trial.syndromes = {k: v for k, v in trial.syndromes.items() if k[0] != bid}
                trial.prepared_basis[logical] = operation.basis
                trial.logical_state.reset(index)
                if operation.basis == "X":
                    trial.logical_state.h(index)
        elif kind == "TransversalH":
            logical, block = logical_ids[0], blocks[0]
            correction = backend.hadamard_corrections(block, logical, trial.orientations[logical])
            expressions = {}
            for axis in "XZ":
                value = ParityExpression()
                for check in correction[axis]:
                    value ^= trial.syndromes[(block.block_id, check)]
                expressions[axis] = value
            trial.propagate_frames("H", logical_ids, (expressions["Z"], expressions["X"]))
            trial.orientations[logical] ^= 1
            trial.logical_state.h(indices[0])
        elif kind == "TransversalCNOT":
            chunk, reflow = fragment.components
            source_values = {}
            for logical, block, orientation in zip(
                logical_ids, blocks, fragment.orientations_before, strict=True
            ):
                code = backend.stabilizer_code(block, logical, orientation)
                check_at = {block.position(c.ancilla): c.check_id for c in block.layout.checks}
                for tile in code.tiles:
                    original = tile.to_pauli_map()
                    flow = next(f for f in chunk.flows if f.start == original)
                    source_values[flow.end] = trial.syndromes[
                        (block.block_id, check_at[tile.measure_qubit])
                    ]
            for logical, block, orientation in zip(
                logical_ids, blocks, fragment.orientations_after, strict=True
            ):
                code = backend.stabilizer_code(block, logical, orientation)
                check_at = {block.position(c.ancilla): c.check_id for c in block.layout.checks}
                for tile in code.tiles:
                    expression = ParityExpression()
                    for source in reflow.out2in[tile.to_pauli_map()]:
                        expression ^= source_values[source]
                    trial.syndromes[(block.block_id, check_at[tile.measure_qubit])] = expression
            trial.propagate_frames("CX", logical_ids)
            trial.logical_state.cx(*indices)
        elif kind == "LogicalPauli":
            for logical, index in zip(logical_ids, indices, strict=True):
                getattr(trial.logical_state, operation.pauli.lower())(index)
                if operation.mode == "frame":
                    frame = trial.frames[logical]
                    x = frame.x ^ (operation.pauli in ("X", "Y"))
                    z = frame.z ^ (operation.pauli in ("Z", "Y"))
                    trial.frames[logical] = frame.with_parities(x, z)
        elif kind == "LogicalMeasure":
            for logical, block, index in zip(logical_ids, blocks, indices, strict=True):
                pauli = stim.PauliString(trial.num_logical_slots)
                pauli[index] = operation.basis
                expectation = trial.logical_state.peek_observable_expectation(pauli)
                if expectation == 0 and operation.mode == "deterministic":
                    raise ValueError("Requested logical measurement is nondeterministic")
                trial.expected_outputs[logical] = (
                    int(expectation == -1) if expectation else None)
                trial.measurement_bases[logical] = operation.basis
                trial.readout_frames[logical] = trial.frames[logical]
                trial.readout_orientations[logical] = trial.orientations[logical]
                trial.readout_blocks[logical] = block.block_id
                trial.readout_modes[logical] = operation.mode
                use = BlockUseId(block.block_id, trial.epochs[block.block_id])
                trial.readout_uses[logical] = use
                trial.block_uses[use] = replace(
                    trial.block_uses[use], terminal_module_id=fragment.module_id)
                trial.retired_logicals |= {logical}
                trial.status[block.block_id] = BlockStatus.MEASURED
        elif kind != "SyndromeExtraction":
            raise ValueError(f"Unsupported operation {kind}")
        trial.record_syndromes(fragment)
        return trial

    def record_syndromes(self, fragment):
        """Track the latest per-use check outcomes and first-round random sectors."""
        site_at = {position: site for site, position in self.site_positions.items()}
        for chunk in fragment.chunks():
            i2q = {i: q for q, i in chunk.q2i.items()}
            for instruction in chunk.circuit:
                if instruction.name not in ("M", "MX"):
                    continue
                for target in instruction.targets_copy():
                    block_id, local = site_at[i2q[target.value]]
                    if local not in self.blocks[block_id].layout.ancilla_ids:
                        continue
                    round_index = self.round_counts.get((block_id, local), 0)
                    key = MeasurementKey(
                        block_id, local, "syndrome", round_index, self.epochs[block_id])
                    self.round_counts[(block_id, local)] = round_index + 1
                    self.syndromes[(block_id, local)] = ParityExpression((key,))
                    if (fragment.operation_type == "LogicalInit" and round_index == 0
                            and ("X" if instruction.name == "MX" else "Z")
                            != self.prepared_basis[fragment.logical_id]):
                        frame = self.frames[fragment.logical_id]
                        self.frames[fragment.logical_id] = replace(frame,
                            preparation_syndromes=frame.preparation_syndromes + (key,))
