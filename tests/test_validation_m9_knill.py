"""Independent physical, algebraic and numerical controls for Phase 3 research."""

import csv
import gzip
import json
import math
from dataclasses import replace

import numpy as np
import pytest
import stim

from examples.knill_memory_offline_decoding import analyze_knill, prepare_compiled
from logical_to_stim_converter.decoding import (
    CorrectionBatch,
    DecoderViewError,
    SourceMismatchError,
    StageInputs,
)
from validation.m9_knill import (
    binomial_tail,
    k_estimates,
    low_weight_prediction,
    main,
    parallel_enumeration,
)
from validation.m9_knill_faults import (
    Case,
    assignments,
    audit_boundary_ownership,
    audit_conditional_singles,
    audit_direct_physical_samples,
    audit_epoch_clearing,
    audit_pair_action,
    make_experiment,
    pattern_counts,
    scan_locations,
    simulate_assignments,
)


def test_exact_exclusive_counts_and_actual_m9_stim_targets():
    assert pattern_counts(18) == (1, 54, 1377)
    assert pattern_counts(54) == (1, 162, 12879)
    assert sum(pattern_counts(18)) == 1432
    assert sum(pattern_counts(54)) == 13042
    for cycles in (1, 3):
        case = Case(cycles)
        experiment = make_experiment(case, 0.012)
        locations = scan_locations(experiment, 0.012)
        patterns = tuple(assignments(len(locations)))
        assert len(patterns) == sum(pattern_counts(len(locations)))
        assert [p.rank for p in patterns] == list(range(len(patterns)))
        assert len(locations) == 18 * cycles
        assert all(p.atoms[0][0] != p.atoms[1][0] for p in patterns if p.weight == 2)
        assert {axis for p in patterns if p.weight == 1 for _, axis in p.atoms} == set("XYZ")
        assert audit_boundary_ownership(experiment, locations)["conditional_windows"] == cycles
        for model in experiment.conditional_models:
            atoms = [fault for fault in model.faults if fault.channel == "DEPOLARIZE1"]
            assert len(atoms) == 54
            assert all(fault.probability == pytest.approx(0.012 / 3) for fault in atoms)
            assert len({fault.exclusive_group for fault in atoms}) == 18
        zero = make_experiment(case, 0)
        assert zero.compiled.circuit == zero.compiled.ideal_circuit
        assert len(scan_locations(zero, 0)) == 18 * cycles


def test_hand_authored_bell_physical_x_y_z_truth_table():
    ideal = stim.Circuit("R 0 1\nH 0\nCX 0 1\nMPP X0*X1 Z0*Z1\nDETECTOR rec[-2]\nDETECTOR rec[-1]")
    converter = ideal.compile_m2d_converter()
    for wire in (0, 1):
        for axis, expected in (("X", (0, 1)), ("Y", (1, 1)), ("Z", (1, 0))):
            fault = stim.Circuit("R 0 1\nH 0\nCX 0 1")
            fault.append(axis, [wire])
            fault += stim.Circuit("MPP X0*X1 Z0*Z1\nDETECTOR rec[-2]\nDETECTOR rec[-1]")
            raw = fault.compile_sampler(seed=91).sample(32)
            events = converter.convert(measurements=raw, separate_observables=False)
            assert np.all(events == expected)


def test_all_single_physical_maps_signed_branches_and_recycled_epoch():
    for cycles in (1, 3):
        experiment = make_experiment(Case(cycles), 0.01)
        locations = scan_locations(experiment, 0.01)
        singles = tuple(p for p in assignments(len(locations)) if p.weight == 1)
        actions = simulate_assignments(experiment, locations, singles, seed=701)
        other = simulate_assignments(experiment, locations, singles, seed=702)
        assert all(np.array_equal(a, b) for a, b in zip(actions, other, strict=True))
        assert (
            audit_conditional_singles(experiment, locations, singles, actions[0], actions[3])[
                "checked_atoms"
            ]
            == 54 * cycles
        )
        assert audit_epoch_clearing(experiment, locations, singles)["retired_atom_use_checks"] == (
            0 if cycles == 1 else 81
        )
        selected = tuple(singles[i] for i in (0, 1, 2, len(singles) - 1))
        direct = simulate_assignments(experiment, locations, selected)
        assert (
            audit_direct_physical_samples(experiment, locations, selected, direct)[
                "explicit_circuits"
            ]
            == 4
        )


