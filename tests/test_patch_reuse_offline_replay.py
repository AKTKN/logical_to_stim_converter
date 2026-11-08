"""External stage adapters, honest labels and bounded offline replay over three patches."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from examples.knill_memory_offline_decoding import (
    ReadoutMatching,
    analyze_knill,
    build_knill,
    prepare_compiled,
)
from examples.knill_memory_three_patch_reuse import (
    build_explicit_three_patch_knill,
    explicit_three_patch_program,
    prepare_three_patch,
    run_three_patch,
    save_report,
)
from logical_to_stim_converter import BlockUseId, NoiseModel
from logical_to_stim_converter.decoding import (
    CorrectionBatch,
    DecoderViewError,
    OfflineFrameBatch,
    StageInputs,
)


class BoundAdapter:
    """An external adapter binding baseline hypotheses to actual use/input ordering.

    It receives only public request/current-record inputs. Optional unequal
    weights select a different Bell capacity decoder on the same physical batch.
    """

    def __init__(self, decoder, boundary):
        """Keep the caller's decoder and immutable physical correction boundary."""
        self.decoder, self.boundary = decoder, boundary

    def decode_batch(self, request, inputs):
        """Audit public causal inputs and return explicitly use-ordered correction bits."""
        assert isinstance(inputs, StageInputs)
        assert set(vars(inputs)) == {"source_fingerprint", "events", "records", "expected_sector"}
        assert not inputs.records.flags.writeable and not inputs.events.flags.writeable
        assert not hasattr(request, "expected_value") and not hasattr(inputs, "truth")
        result = self.decoder.decode_batch(request, inputs)
        return replace(
            result,
            correction=replace(
                result.correction,
                block_use_id=self.boundary.block_use_id,
                input_ids=self.boundary.input_ids,
            ),
        )


def replacement_adapters(experiment):
    """Return independently selected boundary and unequal-weight readout decoders."""
    plan = experiment.frame_plan
    boundary = {
        k: BoundAdapter(v, plan.boundary_by_id[k]) for k, v in experiment.boundary_decoders.items()
    }
    readout = {
        r.readout.module_id: BoundAdapter(
            ReadoutMatching(r, weights=np.linspace(1.0, 1.5, len(r.record_ids))),
            plan.boundary_by_id[r.readout.module_id],
        )
        for r in experiment.requests.readouts
    }
    return dict(boundary_decoders=boundary, readout_decoders=readout)


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
def test_three_cycle_noiseless_replacement_decoders_and_actual_readout_labels(distance, basis, bit):
    """Both external selections recover signed physical outputs on unchanged branches."""
    e = prepare_three_patch(distance=distance, basis=basis, bit=bit, p=0)
    raw = e.compiled.circuit.compile_sampler(seed=911).sample(64)
    before, dem = raw.copy(), e.global_dem.copy()
    for adapters in ({}, replacement_adapters(e)):
        result = analyze_knill(e, raw, **adapters)
        assert result.errors == 0 and (result.logical_values == bit).all()
        assert not result.physical_events.any() and not result.physical_observable_flips.any()
        expected = np.column_stack(
            [
                np.bitwise_xor.reduce(
                    result.interpreted_measurements[:, o.readout_measurement_indices], axis=1
                )
                ^ o.expected_value
                for o in e.compiled.observables
            ]
        )
        np.testing.assert_array_equal(result.failures, expected)
        assert result.raw_measurements.any()
    np.testing.assert_array_equal(raw, before)
    assert e.global_dem == dem == e.compiled.circuit.detector_error_model()


