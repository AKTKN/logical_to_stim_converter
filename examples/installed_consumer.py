"""Copy this file and the .lstim inputs outside the checkout; use an installed wheel.

Only public converter imports and runtime dependencies are used. The adapter
trusts last recorded sectors and assumes zero readout errors. It resolves random
noiseless preparation sectors; it is NOT a reliable noisy Knill decoder. Neither
hidden faults nor model-only MPP outcomes enter its inputs. No sampling occurs
inside analysis/replay. See docs/ordinary_memory_tutorial.md and
knill_memory_tutorial.md for source inputs, commands, labels and limitations.
"""

import argparse
import json
from dataclasses import dataclass

import numpy as np

from logical_to_stim_converter import (
    NoiseModel,
    ResourcePreparationNoise,
    parse_logical_file,
)
from logical_to_stim_converter.decoding import (
    BoundaryRequest,
    CorrectionBatch,
    DecoderViewError,
    SourceMismatchError,
    StageDecoder,
    StageInputs,
    StageResult,
    make_conditional_readout_model,
    make_stage_requests,
    source_fingerprint,
)


def solve_sector(matrix, syndrome):
    """Solve H*x=s over GF(2), free variables zero; no likelihood/error inference.

    matrix is [checks, data], syndrome [shots, checks]. Binary elimination acts
    on the whole batch, not on quantum states. A logical row can fix preparation
    ambiguity. This arbitrary representative is intentionally not minimum weight.
    """
    a = np.array(matrix, dtype=bool, copy=True)
    rhs = np.array(syndrome, dtype=bool, copy=True)
    pivots = []
    row = 0
    for column in range(a.shape[1]):
        candidates = np.flatnonzero(a[row:, column])
        if not len(candidates):
            continue
        pivot = row + candidates[0]
        a[[row, pivot]] = a[[pivot, row]]
        rhs[:, [row, pivot]] = rhs[:, [pivot, row]]
        for other in np.flatnonzero(a[:, column]):
            if other != row:
                a[other] ^= a[row]
                rhs[:, other] ^= rhs[:, row]
        pivots.append(column)
        row += 1
    if rhs[:, row:].any():
        raise ValueError("Inconsistent sector equations")
    result = np.zeros((len(rhs), a.shape[1]), dtype=bool)
    result[:, pivots] = rhs[:, :row]
    return result


class ObservedSectorAdapter:
    """Consumer-owned StageDecoder: recorded-sector / identity-readout baseline.

    Ordinary detector events and temporal/conditional models are available to a
    replacement adapter. This baseline does not infer measurement or logical
    faults. At zero noise it still selects nonzero random-gauge representatives.
    """

    def __init__(self, plan):
        self.plan = plan

    def decode_batch(self, request, inputs: StageInputs) -> StageResult:
        if inputs.source_fingerprint != self.plan.source_fingerprint:
            raise SourceMismatchError("Stage inputs belong to another physical source")
        if request.view.source_fingerprint != inputs.source_fingerprint:
            raise SourceMismatchError("Stage request belongs to another physical source")
        if (inputs.events.shape[1] != len(request.view.detectors)
                or inputs.records.shape[1] != len(request.view.measurements)):
            raise DecoderViewError("Stage input widths disagree with the request")
        physical = isinstance(request, BoundaryRequest)
        module = request.module_id if physical else request.readout.module_id
        boundary = self.plan.boundary_by_id[module]
        if request.block_use_id != boundary.block_use_id:
            raise DecoderViewError("Stage request belongs to another physical use")
        if not physical:
            if (inputs.expected_sector is None or inputs.expected_sector.shape != (
                    len(inputs.records), request.check_matrix.shape[0])):
                raise DecoderViewError("Readout needs predicted incoming check sectors")
            bits = np.zeros((len(inputs.records), len(request.record_ids)), dtype=bool)
            net = predicted = None
        else:
            mapping = request.view.measurement_map.global_to_local
            observed = inputs.records[:, [mapping[i] for i in request.last_record_ids]]
            xz = []
            for axis, check_basis in (("X", "Z"), ("Z", "X")):
                matrix = request.check_matrix(check_basis)
                syndrome = observed[:, [i for i, c in enumerate(request.checks)
                                        if c.basis == check_basis]]
                prep = request.preparation
                if prep is not None and prep.basis == check_basis:
                    support = prep.logical_x if check_basis == "X" else prep.logical_z
                    matrix = np.vstack((matrix, [q in support for q in request.data_ids]))
                    syndrome = np.column_stack((syndrome, np.zeros(len(syndrome), dtype=bool)))
                xz.append(solve_sector(matrix, syndrome))
            bits = np.concatenate(xz, axis=1)  # X(data_ids), then Z(data_ids).
            effect = np.column_stack([
                np.bitwise_xor.reduce(
                    xz[1 if c.basis == "X" else 0][:, [request.data_ids.index(q)
                                                     for q in c.support]], axis=1,
                ) for c in request.checks
            ])
            net = observed ^ effect
            predicted = np.zeros_like(observed)  # Assumption: last result has no error.
        return StageResult(
            CorrectionBatch(inputs.source_fingerprint, module, bits,
                            block_use_id=request.block_use_id, input_ids=boundary.input_ids),
            predicted_record_errors=predicted, net_sector=net,
        )


