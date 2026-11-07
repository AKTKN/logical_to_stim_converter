"""External-consumer memory decoding: physical truth and many views of one batch."""

import json

import numpy as np
import pytest
import stim

from examples.memory_offline_decoding import (
    MatchingModelError,
    analyze_memory,
    build_memory,
    make_matching,
    run_memory,
    save_report,
    wilson_interval,
)
from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    NoiseParameters,
    SyndromeExtraction,
)
from tests.helpers.decoder_view_physics import hand_artifact


def check_raw_truth(run):
    """Reconstruct signs/physical parities independently of the example adapter."""
    c = run.compiled
    raw = run.raw_measurements
    ref = c.circuit.reference_sample()
    for d in c.detectors:
        indices = list(d.measurement_indices)
        bits = np.bitwise_xor.reduce(raw[:, indices], axis=1)
        bits ^= np.bitwise_xor.reduce(ref[indices])
        assert np.array_equal(bits, run.detection_events[:, d.index])
    key_map = {m.key: m.index for m in c.measurements}
    for o in c.observables:
        readout = np.bitwise_xor.reduce(raw[:, o.readout_measurement_indices], axis=1)
        interpreted = readout ^ o.frame_correction.evaluate(raw, key_map)
        assert np.array_equal(interpreted ^ o.expected_value, run.observable_flips[:, o.index])
    dets, obs = c.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    assert np.array_equal(dets, run.detection_events)
    assert np.array_equal(obs, run.observable_flips)


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_noiseless_memory_correctness_and_repeated_branches(distance, basis):
    run = run_memory(distance=distance, rounds=distance, basis=basis, p=0, shots=128, seed=291)
    assert run.raw_measurements.any()  # Random preparation gauges are not errors.
    check_raw_truth(run)
    assert not run.detection_events.any() and not run.observable_flips.any()
    for result in run.strategies:
        assert result.predicted_flips.shape == (128, 1)
        assert not result.failures.any() and result.logical_errors == 0
    for seed in (292, 293):
        raw = run.compiled.circuit.compile_sampler(seed=seed).sample(64)
        repeated = analyze_memory(run.compiled, raw)
        check_raw_truth(repeated)
        assert all(s.logical_errors == 0 for s in repeated.strategies)
    # R is a total, independent of d, with one round in init and R-1 in SE.
    syndromes = [m for m in run.compiled.measurements if m.key.kind == "syndrome"]
    assert len(syndromes) == distance * (distance * distance - 1)


@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("initial_minus", [False, True])
@pytest.mark.parametrize("last_pauli", [None, "physical", "frame"])
def test_observable_truth_signed_input_and_physical_virtual_paulis(
    basis, initial_minus, last_pauli
):
    block = LogicalBlock.placed("physical", CodeSpec.rotated_surface(3))
    compiler = CircuitCompiler([block], logical_to_block={"memory": "physical"})
    opposite = "Z" if basis == "X" else "X"
    program = [LogicalInit("memory", basis, 1)]
    if initial_minus:
        program.append(LogicalPauli("memory", opposite, mode="physical"))
    program.append(SyndromeExtraction("memory", 2))
    if last_pauli is not None:
        program.append(LogicalPauli("memory", opposite, mode=last_pauli))
    program.append(LogicalMeasure("memory", basis))
    c = compiler.compile(program, noise_model=NoiseModel())
    raw = c.circuit.compile_sampler(seed=294).sample(96)
    run = analyze_memory(c, raw)
    check_raw_truth(run)
    (o,) = c.observables
    expected = initial_minus ^ (last_pauli is not None)
    assert o.expected_value == expected
    assert (c.interpreted_measurements(raw) == expected).all()
    physical_parity = np.bitwise_xor.reduce(raw[:, o.readout_measurement_indices], axis=1)
    assert (physical_parity == (initial_minus ^ (last_pauli == "physical"))).all()
    assert not run.observable_flips.any()  # A deterministic -1 is not an observable flip.
    assert all(s.logical_errors == 0 for s in run.strategies)


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_nonzero_noise_baseline_and_exact_ler_count(basis):
    run = run_memory(distance=3, rounds=5, basis=basis, p=0.003, shots=512, seed=295)
    check_raw_truth(run)
    assert run.parameters["rounds"] == 5 and run.parameters["distance"] == 3
    assert run.global_dem == run.compiled.circuit.detector_error_model()
    for result in run.strategies:
        labels = run.observable_flips[:, result.view.observable_map.global_ids]
        failures = result.predicted_flips ^ labels
        errors = int(np.count_nonzero(np.any(failures, axis=1)))
        assert np.array_equal(result.failures, failures)
        assert result.logical_errors == errors
        assert result.logical_error_rate == errors / 512
        assert 0 <= errors <= 512
        assert result.per_observable_errors == tuple(np.count_nonzero(failures, axis=0))
    assert any(
        t.is_separator()
        for inst in run.strategies[0].view.detector_error_model.flattened()
        if inst.type == "error"
        for t in inst.targets_copy()
    )


