"""Typed boundary prediction and conditional destructive-readout requests.

Boundary probes are model-only ideal MPPs, never executed in the canonical
experiment or exposed as measured truth to a decoder. They define verifiable
last-record error/logical targets for temporal inference from earlier detectors.
"""

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import stim

from ..core.lifecycle import BlockUseId
from ..core.protocol import CheckHistory, LogicalReadout, PreparationInfo
from .errors import DecoderViewError, DEMConstructionError
from .frames import CorrectionBatch, readonly
from .records import GF2Map, binary_batch
from .views import (
    DecoderView,
    _freeze_circuit,
    _freeze_dem,
    _thaw_circuit,
    _thaw_dem,
)


@dataclass(frozen=True)
class StageInputs:
    """Current interpreted events/records and predicted sectors, never hidden truth."""
    source_fingerprint: str
    events: np.ndarray
    records: np.ndarray
    expected_sector: np.ndarray | None = None

    def __post_init__(self):
        if not self.source_fingerprint:
            raise DecoderViewError("Stage inputs need a source fingerprint")
        shots = None
        for name in ("events", "records", "expected_sector"):
            value = getattr(self, name)
            if value is None and name == "expected_sector":
                continue
            a = np.asarray(value)
            if a.ndim != 2 or (shots is not None and len(a) != shots):
                raise DecoderViewError("Stage input batches have inconsistent shapes")
            shots = len(a)
            object.__setattr__(self, name, readonly(binary_batch(a, a.shape[1], name)))


@dataclass(frozen=True)
class StageResult:
    """External correction hypothesis plus optional temporal/sector predictions."""
    correction: CorrectionBatch
    predicted_record_errors: np.ndarray | None = None
    net_sector: np.ndarray | None = None
    diagnostics: tuple[tuple[str, float], ...] = ()

    def __post_init__(self):
        for name in ("predicted_record_errors", "net_sector"):
            value = getattr(self, name)
            if value is not None:
                a = np.asarray(value)
                if (
                    a.ndim != 2
                    or len(a) != len(self.correction.bits)
                    or not np.isin(a, (0, 1)).all()
                ):
                    raise DecoderViewError("Stage output has invalid binary shape")
                object.__setattr__(self, name, readonly(a))


class StageDecoder(Protocol):
    """A caller-owned adapter. Correction selection never enters the compiler."""

    def decode_batch(self, request, inputs: StageInputs) -> StageResult:
        """Select a source-bound hypothesis from current records/events in request order."""
        ...


@dataclass(frozen=True)
class BoundaryRequest:
    """One use-specific preparation/SE boundary and its temporal prediction model.

    model_circuit adds ideal MPP targets to a physical prefix for model building
    only. Decoder inputs remain the selected canonical events and raw records.
    """
    module_id: str
    block_id: str
    orientation: int
    data_ids: tuple[str, ...]
    checks: tuple[CheckHistory, ...]
    last_record_ids: tuple[int, ...]
    preparation: PreparationInfo | None
    view: DecoderView
    _model_circuit: tuple = field(repr=False)
    _model: tuple = field(repr=False)
    block_use_id: BlockUseId | None = None
    source_preparation: PreparationInfo | None = None

    @property
    def model_circuit(self):
        """Copy the temporal model with ideal probes, never a sampled experiment."""
        return _thaw_circuit(self._model_circuit)

    @property
    def detector_error_model(self):
        """Copy the exact temporal target DEM; this is not a new physical experiment."""
        return _thaw_dem(self._model)

    def check_matrix(self, basis):
        """Physical check rows in data_ids column order at this boundary's orientation."""
        return np.array(
            [[q in c.support for q in self.data_ids] for c in self.checks if c.basis == basis],
            dtype=np.uint8,
        )

    @property
    def target_ids(self):
        """Prediction targets: last-result errors, then optional prepared logical error."""
        ids = tuple(f"last_record_error:{c.check_id}" for c in self.checks)
        return ids + (("prepared_logical_error",) if self.preparation is not None else ())


