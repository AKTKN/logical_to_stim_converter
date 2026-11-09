"""Research-validator checks independent of the converter's decoder views."""

import json
import math
import multiprocessing
from fractions import Fraction

import numpy as np
import pymatching
import pytest
import stim

from logical_to_stim_converter import CodeSpec
from validation.code_capacity import (
    REFERENCE,
    _masks,
    _sample_task,
    depolarizing_check,
    edited_circuit,
    enumerate_failures,
    fit_points,
    main,
    minimum_syndrome_classes,
    patterns,
    physical_memory,
    physical_patterns,
    power_coefficients,
    probability_bounds,
    reference_matrix,
    run_point,
    syndrome,
    verify_physical_patterns,
    wilson,
)


def test_hand_authored_supports_and_gf2_parity():
    assert REFERENCE[3] == ((1, 2, 4, 5), (3, 6), (4, 7), (5, 6, 8, 9))
    for d in (3, 5):
        hz, lz = reference_matrix(d)
        code = CodeSpec.rotated_surface(d)
        assert np.array_equal(hz, code.H_Z)
        assert np.array_equal(lz, code.L_Z)
        columns, logical = _masks(d)
        for e in (0, 1, 3, (1 << (d * d)) - 1, 0b1010101):
            bits = np.array([(e >> j) & 1 for j in range(d * d)], dtype=np.uint8)
            assert syndrome(e, columns) == sum(int(x) << i for i, x in enumerate(hz @ bits % 2))
            assert (e & logical).bit_count() % 2 == int((lz @ bits % 2)[0])


def test_exact_counts_polynomial_and_rational_evaluation():
    small = enumerate_failures(3)
    assert small["counts"] == [0, 0, 18, 56, 57, 69, 28, 18, 9, 1]
    assert small["visited"] == [math.comb(9, w) for w in range(10)]
    assert (small["A"], small["B"]) == (18, -70)
    assert power_coefficients(small["counts"], 9) == [0, 0, 18, -70, 99, -6, -168, 240, -144, 32]
    q = Fraction(1, 13)
    exact = sum(n * q**w * (1 - q) ** (9 - w) for w, n in enumerate(small["counts"]))
    polynomial = sum(n * q**w for w, n in enumerate(power_coefficients(small["counts"], 9)))
    assert exact == polynomial
    assert probability_bounds(3, q, small) == (float(exact), float(exact))
    large = enumerate_failures(5)
    assert large["counts"] == [0, 0, 0, 292, 4333]
    assert large["visited"] == [math.comb(25, w) for w in range(5)]
    assert (large["A"], large["B"]) == (292, -2091)
    assert large["minimum_ties"] > 0 and small["minimum_ties"] > 0
    for d, census in ((3, small), (5, large)):
        for q in (0, 0.001, 0.05, 0.5):
            low, high = probability_bounds(d, q, census)
            assert 0 <= low <= high <= 1
    assert probability_bounds(5, 0.02, large)[1] > probability_bounds(5, 0.02, large)[0]


@pytest.mark.parametrize("d,max_weight", [(3, 9), (5, 4)])
def test_pymatching_against_independent_minimum_syndrome_solver(d, max_weight):
    hz, lz = reference_matrix(d)
    classes, ties = minimum_syndrome_classes(d, max_weight)
    assert ties > 0
    matching = pymatching.Matching.from_check_matrix(hz, faults_matrix=lz, weights=math.log(99))
    syndromes = np.array(
        [[bool(key & (1 << row)) for row in range(len(hz))] for key in classes], dtype=np.uint8
    )
    predicted = matching.decode_batch(syndromes).reshape(-1)
    assert np.array_equal(predicted, [classes[key][1] for key in classes])
    # Explicitly check all physically visited errors, including patterns above t.
    columns, logical = _masks(d)
    errors = list(patterns(d, range(max_weight + 1)))
    events = np.array(
        [[bool(syndrome(e, columns) & (1 << row)) for row in range(len(hz))] for e in errors],
        dtype=np.uint8,
    )
    failures = matching.decode_batch(events).reshape(-1) ^ np.array(
        [(e & logical).bit_count() & 1 for e in errors], dtype=np.uint8
    )
    counts = [
        int(np.count_nonzero(failures[np.array([e.bit_count() == w for e in errors])]))
        for w in range(max_weight + 1)
    ]
    assert counts == enumerate_failures(d)["counts"]