def test_only_one_sampling_call_and_independent_patch_scope(monkeypatch):
    calls = []
    original = stim.Circuit.compile_sampler

    def spy(circuit, *args, **kwargs):
        calls.append(circuit.copy())
        return original(circuit, *args, **kwargs)

    monkeypatch.setattr(stim.Circuit, "compile_sampler", spy)
    run = run_memory(distance=3, rounds=3, two_patch=True, p=0.002, shots=257, seed=296)
    assert len(calls) == 1
    assert calls[0] == run.compiled.circuit
    assert len(run.compiled.observables) == 2
    assert run.compiled.observables[0].logical_id == "a_input"
    assert run.compiled.observables[0].block_id == "physical_1"
    assert run.compiled.observables[1].block_id == "physical_0"
    check_raw_truth(run)
    raw_before = run.raw_measurements.copy()
    for result in run.strategies:
        if result.strategy == "global":
            assert result.predicted_flips.shape == (257, 2)
        else:
            assert result.predicted_flips.shape == (257, 1)
            (global_id,) = result.view.observable_map.global_ids
            block_id = run.compiled.observables[global_id].block_id
            assert result.view.observable_map.global_to_local[global_id] == 0
            assert all(d.supporting_block_ids == (block_id,) for d in result.view.detectors)
            assert len(result.view.detectors) * 2 == len(run.compiled.detectors)
            assert np.array_equal(
                result.view.events_from_raw(run.raw_measurements),
                result.view.project_detection_events(run.detection_events),
            )
        matching = make_matching(result.view.detector_error_model)
        events = result.view.project_detection_events(run.detection_events)
        chunked = np.concatenate(
            [
                matching.decode_batch(events[a:b], enable_correlations=True)
                for a, b in ((0, 13), (13, 147), (147, 257))
            ]
        )
        assert np.array_equal(chunked, result.predicted_flips)
        truth = result.view.project_observable_flips(run.observable_flips)
        assert (
            np.count_nonzero(np.any(chunked.astype(bool) ^ truth, axis=1)) == result.logical_errors
        )
    assert len(calls) == 1 and np.array_equal(raw_before, run.raw_measurements)
    assert not run.raw_measurements.flags.writeable


def test_seed_reproducibility_and_registration_reordering():
    options = dict(distance=3, rounds=4, two_patch=True, p=0.002, shots=129, seed=297)
    first = run_memory(**options)
    second = run_memory(**options, reverse_registration=True)
    assert first.compiled.circuit == second.compiled.circuit
    assert first.summary()["source_fingerprint"] == second.summary()["source_fingerprint"]
    assert first.summary()["raw_batch_sha256"] == second.summary()["raw_batch_sha256"]
    assert np.array_equal(first.raw_measurements, second.raw_measurements)
    for a, b in zip(first.strategies, second.strategies, strict=True):
        assert a.view.detector_map == b.view.detector_map
        assert a.view.observable_map == b.view.observable_map
        assert np.array_equal(a.predicted_flips, b.predicted_flips)
        assert a.logical_errors == b.logical_errors