@dataclass(frozen=True)
class ReadoutRequest:
    """One historical destructive measurement with incoming predicted check sectors."""
    readout: LogicalReadout
    record_ids: tuple[int, ...]
    view: DecoderView
    # Inputs are net boundary sectors, in StageRequests.sector_input_ids order.
    sector_map: GF2Map
    sector_constant: tuple[bool, ...]
    source_preparation: PreparationInfo | None = None

    @property
    def check_matrix(self):
        """Measured-basis check rows in the declared raw readout-record order."""
        return self.readout.check_matrix(self.readout.basis)

    @property
    def logical_indices(self):
        """Readout-record columns forming this use's logical representative."""
        return tuple(
            i for i, k in enumerate(self.readout.records) if k in self.readout.logical_parity.terms
        )

    @property
    def block_use_id(self):
        """Physical reset-to-readout interval, independent of later site occupants."""
        return self.readout.block_use_id


@dataclass(frozen=True)
class StageRequests:
    """Causally ordered physical module boundaries over one static experiment.

    order determines offline inference order. It neither schedules gates nor
    samples independent experiments. sector_input_ids label module/check bits.
    """
    boundaries: tuple[BoundaryRequest, ...]
    readouts: tuple[ReadoutRequest, ...]
    sector_input_ids: tuple[tuple[str, str], ...]
    # Causal physical-module order, independent of decoder choices.
    order: tuple[tuple[str, str], ...]


def module_end(circuit, module_id):
    """Include the final layer's physical noise/idle, stopping at its next TICK."""
    indices = [
        i
        for i, inst in enumerate(circuit)
        if inst.tag == module_id and stim.gate_data(inst.name).produces_measurements
    ]
    if not indices:
        raise DecoderViewError("Boundary has no physical measurements")
    last = indices[-1]
    return next(
        (i + 1 for i in range(last + 1, len(circuit)) if circuit[i].name == "TICK"), len(circuit)
    )


def pauli_targets(compiled, block_id, support, basis):
    """Build ideal MPP targets on stable physical sites for a boundary model."""
    targets = []
    for q in support:
        if targets:
            targets.append(stim.target_combiner())
        index = compiled.physical_qubit_map[block_id, q]
        targets.append(stim.target_x(index) if basis == "X" else stim.target_z(index))
    return targets