def test_physical_exhaustive_and_negative_controls():
    assert verify_physical_patterns(3)["patterns"] == 512
    assert verify_physical_patterns(5, 4)["patterns"] == 15276
    errors = [1 << j for j in range(9)]
    events, truth = physical_patterns(3, errors)
    hz, lz = reference_matrix(3)
    assert np.array_equal(events.T, hz.astype(bool))
    assert np.array_equal(truth, lz[0].astype(bool))
    assert not np.array_equal(events.T, hz[:, ::-1])  # wrong data order
    assert not np.array_equal(truth, np.roll(lz[0], 1))  # wrong logical support
    memory = physical_memory(3)
    sim = stim.FlipSimulator(batch_size=1, num_qubits=memory.compiled.ideal_circuit.num_qubits)
    sim.do(memory.prefix)
    sim.do(memory.suffix[:-5])  # late insertion after syndrome measurements
    mask = np.zeros((memory.compiled.ideal_circuit.num_qubits, 1), dtype=bool)
    mask[memory.data_wires[0], 0] = True
    sim.broadcast_pauli_errors(pauli="X", mask=mask)
    sim.do(memory.suffix[-5:])
    assert not sim.get_detector_flips()[list(memory.syndrome_detector_ids)].any()
    assert memory.compiled.observables[0].expected_value == 0
    assert memory.compiled.ideal_circuit.compile_detector_sampler(seed=4).sample(64)[0].sum() == 0
    raw = memory.compiled.ideal_circuit.compile_sampler(seed=4).sample(64)
    gauge_ids = [
        m.index
        for m in memory.compiled.measurements
        if m.key.kind == "syndrome" and m.key.round_index == 0 and m.basis == "X"
    ]
    assert raw[:, gauge_ids].any() and not raw[:, gauge_ids].all()


def test_depolarize_x_component_and_source_edit():
    for d in (3, 5):
        memory = physical_memory(d)
        x = edited_circuit(memory, 0.04)
        depol = edited_circuit(memory, 0.06, depolarize=True)
        assert x != memory.compiled.ideal_circuit
        assert (
            x.num_measurements
            == depol.num_measurements
            == memory.compiled.ideal_circuit.num_measurements
        )
        assert x.num_detectors == depol.num_detectors == memory.compiled.ideal_circuit.num_detectors
        for wire in memory.data_wires:
            response = {}
            for pauli in "XYZ":
                sim = stim.FlipSimulator(batch_size=1, num_qubits=x.num_qubits)
                sim.do(memory.prefix)
                mask = np.zeros((x.num_qubits, 1), dtype=bool)
                mask[wire, 0] = True
                sim.broadcast_pauli_errors(pauli=pauli, mask=mask)
                sim.do(memory.suffix)
                response[pauli] = (
                    sim.get_detector_flips()[list(memory.syndrome_detector_ids)].copy(),
                    sim.get_observable_flips().copy(),
                )
            assert all(np.array_equal(a, b) for a, b in zip(response["X"], response["Y"]))
            assert not any(a.any() for a in response["Z"])
    check = depolarizing_check(3, q=0.06, shots=2000)
    x = check["channels"]["X_ERROR"]
    depol = check["channels"]["DEPOLARIZE1"]
    assert x["shots"] == depol["shots"] == 2000
    assert check["p"] == pytest.approx(0.09)
    assert x["wilson_95"][0] <= depol["wilson_95"][1]
    assert depol["wilson_95"][0] <= x["wilson_95"][1]