def analyze_memory(compiled, raw, predictor=None):
    """One unchanged batch, exact physical models, and external observable predictions.

    predictor(view, events) returns bool[shots, selected_observables]; it receives
    no actual observable labels. Default predicts zero reference-relative flips.
    """
    full = compiled.make_decoder_view()
    local = compiled.make_decoder_view(
        detector_selector=tuple(range(len(compiled.detectors) - 1, -1, -2)),
        observable_selector=tuple(reversed(range(len(compiled.observables)))),
        measurement_selector=tuple(range(len(compiled.measurements) - 1,
                                         max(-1, len(compiled.measurements) - 5), -1)),
    )
    inputs = full.inputs_from_raw(raw, source_fingerprint=full.source_fingerprint)
    events = local.events_from_raw(raw, source_fingerprint=full.source_fingerprint)
    if predictor is None:
        predicted = np.zeros((len(raw), len(local.observables)), dtype=bool)
    else:
        predicted = np.asarray(predictor(local, events))
    # The adapter owns this validation; labels never enter prediction.
    if predicted.shape != (len(raw), len(local.observables)) or predicted.dtype != np.bool_:
        raise ValueError("Predictor must return bool[shots, selected_observables]")
    actual = local.project_observable_flips(inputs.observable_flips)
    values = compiled.interpreted_measurements(raw)[:, local.observable_map.global_ids]
    expected = np.array([o.expected_value for o in local.observables], dtype=bool)
    failures = values ^ predicted ^ expected
    assert np.array_equal(failures, actual ^ predicted)
    assert np.array_equal(events, local.project_detection_events(inputs.detection_events))
    return dict(full=full, local=local, inputs=inputs, predicted=predicted,
                values=values ^ predicted, failures=failures)


@dataclass(frozen=True)
class KnillSetup:
    """One-time public models/maps; no quantum sample or per-shot state."""
    compiled: object
    plan: object
    requests: object
    conditional_models: tuple


def prepare_knill(compiled):
    return KnillSetup(compiled, compiled.make_frame_plan(), make_stage_requests(compiled),
                      tuple(make_conditional_readout_model(compiled, b)
                            for b in compiled.bell_measurements))