def make_boundary_request(compiled, fragment, prep):
    """Build one module-local temporal model using its actual physical-use preparation.

    prep is the prepared-eigenvalue target for an initialization, and None for
    ordinary SE. source_preparation always identifies the reset of this use.
    """
    use = fragment.block_use_ids[0]
    matches = [p for p in compiled.preparations if p.block_use_id == use]
    if len(matches) != 1:
        raise DecoderViewError("Boundary needs exactly one preparation for its physical use")
    original = matches[0]
    if prep is not None and (prep != original or prep.module_id != fragment.module_id):
        raise DecoderViewError("Prepared logical target belongs to a different module/use")
    orientation = fragment.orientations_after[0]
    records = [m for m in compiled.measurements if m.module_id == fragment.module_id]
    if not records or any(m.key.block_use_id != use for m in records):
        raise DecoderViewError("Boundary records disagree with the physical-use identity")
    checks = []
    for c in original.checks:
        history = tuple(m.key for m in records if m.key.local_id == c.measurements[0].local_id)
        basis = c.basis if orientation == original.orientation else ("Z" if c.basis == "X" else "X")
        checks.append(CheckHistory(c.check_id, basis, c.support, history))
    keys = compiled.measurement_index_by_key
    checks = tuple(checks)
    last = tuple(keys[c.measurements[-1]] for c in checks)
    # Preparation regions cannot borrow future or another module's records.
    own = {m.index for m in records}
    det_ids = tuple(d.index for d in compiled.detectors if set(d.measurement_indices) <= own)
    view = compiled.make_decoder_view(
        detector_selector=det_ids,
        observable_selector=(),
        measurement_selector=tuple(m.index for m in records),
    )
    end = module_end(compiled.circuit, fragment.module_id)
    cuts = (*compiled.resource_preparation_boundaries, *compiled.post_initialization_boundaries)
    own_cuts = [b for b in cuts if b.preparation_module_id == fragment.module_id]
    if own_cuts:
        layers = {b.final_se_layer for b in own_cuts}
        indices = [b.channel_instruction for b in cuts if b.final_se_layer in layers
                   and b.channel_instruction is not None]
        if indices:
            end = min(end, min(indices))
    model = stim.Circuit()
    detector_index = 0
    for inst in compiled.circuit[:end]:
        if inst.name == "DETECTOR":
            if detector_index in det_ids:
                model.append(inst)
            detector_index += 1
        elif inst.name != "OBSERVABLE_INCLUDE":
            model.append(inst)
    nrecords = model.num_measurements
    for i, (check, record) in enumerate(zip(checks, last, strict=True)):
        model.append("MPP", pauli_targets(compiled, fragment.block_id, check.support, check.basis))
        model.append(
            "OBSERVABLE_INCLUDE",
            [stim.target_rec(-1), stim.target_rec(record - model.num_measurements)],
            i,
        )
    if prep is not None:
        support = prep.logical_x if prep.basis == "X" else prep.logical_z
        model.append("MPP", pauli_targets(compiled, prep.block_id, support, prep.basis))
        model.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], len(checks))
    if nrecords > len(compiled.measurements):
        raise DecoderViewError("Boundary prefix does not map to canonical records")
    try:
        dem = model.detector_error_model(decompose_errors=True)
    except ValueError as ex:
        raise DEMConstructionError(
            f"Boundary probe model is not exactly decomposable: {ex}"
        ) from ex
    return BoundaryRequest(
        fragment.module_id,
        fragment.block_id,
        orientation,
        original.data_ids,
        checks,
        last,
        prep,
        view,
        _freeze_circuit(model),
        _freeze_dem(dem),
        use,
        original,
    )


def _support(p):
    """Binary physical X-then-Z support for signed stabilizer elimination."""
    xs, zs = p.to_numpy()
    return np.concatenate((xs, zs))


def _express(target, bank, expressions):
    """Exact Pauli support elimination, retaining independent signed products."""
    pivots = {}
    for i, p in enumerate(bank):
        row = _support(p)
        combination = np.zeros(len(bank), dtype=bool)
        combination[i] = True
        for col, (other, coefficients) in pivots.items():
            if row[col]:
                row ^= other
                combination ^= coefficients
        nz = np.flatnonzero(row)
        if len(nz):
            pivots[int(nz[0])] = (row, combination)
    row = _support(target)
    combination = np.zeros(len(bank), dtype=bool)
    for col in sorted(pivots):
        if row[col]:
            other, coefficients = pivots[col]
            row ^= other
            combination ^= coefficients
    if row.any():
        raise DecoderViewError("Readout check is outside the predicted boundary stabilizer span")
    product = stim.PauliString(len(target))
    value = np.zeros(expressions.shape[1], dtype=bool)
    for i in np.flatnonzero(combination):
        product *= bank[i]
        value ^= expressions[i]
    if product.sign not in (1, -1) or target.sign not in (1, -1):
        raise DecoderViewError("Non-real conditional stabilizer phase")
    value[-1] ^= product.sign != target.sign
    return value


