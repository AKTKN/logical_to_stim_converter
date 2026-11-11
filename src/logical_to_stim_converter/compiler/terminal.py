"""Decoder-neutral terminal signed logical Pauli probes on an independent circuit."""

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import stim

from ..core.lifecycle import BlockUseId
from ..decoding.errors import SourceMismatchError
from ..decoding.records import binary_batch
from ..decoding.views import _freeze_circuit, _thaw_circuit, source_fingerprint


@dataclass(frozen=True)
class LogicalPauliProduct:
    """Hermitian signed product of logical X/Y/Z factors on distinct handles.

    ``factors`` accepts a mapping or pairs. ``sign`` is +1 or -1. Identity factors
    are omitted. A signed stabilizer has expectation +1 in the intended state.
    """

    factors: tuple[tuple[str, str], ...] | Mapping[str, str]
    sign: int = 1
    label: str | None = None

    def __post_init__(self):
        factors = tuple(self.factors.items() if isinstance(self.factors, Mapping) else self.factors)
        if (
            not factors
            or any(
                len(p) != 2 or not isinstance(p[0], str) or not p[0] or p[1] not in ("X", "Y", "Z")
                for p in factors
            )
            or len({p[0] for p in factors}) != len(factors)
        ):
            raise ValueError("Logical products require distinct handles and X/Y/Z factors")
        if type(self.sign) is not int or self.sign not in (-1, 1):
            raise ValueError("Logical product sign must be +1 or -1")
        if self.label is not None and (not isinstance(self.label, str) or not self.label):
            raise ValueError("Logical product label must be a nonempty string")
        object.__setattr__(self, "factors", tuple(sorted(tuple(p) for p in factors)))


def output_stabilizers(context):
    """Snapshot intended active-state generators, including virtual Pauli signs."""
    from ..core.compiler_context import BlockStatus

    active = {
        context.observable_ids[q]: q
        for q, b in context.logical_to_block.items()
        if context.status[b] == BlockStatus.ACTIVE
    }
    result = []
    rows = list(context.logical_state.canonical_stabilizers())
    pivot = 0
    for i in range(context.num_logical_slots):
        if i in active:
            continue
        for axes in ((1, 2), (2, 3)):
            found = next((j for j in range(pivot, len(rows)) if rows[j][i] in axes), None)
            if found is None:
                continue
            rows[pivot], rows[found] = rows[found], rows[pivot]
            for j in range(len(rows)):
                if j != pivot and rows[j][i] in axes:
                    rows[j] *= rows[pivot]
            pivot += 1
    for p in rows[pivot:]:
        support = {i for i in range(len(p)) if p[i]}
        if support and support <= active.keys():
            result.append(
                LogicalPauliProduct(
                    tuple((active[i], "_XYZ"[p[i]]) for i in sorted(support)), int(p.sign.real)
                )
            )
    return tuple(result)


@dataclass(frozen=True)
class TerminalObservableInfo:
    """One appended signed MPP and its physical symplectic support in global wires."""

    logical_observable: LogicalPauliProduct
    measurement_index: int
    physical_x: tuple[int, ...]
    physical_z: tuple[int, ...]
    physical_sign: int
    expected_value: int
    block_use_ids: tuple[BlockUseId, ...]


@dataclass(frozen=True)
class TerminalObservableProbe:
    """Sampler-ready derived experiment with a canonical record prefix.

    No terminal measurement is added to canonical metadata or decoder models.
    The stored circuit uses exact immutable instruction snapshots; each access
    returns an independent copy. Frames consume only ``original_measurement_count``.
    """

    source_fingerprint: str
    original_measurement_count: int
    original_qubit_count: int
    observables: tuple[TerminalObservableInfo, ...]
    _circuit: tuple = field(repr=False)

    @property
    def circuit(self):
        return _thaw_circuit(self._circuit)

    @property
    def measurement_indices(self):
        return tuple(o.measurement_index for o in self.observables)

    def split_measurements(self, samples):
        """Copy the canonical raw prefix and the terminal columns, in observable order."""
        raw = binary_batch(samples, self.original_measurement_count + len(self.observables))
        return (
            raw[:, : self.original_measurement_count].copy(),
            raw[:, self.measurement_indices].copy(),
        )

    def corrected_flips(self, samples, frame_batch):
        """Terminal outcome XOR physical frame anticommutation XOR ideal expectation.

        The caller selects decoder corrections through the existing frame API.
        An unresolved/noisy hypothesis can produce failures; this method does not
        infer corrections or interpret terminal outcomes as decoder inputs.
        """
        if frame_batch.plan.source_fingerprint != self.source_fingerprint:
            raise SourceMismatchError("Terminal probe and frame batch have different sources")
        raw, outcomes = self.split_measurements(samples)
        if not np.array_equal(raw, frame_batch.raw_measurements):
            raise SourceMismatchError("Terminal samples do not match the frame batch raw prefix")
        x, z = frame_batch.final_x, frame_batch.final_z
        if x.shape != (len(raw), self.original_qubit_count) or z.shape != x.shape:
            raise ValueError("Terminal physical frame dimensions disagree")
        for i, obs in enumerate(self.observables):
            outcomes[:, i] ^= np.logical_xor.reduce(x[:, obs.physical_z], axis=1)
            outcomes[:, i] ^= np.logical_xor.reduce(z[:, obs.physical_x], axis=1)
            outcomes[:, i] ^= bool(obs.expected_value)
        return outcomes