def analyze_knill(setup, raw, decoder: StageDecoder | None = None):
    """Causal same-raw replay; final failure is corrected physical parity XOR intent."""
    compiled, plan, requests = setup.compiled, setup.plan, setup.requests
    if source_fingerprint(compiled) != plan.source_fingerprint:
        raise SourceMismatchError("Rebuild the stale frame plan and stage models")
    if any(m.source_fingerprint != plan.source_fingerprint for m in setup.conditional_models):
        raise SourceMismatchError("Rebuild the stale conditional model")
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    decoder = ObservedSectorAdapter(plan) if decoder is None else decoder
    sectors = np.zeros((len(raw), len(requests.sector_input_ids)), dtype=bool)
    boundaries = {r.module_id: r for r in requests.boundaries}
    readouts = {r.readout.module_id: r for r in requests.readouts}
    results = []
    for kind, module in requests.order:
        request = boundaries[module] if kind == "boundary" else readouts[module]
        inputs = StageInputs(
            plan.source_fingerprint, state.events(request.view),
            request.view.project_raw_measurements(state.interpreted_measurements),
            (request.sector_map.apply(sectors) ^ request.sector_constant
             if kind == "readout" else None),
        )
        result = decoder.decode_batch(request, inputs)
        if result.correction.boundary_id != module:
            raise DecoderViewError("Adapter returned another module's correction")
        state.apply(result.correction)
        if kind == "boundary":
            if result.net_sector is None or result.net_sector.shape != (
                    len(raw), len(request.checks)):
                raise DecoderViewError("Adapter must return request-ordered net sectors")
            for i, check in enumerate(request.checks):
                sectors[:, requests.sector_input_ids.index((module, check.check_id))] = (
                    result.net_sector[:, i])
        results.append((inputs, result))
    interpreted = state.interpreted_measurements
    values = np.column_stack([
        np.bitwise_xor.reduce(interpreted[:, o.readout_measurement_indices], axis=1)
        for o in compiled.observables
    ])
    expected = np.array([o.expected_value for o in compiled.observables], dtype=bool)
    return dict(batch=state, values=values, failures=values ^ expected, results=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", choices=("memory", "knill"))
    parser.add_argument("source", help="Consumer-supplied .lstim file (not installed in wheel)")
    parser.add_argument("--p", type=float, default=0)
    parser.add_argument("--m9", action="store_true", help="Enable ideal Bell-owned preparation")
    parser.add_argument("--p-st", type=float, default=.003, help="M9 data probability in [0,.75]")
    parser.add_argument("--shots", type=int, default=32)
    parser.add_argument("--seed", type=int, default=41)
    args = parser.parse_args()
    if args.shots < 1:
        parser.error("shots must be positive")
    try:
        noise = NoiseModel(default=NoiseModel.uniform_depolarizing(args.p).default,
                           resource_preparation=ResourcePreparationNoise(args.m9, args.p_st))
        program = parse_logical_file(args.source)
        compiled = program.compile(noise_model=noise)
        compiled.validate_metadata()
        dem = compiled.circuit.detector_error_model()  # Canonical full model, unchanged.
        setup = prepare_knill(compiled) if args.workflow == "knill" else None
        # The only physical sampling call. Replay functions cannot sample again.
        raw = compiled.circuit.compile_sampler(seed=args.seed).sample(shots=args.shots)
        raw.flags.writeable = False
        analysis = (analyze_knill(setup, raw) if setup is not None
                    else analyze_memory(compiled, raw))
    except ValueError as error:
        parser.error(str(error))
    failures = analysis["failures"]
    print(json.dumps(dict(
        workflow=args.workflow, p=args.p, m9=args.m9, p_st=args.p_st,
        decoder=("observed-last-sector / identity-readout" if setup else "zero-flip prediction"),
        noisy_accuracy_claim=False, raw_shape=list(raw.shape),
        events_shape=[len(raw), len(compiled.detectors)], values_shape=list(failures.shape),
        errors=int(np.any(failures, axis=1).sum()),
        empirical_failure_rate=float(np.any(failures, axis=1).mean()),
        canonical_dem_errors=dem.num_errors, block_uses=len(compiled.block_uses),
        final_location=dict(compiled.logical_to_block),
        resource_boundaries=len(compiled.resource_preparation_boundaries),
        conditional_atoms=([len(m.faults) for m in setup.conditional_models] if setup else []),
    ), sort_keys=True))


if __name__ == "__main__":
    main()