def make_stage_requests(compiled):
    """Build boundary models and sector-transfer maps once from public metadata."""
    preps = {p.module_id: p for p in compiled.preparations}
    boundaries = tuple(
        make_boundary_request(compiled, f, preps.get(f.module_id))
        for f in compiled.fragments
        if f.operation_type in ("LogicalInit", "SyndromeExtraction")
    )
    by_module = {b.module_id: b for b in boundaries}
    sector_ids = tuple((b.module_id, c.check_id) for b in boundaries for c in b.checks)
    width = len(sector_ids)
    bank, labels, expressions = [], [], np.zeros((0, width + 1), dtype=bool)
    records = compiled.measurement_index_by_key
    readout_by_id = {r.module_id: r for r in compiled.readouts}
    readouts, order = [], []
    # Check supports at a given orientation are physical; H swaps their axes.
    original = {p.block_use_id: p for p in compiled.preparations}
    orientations = {p.block_use_id: p.orientation for p in compiled.preparations}
    active = []
    nq = compiled.ideal_circuit.num_qubits

    def checks_for(use):
        """Physical checks of the currently occupied use, after actual H rotations."""
        p = original[use]
        return tuple(
            (
                c.support,
                c.basis if orientations[use] == p.orientation else ("Z" if c.basis == "X" else "X"),
            )
            for c in p.checks
        )

    def operator(bid, support, basis):
        """Lift a boundary check onto the circuit's fixed global physical wires."""
        p = stim.PauliString(nq)
        for q in support:
            p[compiled.physical_qubit_map[bid, q]] = basis
        return p

    def rebase():
        """Express current local checks through transported signed boundary sectors."""
        nonlocal bank, labels, expressions
        new, tags, values = [], [], []
        for use in active:
            for support, basis in checks_for(use):
                p = operator(use.block_id, support, basis)
                new.append(p)
                tags.append(use)
                values.append(_express(p, bank, expressions))
        bank, labels = new, tags
        expressions = np.array(values, dtype=bool).reshape(len(new), width + 1)

    for f in compiled.fragments:
        use = f.block_use_ids[0]
        if f.module_id in by_module:
            boundary = by_module[f.module_id]
            keep = [i for i, previous in enumerate(labels) if previous != use]
            bank = [bank[i] for i in keep]
            labels = [labels[i] for i in keep]
            expressions = expressions[keep]
            if use not in active:
                active.append(use)
            orientations[use] = boundary.orientation
            for c in boundary.checks:
                bank.append(operator(f.block_id, c.support, c.basis))
                labels.append(use)
                row = np.zeros(width + 1, dtype=bool)
                row[sector_ids.index((f.module_id, c.check_id))] = True
                expressions = np.vstack((expressions, row))
            order.append(("boundary", f.module_id))
        elif f.operation_type in ("TransversalCNOT", "TransversalH"):
            unitary = stim.Circuit()
            for inst in compiled.ideal_circuit:
                if inst.tag == f.module_id:
                    unitary.append(inst)
            bank = [p.after(unitary) for p in bank]
            if f.operation_type == "TransversalH":
                orientations[use] = f.orientations_after[0]
            rebase()
        elif f.module_id in readout_by_id:
            r = readout_by_id[f.module_id]
            values = [
                _express(operator(r.block_id, c.support, c.basis), bank, expressions)
                for c in r.checks
                if c.basis == r.basis
            ]
            matrix = np.array(values, dtype=bool)
            ids = tuple(records[k] for k in r.records)
            view = compiled.make_decoder_view(
                detector_selector=tuple(
                    d.index for d in compiled.detectors if d.anchor_module_id == r.module_id
                ),
                observable_selector=(),
                measurement_selector=ids,
            )
            readouts.append(
                ReadoutRequest(
                    r, ids, view, GF2Map.from_matrix(matrix[:, :-1].T), tuple(matrix[:, -1]),
                    original[r.block_use_id],
                )
            )
            keep = [i for i, previous in enumerate(labels) if previous != r.block_use_id]
            bank = [bank[i] for i in keep]
            labels = [labels[i] for i in keep]
            expressions = expressions[keep]
            active.remove(r.block_use_id)
            order.append(("readout", f.module_id))
    return StageRequests(boundaries, tuple(readouts), sector_ids, tuple(order))
