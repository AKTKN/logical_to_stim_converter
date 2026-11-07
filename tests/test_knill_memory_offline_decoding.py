"""M6-D: physical memory truth, static sampling, replay and wall-time accounting."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from examples.knill_memory_offline_decoding import (
    ReadoutMatching,
    analyze_knill,
    build_knill,
    prepare_compiled,
    prepare_experiment,
    run_knill,
    save_report,
)
from logical_to_stim_converter import BellStatePrep, KnillEC
from logical_to_stim_converter.decoding import StageInputs
from tests.helpers.knill_physics import corrected_expectation, make_compiler, pauli, simulate


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
@pytest.mark.parametrize("teleportations", [1, 2])
def test_noiseless_memory_all_signs_random_branches(distance, basis, bit, teleportations):
    run = run_knill(
        distance=distance,
        basis=basis,
        bit=bit,
        teleportations=teleportations,
        p=0,
        shots=64,
        seed=412,
    )
    e, a = run.experiment, run.analysis
    assert a.errors == 0 and (a.logical_values == bit).all()
    assert not a.physical_events.any() and not a.physical_observable_flips.any()
    assert a.raw_measurements.any()
    assert len(e.compiled.relocation_history) == teleportations
    assert e.compiled.logical_to_block == {"D": f"physical_B{teleportations - 1}"}
    assert [p.rounds for p in e.compiled.preparations] == [distance] * (1 + 2 * teleportations)
    for bell in e.compiled.bell_measurements:
        mx = bell.x_readout.logical_parity.evaluate(
            a.interpreted_measurements, e.compiled.measurement_index_by_key
        )
        mz = bell.z_readout.logical_parity.evaluate(
            a.interpreted_measurements, e.compiled.measurement_index_by_key
        )
        assert len(set(zip(mx, mz, strict=True))) == 4
    assert not any(i.name == "MPP" for i in e.compiled.circuit)
    assert e.global_dem == e.compiled.circuit.detector_error_model()
    assert sum(v for k, v in run.timings.items() if k != "total_wall") == pytest.approx(
        run.timings["total_wall"], abs=1e-8
    )
    assert all(v >= 0 for v in run.timings.values())


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("teleportations", [1, 2])
def test_physical_tableau_entangled_reference_and_nontrivial_frames(distance, teleportations):
    names = ["R", "D"] + [q for t in range(teleportations) for q in (f"A{t}", f"B{t}")]
    c = make_compiler(distance, names).compile(
        [BellStatePrep("R", "D")] + [KnillEC("D", f"A{t}", f"B{t}") for t in range(teleportations)],
        allow_open_outputs=True,
    )
    experiment = prepare_compiled(c)
    raw, simulators = simulate(c, range(16))
    result = analyze_knill(experiment, raw)
    assert result.final_x.any() or result.final_z.any()
    for shot, simulator in enumerate(simulators):
        for basis in "XZ":
            joint = pauli(c, "R", basis) * pauli(c, "D", basis)
            xs, zs = joint.to_numpy()
            sign = (
                np.count_nonzero(result.final_x[shot] & zs)
                + np.count_nonzero(result.final_z[shot] & xs)
            ) % 2
            assert simulator.peek_observable_expectation(joint) * (-1) ** sign == 1
            assert simulator.peek_observable_expectation(pauli(c, "D", basis)) == 0
    # Independently validated M5 oracle, on the same actual tableau branches.
    corrections = {}
    for module, _, decoded, _ in result.diagnostics:
        if module in {p.module_id for p in c.preparations}:
            prep = next(p for p in c.preparations if p.module_id == module)
            n = len(prep.data_ids)
            corrections[module] = tuple(prep.resolve(v[:n], v[n:]) for v in decoded.correction.bits)
    reference = c.evaluate_frames(raw, corrections)
    assert np.array_equal(reference.corrected_measurements, result.interpreted_measurements)
    for shot, simulator in enumerate(simulators):
        frames = [reference.final_frames[q][shot] for q in ("R", "D")]
        for basis in "XZ":
            assert (
                corrected_expectation(
                    simulator, c, pauli(c, "R", basis) * pauli(c, "D", basis), frames
                )
                == 1
            )


def test_noisy_same_batch_replay_chunking_and_one_physical_sample(monkeypatch):
    calls = []
    original = stim.Circuit.compile_sampler

    def spy(circuit, *args, **kwargs):
        calls.append(circuit.copy())
        return original(circuit, *args, **kwargs)

    monkeypatch.setattr(stim.Circuit, "compile_sampler", spy)
    run = run_knill(
        distance=3, basis="Z", teleportations=2, post_rounds=3, p=0.002, shots=257, seed=417
    )
    assert len(calls) == 1
    e, a = run.experiment, run.analysis
    before = a.raw_measurements.copy()
    replay = analyze_knill(e, a.raw_measurements)
    assert len(calls) == 1 and np.array_equal(a.logical_values, replay.logical_values)
    alternate = {
        r.readout.module_id: ReadoutMatching(r, weights=np.linspace(1, 1.5, len(r.record_ids)))
        for r in e.requests.readouts
    }
    other = analyze_knill(e, a.raw_measurements, readout_decoders=alternate)
    assert 0 <= other.errors <= 257
    chunks = [
        analyze_knill(e, a.raw_measurements[i:j]) for i, j in ((0, 13), (13, 147), (147, 257))
    ]
    assert np.array_equal(np.concatenate([v.logical_values for v in chunks]), a.logical_values)
    assert sum(v.errors for v in chunks) == a.errors
    assert np.array_equal(a.raw_measurements, before)
    assert not a.raw_measurements.flags.writeable and not a.physical_events.flags.writeable
    assert a.errors == np.count_nonzero(np.any(a.logical_values != 0, axis=1))
    assert 0 <= a.errors <= 257
    assert e.global_dem == e.compiled.circuit.detector_error_model()
    # Fixed circuit/call structure, never coupling independent random streams to infer physics.
    again = original(e.compiled.circuit, seed=417).sample(257)
    assert np.array_equal(before, again)


def test_stage_protocol_has_no_hidden_truth_or_simulator(monkeypatch):
    experiment = prepare_experiment(p=0.001)
    raw = experiment.compiled.circuit.compile_sampler(seed=418).sample(32)

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
            assert not inputs.records.flags.writeable
            assert inputs.records.shape[1] == len(request.view.measurements)
            assert not hasattr(request, "_compiler")
            return self.decoder.decode_batch(request, inputs)

    def forbidden(*args, **kwargs):
        raise AssertionError("No shot-specific quantum execution")

    monkeypatch.setattr(stim, "TableauSimulator", forbidden)
    monkeypatch.setattr(stim.Circuit, "compile_sampler", forbidden)
    result = analyze_knill(
        experiment,
        raw,
        boundary_decoders={k: Audited(v) for k, v in experiment.boundary_decoders.items()},
        readout_decoders={k: Audited(v) for k, v in experiment.readout_decoders.items()},
    )
    assert len(result.failures) == 32


def test_missing_bell_hypothesis_breaks_logical_memory():
    experiment = prepare_experiment(p=0, basis="X", post_rounds=0)
    raw = experiment.compiled.circuit.compile_sampler(seed=419).sample(128)
    normal = analyze_knill(experiment, raw)
    bell = experiment.compiled.bell_measurements[0]
    # TEST-ONLY deliberately corrupt the source Bell byproduct parity in the physical plan.
    bad_bell = replace(
        bell,
        x_readout=replace(
            bell.x_readout, logical_parity=replace(bell.x_readout.logical_parity, terms=())
        ),
    )
    bad = replace(experiment.compiled, bell_measurements=(bad_bell,))
    bad_plan = bad.make_frame_plan()
    broken = analyze_knill(replace(experiment, frame_plan=bad_plan), raw)
    assert normal.errors == 0 and broken.errors > 0


def test_report_has_exclusive_wall_timings_and_distinct_output_directory(tmp_path):
    run = run_knill(distance=3, shots=32, seed=420, p=0.001)
    report = save_report([run], tmp_path / "m6d_knill")
    assert report["experiments"][0]["errors"] == run.analysis.errors
    assert report["report_generation_wall"] > 0
    assert (tmp_path / "m6d_knill/knill_ler_and_timing.png").exists()
    assert "frame_map_setup" in (tmp_path / "m6d_knill/knill_timing.csv").read_text()
    with pytest.raises(ValueError, match="positive shots"):
        run_knill(shots=0)
    with pytest.raises(ValueError, match="teleportations"):
        build_knill(teleportations=0)