def test_pair_physical_actions_compose_but_decoder_recomputes_combined_syndrome():
    experiment = make_experiment(Case(3), 0.01)
    locations = scan_locations(experiment, 0.01)
    singles = tuple(p for p in assignments(len(locations)) if p.weight == 1)
    single_actions = simulate_assignments(experiment, locations, singles)
    pairs = [p for p in assignments(len(locations)) if p.weight == 2]
    selected = (pairs[0], pairs[17], pairs[len(pairs) // 2], pairs[-1])
    actions = simulate_assignments(experiment, locations, selected)
    assert audit_pair_action(selected, *actions, single_actions) == len(selected)
    corrupted = list(single_actions)
    corrupted[0] = corrupted[0].copy()
    corrupted[0][0, 0] ^= True
    with pytest.raises(AssertionError, match=r"GF\(2\) pair action"):
        audit_pair_action(selected, *actions, tuple(corrupted))
    # The decoder is applied to each combined raw record; no XOR of decoded
    # single-fault decisions is used as the pair decision.
    ideal = experiment.compiled.ideal_circuit.compile_sampler(seed=811).sample(32)
    raw = np.repeat(ideal[None], len(selected), axis=0) ^ actions[0][:, None, :]
    result = analyze_knill(experiment, raw.reshape(-1, raw.shape[-1]))
    assert result.failures.shape == (len(selected) * len(ideal), 1)


def test_wrong_cut_missing_byproduct_and_stale_source_fail():
    experiment = make_experiment(Case(3), 0.01)
    locations = scan_locations(experiment, 0.01)
    singles = tuple(p for p in assignments(len(locations)) if p.weight == 1)
    correct = simulate_assignments(experiment, locations, singles[:3])[0]
    shifted = list(locations)
    shifted[0] = replace(shifted[0], ideal_cut=shifted[0].ideal_cut + 1)
    wrong = simulate_assignments(experiment, tuple(shifted), singles[:3])[0]
    assert not np.array_equal(correct, wrong)
    boundaries = list(experiment.compiled.resource_preparation_boundaries)
    boundaries[0] = replace(
        boundaries[0], ideal_boundary_instruction=boundaries[0].ideal_boundary_instruction + 1
    )
    corrupted = replace(
        experiment,
        compiled=replace(experiment.compiled, resource_preparation_boundaries=tuple(boundaries)),
    )
    with pytest.raises(AssertionError, match="final preparation TICK"):
        scan_locations(corrupted, 0.01)
    ideal = make_experiment(Case(3), 0)
    raw = ideal.compiled.circuit.compile_sampler(seed=812).sample(64)
    plan = ideal.frame_plan
    with pytest.raises(SourceMismatchError):
        plan.start(raw, source_fingerprint="stale")
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    first = plan.boundaries[0]
    bits = np.zeros((len(raw), len(first.input_ids)), dtype=bool)
    correction = CorrectionBatch(plan.source_fingerprint, first.boundary_id, bits)
    state.apply(correction)
    with pytest.raises(DecoderViewError, match="already applied"):
        state.apply(correction)
    bell = ideal.compiled.bell_measurements[2]
    altered = replace(
        bell,
        z_readout=replace(
            bell.z_readout,
            logical_parity=replace(bell.z_readout.logical_parity, terms=()),
        ),
    )
    bells = (*ideal.compiled.bell_measurements[:2], altered)
    broken = prepare_compiled(replace(ideal.compiled, bell_measurements=bells))
    assert analyze_knill(ideal, raw).errors == 0
    assert analyze_knill(broken, raw).errors > 0


def test_stage_inputs_are_causal_and_frozen_decoder_replays_same_raw():
    reference = make_experiment(Case(1), 0.01)
    actual = make_experiment(Case(1), 0.017)
    raw = actual.compiled.circuit.compile_sampler(seed=813).sample(64)
    before = raw.copy()
    calls = []

    class Audited:
        def __init__(self, decoder):
            self.decoder = decoder

        def decode_batch(self, request, inputs):
            assert isinstance(inputs, StageInputs)
            assert set(vars(inputs)) == {
                "source_fingerprint",
                "events",
                "records",
                "expected_sector",
            }
            assert not inputs.events.flags.writeable and not inputs.records.flags.writeable
            assert not hasattr(inputs, "truth") and not hasattr(inputs, "fault_atoms")
            assert not any(inst.name == "MPP" for inst in actual.compiled.circuit)
            calls.append(
                request.module_id if hasattr(request, "module_id") else request.readout.module_id
            )
            return self.decoder.decode_batch(request, inputs)

    boundary = {key: Audited(value) for key, value in reference.boundary_decoders.items()}
    readout = {key: Audited(value) for key, value in reference.readout_decoders.items()}
    result = analyze_knill(actual, raw, boundary_decoders=boundary, readout_decoders=readout)
    assert tuple(calls) == tuple(module for _, module in actual.requests.order)
    assert np.array_equal(raw, before)
    assert np.array_equal(result.failures, result.logical_values)


def test_k_algebra_tail_zero_counts_and_fits():
    def row(rank, weight, failures):
        return (rank, weight, 0, "X", -1, "", failures, 10, "", "", "", "")

    rows = [row(0, 0, 0)]
    rows += [row(i + 1, 1, 10 if i == 0 else 0) for i in range(6)]
    rows += [row(i + 7, 2, 10 if i < 2 else 0) for i in range(9)]
    estimates = k_estimates(rows, 2)
    assert estimates["K0"]["estimate"] == 0
    assert estimates["K1"]["estimate"] == 1
    assert estimates["K2"]["estimate"] == 2
    assert estimates["a1"]["estimate"] == pytest.approx(1 / 3)
    assert estimates["a2"]["estimate"] == pytest.approx(2 / 9 - 1 / 3)
    assert binomial_tail(2, 0.1) == 0
    assert binomial_tail(3, 0.1) == pytest.approx(0.001)
    prediction = low_weight_prediction(estimates, 2, 0.1)
    assert prediction["partial_estimate"] == pytest.approx((1 / 3) * 0.1 * 0.9 + (2 / 9) * 0.01)
    zero = k_estimates([row(0, 0, 0), *[row(i + 1, 1, 0) for i in range(6)]], 2)
    assert 0 < zero["K1"]["confidence_interval"][1] < 1
    assert low_weight_prediction(zero, 2, 0.1)["status"] == "incomplete_enumeration"
    from validation.code_capacity import fit_points

    synthetic = [
        dict(q=q, shots=100000, failures=round(100000 * 80 * q**2))
        for q in (0.01, 0.02, 0.03, 0.04, 0.05)
    ]
    assert abs(fit_points(synthetic)["beta"] - 2) < 0.2
    assert math.isfinite(fit_points(synthetic, curvature=True)["beta"])


def test_parallel_rank_coverage_seed_identity_and_capped_quick_cli(tmp_path):
    case = Case(1)
    _, _, one, a = parallel_enumeration(
        case, workers=1, batch_size=32, branches=4, seed=91, max_patterns=64
    )
    _, _, two, b = parallel_enumeration(
        case, workers=2, batch_size=32, branches=4, seed=91, max_patterns=64
    )
    assert one == two
    assert a["evaluated_patterns"] == b["evaluated_patterns"] == 64
    assert a["remaining_patterns"] == b["remaining_patterns"] == 1432 - 64
    assert a["physical_pair_checks"] == b["physical_pair_checks"] == 9
    with pytest.raises(ValueError):
        Case(True)
    with pytest.raises(ValueError):
        parallel_enumeration(case, workers=0, batch_size=1, branches=1, seed=1)
    assert (
        main(
            [
                "--quick",
                "--workers",
                "2",
                "--batch-size",
                "32",
                "--max-shots",
                "128",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["cases"][0]["census"]["remaining_patterns"] == 1432 - 64
    assert report["cases"][0]["coefficients"]["K2"]["status"] == "partial_pattern_set"
    with gzip.open(tmp_path / "assignments_d3_Z_r1_m9_only.csv.gz", "rt") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 64 and rows[0]["rank"] == "0"