@pytest.mark.parametrize("basis,bit", [("X", 1), ("Z", 0)])
def test_one_noisy_batch_replayed_chunkwise_with_no_quantum_execution(monkeypatch, basis, bit):
    """Current events, corrections, predictions and honest failures are chunk independent."""
    e = prepare_three_patch(basis=basis, bit=bit, p=0.01, post_rounds=2)
    raw = e.compiled.circuit.compile_sampler(seed=912).sample(257)
    original, dem, fingerprint = raw.copy(), e.global_dem.copy(), e.frame_plan.source_fingerprint

    def forbidden(*args, **kwargs):
        """Any sampler or physical simulator invoked during replay is an error."""
        raise AssertionError("Offline stage replay cannot execute the quantum circuit")

    monkeypatch.setattr(stim.Circuit, "compile_sampler", forbidden)
    monkeypatch.setattr(stim, "TableauSimulator", forbidden)
    for adapters in ({}, replacement_adapters(e)):
        full = analyze_knill(e, raw, **adapters)
        chunks = [
            analyze_knill(e, raw[i:j], **adapters) for i, j in ((0, 13), (13, 147), (147, 257))
        ]
        assert full.errors > 0
        for name in (
            "logical_values",
            "failures",
            "interpreted_measurements",
            "final_x",
            "final_z",
        ):
            np.testing.assert_array_equal(
                np.concatenate([getattr(c, name) for c in chunks]), getattr(full, name)
            )
        for index, (module, events, decoded, sector) in enumerate(full.diagnostics):
            assert module == e.requests.order[index][1]
            np.testing.assert_array_equal(
                np.concatenate([c.diagnostics[index][1] for c in chunks]), events
            )
            np.testing.assert_array_equal(
                np.concatenate([c.diagnostics[index][2].correction.bits for c in chunks]),
                decoded.correction.bits,
            )
            for name in ("predicted_record_errors", "net_sector"):
                value = getattr(decoded, name)
                if value is not None:
                    np.testing.assert_array_equal(
                        np.concatenate([getattr(c.diagnostics[index][2], name) for c in chunks]),
                        value,
                    )
            if sector is not None:
                np.testing.assert_array_equal(
                    np.concatenate([c.diagnostics[index][3] for c in chunks]), sector
                )
        expected = np.column_stack(
            [
                np.bitwise_xor.reduce(
                    full.interpreted_measurements[:, o.readout_measurement_indices], axis=1
                )
                ^ bit
                for o in e.compiled.observables
            ]
        )
        np.testing.assert_array_equal(full.failures, expected)
    np.testing.assert_array_equal(raw, original)
    assert e.global_dem == dem and e.frame_plan.source_fingerprint == fingerprint


def test_count_one_sampler_one_sample_per_batch_all_boundaries_once(monkeypatch):
    """Three bounded sample calls feed causal offline corrections without stage resampling."""
    compile_calls, sample_calls, applications = [], [], []
    original_compile, original_apply = stim.Circuit.compile_sampler, OfflineFrameBatch.apply

    class SamplerSpy:
        """Delegate one fixed Stim sampler while recording requested batch sizes."""

        def __init__(self, sampler):
            """Retain the already compiled physical sampler."""
            self.sampler = sampler

        def sample(self, *, shots):
            """Sample exactly this batch once."""
            sample_calls.append(shots)
            return self.sampler.sample(shots=shots)

    def compile_spy(circuit, *args, **kwargs):
        """Record the only static circuit compilation for physical sampling."""
        compile_calls.append(circuit.copy())
        return SamplerSpy(original_compile(circuit, *args, **kwargs))

    def apply_spy(state, correction):
        """Count each unique boundary once per raw batch."""
        applications.append(correction.boundary_id)
        return original_apply(state, correction)

    monkeypatch.setattr(stim.Circuit, "compile_sampler", compile_spy)
    monkeypatch.setattr(OfflineFrameBatch, "apply", apply_spy)
    run = run_three_patch(shots=19, batch_size=8, seed=913, p=0)
    assert len(compile_calls) == 1 and sample_calls == [8, 8, 3]
    order = [module for _, module in run.experiment.requests.order]
    assert applications == order * 3
    assert run.errors == 0 and run.shots == 19 and run.batches == 3
    assert not hasattr(run, "raw_measurements")
    assert sum(v for k, v in run.timings.items() if k != "total_wall") == pytest.approx(
        run.timings["total_wall"], abs=1e-8
    )