@pytest.mark.parametrize("fault_kind", ["data_X", "readout"])
def test_enumerated_physical_faults_have_known_events_truth_and_predictions(fault_kind):
    # Three-bit memory is a hand-checkable adapter fixture, separate from surface-code tests.
    source = hand_artifact(
        stim.Circuit("""
        R 0 1 2
        X_ERROR(0.01) 0 1 2
        M 0 1 2
        DETECTOR(0, 0, 0) rec[-3] rec[-2]
        DETECTOR(1, 0, 0) rec[-2] rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-3]
    """)
    )
    samples = []
    for fault in (None, 0, 1, 2):
        circuit = stim.Circuit("R 0 1 2")
        if fault_kind == "data_X" and fault is not None:
            circuit.append("X", [fault])
        for target in range(3):
            circuit.append("M", [target], int(fault_kind == "readout" and fault == target))
        samples.append(circuit.compile_sampler(seed=298).sample(1)[0])
    run = analyze_memory(source, np.asarray(samples))
    assert np.array_equal(run.detection_events, [[0, 0], [1, 0], [1, 1], [0, 1]])
    assert np.array_equal(run.observable_flips, [[0], [1], [0], [0]])
    for result in run.strategies:
        assert np.array_equal(result.predicted_flips, run.observable_flips)
        assert result.logical_errors == 0


def test_non_graphlike_models_are_rejected_explicitly():
    model = stim.DetectorErrorModel("error(0.1) D0 D1 D2 L0")
    before = model.copy()
    with pytest.raises(MatchingModelError, match="Undecomposed hyperedge"):
        make_matching(model)
    assert model == before
    c = hand_artifact(
        stim.Circuit("""
        R 0 1 2
        CORRELATED_ERROR(0.1) X0 X1 X2
        M 0 1 2
        DETECTOR(0, 0, 0) rec[-3]
        DETECTOR(1, 0, 0) rec[-2]
        DETECTOR(2, 0, 0) rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-3]
    """)
    )
    with pytest.raises(MatchingModelError, match="Stim graphlike decomposition failed"):
        analyze_memory(c, c.circuit.compile_sampler(seed=299).sample(8))


def test_custom_noise_and_report_outputs(tmp_path):
    noise = NoiseModel(NoiseParameters(measurement=0.002))
    run = run_memory(distance=3, rounds=2, basis="Z", noise_model=noise, shots=64, seed=300)
    assert run.parameters["p"] is None
    assert run.parameters["noise"]["default"]["measurement"] == 0.002
    # Include a zero-error mixed case to check meaningful upper bounds and plot boundaries.
    mixed = run_memory(two_patch=True, p=0, shots=64, seed=301)
    payload = save_report([run, mixed], tmp_path)
    disk = json.loads((tmp_path / "memory_results.json").read_text(encoding="utf-8"))
    assert (
        disk["experiments"][0]["strategies"][0]["logical_errors"]
        == run.strategies[0].logical_errors
    )
    assert payload["experiments"][1]["shots"] == 64
    assert (tmp_path / "memory_ler.png").read_bytes().startswith(b"\x89PNG")
    assert "<svg" in (tmp_path / "memory_ler.svg").read_text(encoding="utf-8")
    assert "logical_error_rate" in (tmp_path / "memory_results.csv").read_text(encoding="utf-8")
    low, high = wilson_interval(0, 64)
    assert low == 0 and 0 < high < 1
    with pytest.raises(ValueError, match="either p"):
        run_memory(noise_model=noise, p=0.001)
    with pytest.raises(ValueError, match="rounds"):
        build_memory(rounds=0)