def test_parallel_task_streams_and_partial_controls():
    tasks = [(3, 0.08, "algebra", 256, 45, i) for i in range(5)]
    serial = [_sample_task(t)[:2] for t in tasks]
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(
        max_workers=2, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        parallel = [result[:2] for result in executor.map(_sample_task, tasks)]
        a = run_point(
            3,
            0.08,
            "algebra",
            workers=2,
            seed=45,
            batch_size=256,
            max_shots=1280,
            target_failures=0,
            max_seconds=30,
            executor=executor,
        )
        physical_parallel = run_point(
            3,
            0.08,
            "physical",
            workers=2,
            seed=45,
            batch_size=128,
            max_shots=256,
            target_failures=0,
            max_seconds=30,
            executor=executor,
        )
    b = run_point(
        3,
        0.08,
        "algebra",
        workers=1,
        seed=45,
        batch_size=256,
        max_shots=1280,
        target_failures=0,
        max_seconds=30,
    )
    assert serial == parallel
    assert (a["shots"], a["failures"]) == (b["shots"], b["failures"])
    physical_serial = run_point(
        3,
        0.08,
        "physical",
        workers=1,
        seed=45,
        batch_size=128,
        max_shots=256,
        target_failures=0,
        max_seconds=30,
    )
    assert (physical_parallel["shots"], physical_parallel["failures"]) == (
        physical_serial["shots"],
        physical_serial["failures"],
    )
    partial = run_point(
        3,
        0.08,
        "algebra",
        workers=1,
        seed=45,
        batch_size=256,
        max_shots=1280,
        target_failures=1,
        max_seconds=30,
    )
    assert partial["stop_reason"] == "target_failures"
    assert partial["shots"] <= 1280
    timed = run_point(
        3,
        0.08,
        "algebra",
        workers=1,
        seed=45,
        batch_size=256,
        max_shots=1280,
        target_failures=0,
        max_seconds=1e-9,
    )
    assert timed["stop_reason"] == "max_seconds" and not timed["complete"]
    assert wilson(0, 100)[0] == 0 and wilson(0, 100)[1] > 0
    for bad in (0, -1, True):
        with pytest.raises(ValueError):
            run_point(
                3,
                0.1,
                "algebra",
                workers=1,
                seed=1,
                batch_size=bad,
                max_shots=100,
                target_failures=0,
                max_seconds=2,
            )
    with pytest.raises(ValueError):
        edited_circuit(physical_memory(3), float("nan"))
    with pytest.raises(ValueError):
        probability_bounds(3, -0.1, enumerate_failures(3))


def test_fit_synthetic_binomial_and_quick_cli(tmp_path):
    # High-count deterministic fixture: finite-q curvature must be recoverable.
    points = []
    for q in (0.015, 0.025, 0.04, 0.06, 0.09):
        shots = 2_000_000
        failures = round(shots * 18 * q**2 * math.exp(-3 * q))
        points.append({"q": q, "shots": shots, "failures": failures})
    free = fit_points(points, curvature=True)
    fixed = fit_points(points, fixed_beta=2, curvature=True)
    assert free["status"] == fixed["status"] == "ok"
    assert abs(free["beta"] - 2) < 0.2
    assert abs(free["A"] - 18) < 4
    assert abs(fixed["c"] + 3) < 1
    assert (
        fit_points([{"q": 0.01, "shots": 100, "failures": 0}])["status"]
        == "insufficient_nonzero_points"
    )
    assert (
        main(
            [
                "--quick",
                "--workers",
                "1",
                "--shots",
                "64",
                "--batch-size",
                "32",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["schema_version"] == 1
    assert len(report["points"]) == 16
    assert all(p["shots"] == 64 for p in report["points"])
    assert (tmp_path / "points.csv").exists()