def make_terminal_observable_probe(compiled, logical_observables, *, require_stabilizers=True):
    """Lift commuting logical products using final bindings/orientations.

    By default every requested signed product must stabilize the intended state.
    Set require_stabilizers=False to accept deterministic expectation -1 as well;
    nondeterministic products always fail. Measurement sign is included in MPP.
    """
    if type(require_stabilizers) is not bool:
        raise ValueError("require_stabilizers must be boolean")
    products = tuple(logical_observables)
    if not products or any(not isinstance(p, LogicalPauliProduct) for p in products):
        raise ValueError("Supply one or more LogicalPauliProduct objects")
    if compiled._compiler is None:
        raise ValueError("Terminal probes require verified physical assembly")
    logical_ids = tuple(sorted(compiled.open_logical_outputs))
    slots = {q: i for i, q in enumerate(logical_ids)}

    def logical_pauli(product):
        p = stim.PauliString(len(slots))
        p.sign = product.sign
        for q, axis in product.factors:
            if q not in slots:
                raise ValueError(f"Terminal target {q!r} is not an active logical output")
            p[slots[q]] = axis
        return p

    logical = [logical_pauli(p) for p in products]
    if any(not p.commutes(q) for i, p in enumerate(logical) for q in logical[:i]):
        raise ValueError("Terminal logical observables must commute")
    basis = [logical_pauli(p) for p in compiled.logical_output_stabilizers]

    def expectation(target):
        # Signed stabilizer elimination: never complete an underconstrained state
        # with arbitrary generators and accidentally declare a random bit known.
        rows = {}
        for source in basis:
            r = source.copy()
            for column in range(2 * len(slots)):
                i, component = divmod(column, 2)
                if r[i] not in ((1, 2) if component == 0 else (2, 3)):
                    continue
                if column not in rows:
                    rows[column] = r
                    break
                r *= rows[column]
        r = target.copy()
        for column, row in sorted(rows.items()):
            i, component = divmod(column, 2)
            if r[i] in ((1, 2) if component == 0 else (2, 3)):
                r *= row
        if any(r):
            raise ValueError("Terminal logical observable is nondeterministic")
        return int(r.sign == -1)

    blocks = {b.block_id: b for b in compiled._compiler.blocks}
    backend = compiled._compiler.backend
    physical, metadata = [], []
    for product, p in zip(products, logical, strict=True):
        expected = expectation(p)
        if require_stabilizers and expected:
            raise ValueError(
                "Requested signed logical observable does not stabilize intended state"
            )
        lifted = stim.PauliString(compiled.circuit.num_qubits)
        lifted.sign = product.sign
        uses = []
        for q, axis in product.factors:
            block = blocks[compiled.open_logical_outputs[q]]
            at = {
                block.position(k): compiled.physical_qubit_map[block.block_id, k]
                for k in block.layout.data_ids
            }

            def support(basis_axis):
                r = stim.PauliString(compiled.circuit.num_qubits)
                for pos, a in backend.logical_pauli(
                    block, q, basis_axis, compiled.orientations[q]
                ).items():
                    r[at[pos]] = a
                return r

            # The i in Y=iXZ matters for products with multiple logical Ys.
            factor = (1j * support("X") * support("Z")) if axis == "Y" else support(axis)
            lifted *= factor
            use = next(
                u.use_id
                for u in compiled.block_uses
                if u.use_id.block_id == block.block_id and u.terminal_module_id is None
            )
            uses.append(use)
        physical.append(lifted)
        metadata.append(
            TerminalObservableInfo(
                product,
                compiled.circuit.num_measurements + len(metadata),
                tuple(i for i in range(len(lifted)) if lifted[i] in (1, 2)),
                tuple(i for i in range(len(lifted)) if lifted[i] in (2, 3)),
                int(lifted.sign.real),
                expected,
                tuple(uses),
            )
        )
    if any(not p.commutes(q) for i, p in enumerate(physical) for q in physical[:i]):
        raise ValueError("Lifted physical terminal observables do not commute")
    circuit = compiled.circuit.copy()
    targets = []
    for pauli in physical:
        first = True
        for i in range(len(pauli)):
            if not pauli[i]:
                continue
            if not first:
                targets.append(stim.target_combiner())
            target = (stim.target_x, stim.target_y, stim.target_z)[pauli[i] - 1]
            targets.append(target(i, invert=first and pauli.sign == -1))
            first = False
    # Stim 1.15's PauliString append shorthand drops signs. Spell inversion
    # explicitly on the first target of each Hermitian product.
    circuit.append("MPP", targets, tag="terminal_logical_probe")
    return TerminalObservableProbe(
        source_fingerprint(compiled),
        compiled.circuit.num_measurements,
        compiled.circuit.num_qubits,
        tuple(metadata),
        _freeze_circuit(circuit),
    )