def test_later_byproduct_omission_and_epoch_boundary_confusion_fail():
    """Physical output breaks when a later Bell bit is omitted; stale epochs reject."""
    e = prepare_three_patch(basis="X", p=0)
    raw = e.compiled.circuit.compile_sampler(seed=914).sample(64)
    normal = analyze_knill(e, raw)
    bells = list(e.compiled.bell_measurements)
    bell = bells[2]
    bells[2] = replace(
        bell,
        x_readout=replace(
            bell.x_readout, logical_parity=replace(bell.x_readout.logical_parity, terms=())
        ),
    )
    corrupted = replace(e.compiled, bell_measurements=tuple(bells))
    broken = analyze_knill(prepare_compiled(corrupted), raw)
    assert normal.errors == 0 and broken.errors > 0
    p = next(p for p in e.compiled.preparations if p.block_use_id == BlockUseId("P0", 2))
    boundary = e.frame_plan.boundary_by_id[p.module_id]
    state = e.frame_plan.start(raw, source_fingerprint=e.frame_plan.source_fingerprint)
    bits = np.zeros((len(raw), len(boundary.input_ids)), dtype=bool)
    with pytest.raises(DecoderViewError, match="different physical use"):
        state.apply(
            CorrectionBatch(e.frame_plan.source_fingerprint, p.module_id, bits, BlockUseId("P0", 0))
        )
    state.apply(
        CorrectionBatch(
            e.frame_plan.source_fingerprint, p.module_id, bits, p.block_use_id, boundary.input_ids
        )
    )
    with pytest.raises(DecoderViewError, match="already applied"):
        state.apply(CorrectionBatch(e.frame_plan.source_fingerprint, p.module_id, bits))


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_fresh_and_reused_finite_noise_independent_stream_confidence(basis):
    """Compare independent seeds using conservative 99.99% Wilson intervals, never raw equality."""
    reused = prepare_three_patch(basis=basis, p=0.002)
    fresh = prepare_compiled(
        build_knill(
            basis=basis, teleportations=3, noise_model=NoiseModel.uniform_depolarizing(0.002)
        )
    )
    results = []
    for e, seed in ((reused, 915), (fresh, 916)):
        raw = e.compiled.circuit.compile_sampler(seed=seed).sample(2048)
        result = analyze_knill(e, raw)
        np.testing.assert_array_equal(result.failures, result.logical_values)
        results.append(result)
    z, n = 3.891, 2048
    intervals = []
    for r in results:
        p = r.errors / n
        center = (p + z * z / (2 * n)) / (1 + z * z / n)
        radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        intervals.append((center - radius, center + radius))
    assert max(lo for lo, hi in intervals) <= min(hi for lo, hi in intervals)


def test_ten_cycle_bounded_batch_smoke_history_growth_and_report(tmp_path):
    """Ten complete cycles retain fixed physical width while circuit/record histories grow."""
    run = run_three_patch(teleportations=10, shots=9, batch_size=4, seed=917, p=0, bit=1)
    c = run.experiment.compiled
    assert c.circuit.num_qubits == 51 and run.errors == 0 and run.batches == 3
    assert len(c.block_uses) == 21 and len(c.relocation_history) == 10
    assert len(set(m.key for m in c.measurements)) == len(c.measurements)
    short = build_explicit_three_patch_knill()
    assert len(c.measurements) > len(short.measurements)
    assert len(c.detectors) > len(short.detectors) and len(c.fragments) > len(short.fragments)
    for layer in c.time_layers:
        assert len(layer.active_use_ids) == len({u.block_id for u in layer.active_use_ids})
    report = save_report([run], tmp_path)
    summary = report["experiments"][0]
    assert summary["physical_patch_count"] == 3 and len(summary["cycles"]) == 10
    assert summary["cycles"][2]["output_use"] == {"block_id": "P0", "epoch": 2}
    assert summary["source_fingerprint"] == run.experiment.frame_plan.source_fingerprint
    assert len(summary["stages"]) == len(run.experiment.requests.order)
    assert report["report_generation_wall"] > 0
    assert (tmp_path / "three_patch_ler_and_timing.svg").exists()
    assert (tmp_path / "three_patch_ler_and_timing.png").exists()
    assert (tmp_path / "three_patch_results.json").exists()
    assert "frame_map_setup" in (tmp_path / "three_patch_timing.csv").read_text()
    assert not any(p.suffix in (".npy", ".npz") for p in tmp_path.iterdir())


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(teleportations=0),
        dict(post_rounds=-1),
        dict(schedule=(("P0", "P1", "P2"),)),
        dict(basis="Y"),
        dict(schedule=(("P0", "P1", "P2"), ("P0", "P1", "P2"), ("P1", "P2", "P0"))),
    ],
)
def test_invalid_explicit_program_rejected(kwargs):
    """Reject malformed authoring parameters before presenting a schedule to the compiler."""
    with pytest.raises(ValueError):
        explicit_three_patch_program(**kwargs)


def test_invalid_sampling_and_noise_choices_rejected():
    """A LER run needs positive bounded batches and an actual final physical readout."""
    for kwargs in (dict(shots=0), dict(batch_size=0), dict(seed=-1), dict(allow_open_outputs=True)):
        with pytest.raises(ValueError):
            run_three_patch(**kwargs)
    with pytest.raises(ValueError):
        prepare_three_patch(p=0.001, noise_model=NoiseModel())
