"""Shared physical records through unchanged external memory and Knill decoders."""

import numpy as np
import pytest
import stim

from examples.knill_memory_offline_decoding import analyze_knill, prepare_compiled
from examples.memory_offline_decoding import analyze_memory
from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    BlockUseId,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    SyndromeExtraction,
)
from tests.helpers.knill_physics import corrected_expectation, explicit_reference, pauli, simulate
from tests.helpers.lstim_equivalence import (
    assert_exact,
    assert_experiment_equal,
    compile_pair,
    declarations,
)
from tests.helpers.lstim_programs import knill_operations, knill_source
from tests.helpers.preparation_matching import preparation_corrections
from tests.test_patch_reuse_offline_replay import replacement_adapters


def prohibit_quantum_execution(monkeypatch):
    """Offline replay may transform records/build models, but never sample trajectories."""
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline decoding attempted quantum execution")

    monkeypatch.setattr(stim.Circuit, "compile_sampler", forbidden)
    monkeypatch.setattr(stim.Circuit, "compile_detector_sampler", forbidden)
    monkeypatch.setattr(stim, "TableauSimulator", forbidden)
    monkeypatch.setattr(stim, "FlipSimulator", forbidden)


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis,bit,mode", [
    ("X", 0, "physical"), ("Z", 1, "physical"), ("X", 1, "frame"), ("Z", 0, "frame"),
])
@pytest.mark.parametrize("p", [0, .003])
def test_ordinary_memory_same_raw_mwpm_predictions_labels_and_ler(
    monkeypatch, distance, basis, bit, mode, p,
):
    source = declarations(distance) + f"BIND D P0\nINIT_{basis}({distance}) D\n"
    operations = [BindPatch("D", "P0"), LogicalInit("D", basis, distance)]
    if bit:
        axis = "Z" if basis == "X" else "X"
        source += f"{axis}[sign] D mode={mode}\n"
        operations.append(LogicalPauli("D", axis, mode=mode, operation_id="sign"))
    source += f"REPEAT 2 {{\n    SE(1) D\n}}\nM{basis} D\n"
    operations.extend((SyndromeExtraction("D", 1), SyndromeExtraction("D", 1),
                       LogicalMeasure("D", basis)))
    # Unicode comments and diagnostic file names must not become physical source identity.
    actual, reference = compile_pair(
        "# frontend provenance 注釈\n" + source, operations, distance=distance,
        noise=NoiseModel.uniform_depolarizing(p),
    )
    raw = assert_experiment_equal(actual, reference, shots=129, seed=821)
    original, dem = raw.copy(), actual.circuit.detector_error_model()
    prohibit_quantum_execution(monkeypatch)
    text_result = analyze_memory(actual, raw)
    direct_result = analyze_memory(reference, raw)
    assert text_result.global_dem == direct_result.global_dem == dem
    for name in ("raw_measurements", "detection_events", "observable_flips"):
        assert_exact(getattr(text_result, name), getattr(direct_result, name))
    logical_bits = actual.interpreted_measurements(raw)
    np.testing.assert_array_equal(logical_bits ^ bit, text_result.observable_flips)
    assert len(text_result.strategies) == len(direct_result.strategies) == 3
    for a, b in zip(text_result.strategies, direct_result.strategies, strict=True):
        assert a.strategy == b.strategy
        assert_exact(a.view, b.view)
        assert_exact(a.predicted_flips, b.predicted_flips)
        assert_exact(a.failures, b.failures)
        labels = a.view.project_observable_flips(text_result.observable_flips)
        np.testing.assert_array_equal(a.failures, a.predicted_flips ^ labels)
        assert a.logical_errors == b.logical_errors
        assert a.per_observable_errors == b.per_observable_errors
        assert a.logical_error_rate == b.logical_error_rate == a.logical_errors / len(raw)
        if p == 0:
            assert a.logical_errors == 0
    assert_exact(raw, original)
    assert actual.circuit.detector_error_model() == dem


@pytest.mark.parametrize("p", [0, .003])
def test_independent_observables_keep_sorted_logical_ids_and_local_decoding(monkeypatch, p):
    source = declarations(3, 2) + """BIND z_input P0
BIND a_input P1
PARALLEL {
    INIT_X(3) z_input
    INIT_Z(3) a_input
}
Z z_input mode=frame
PARALLEL {
    SE(3) z_input
    SE(1) a_input
}
PARALLEL {
    MX z_input
    MZ a_input
}
"""
    operations = (
        BindPatch("z_input", "P0"), BindPatch("a_input", "P1"),
        (LogicalInit("z_input", "X", 3), LogicalInit("a_input", "Z", 3)),
        LogicalPauli("z_input", "Z", mode="frame"),
        (SyndromeExtraction("z_input", 3), SyndromeExtraction("a_input", 1)),
        (LogicalMeasure("z_input", "X"), LogicalMeasure("a_input", "Z")),
    )
    actual, reference = compile_pair(
        source, operations, count=2, noise=NoiseModel.uniform_depolarizing(p),
    )
    raw = assert_experiment_equal(actual, reference, shots=65, seed=827)
    prohibit_quantum_execution(monkeypatch)
    a, b = analyze_memory(actual, raw), analyze_memory(reference, raw)
    assert [o.logical_id for o in actual.observables] == ["a_input", "z_input"]
    np.testing.assert_array_equal(actual.interpreted_measurements(raw) ^ [0, 1], a.observable_flips)
    assert len(a.strategies) == len(b.strategies) == 5
    for x, y in zip(a.strategies, b.strategies, strict=True):
        assert_exact(x.view, y.view)
        assert_exact(x.predicted_flips, y.predicted_flips)
        assert_exact(x.failures, y.failures)
        assert x.logical_errors == y.logical_errors
        assert x.logical_error_rate == y.logical_error_rate
        assert x.per_observable_errors == y.per_observable_errors
        np.testing.assert_array_equal(x.failures, x.predicted_flips ^
                                      x.view.project_observable_flips(a.observable_flips))


class AuditedDecoder:
    """Test adapter recording exactly the public causal inputs received at each stage."""

    def __init__(self, decoder, calls, module):
        self.decoder, self.calls, self.module = decoder, calls, module

    def decode_batch(self, request, inputs):
        assert not inputs.events.flags.writeable and not inputs.records.flags.writeable
        assert not hasattr(inputs, "truth")
        self.calls.append((self.module, request.block_use_id, inputs))
        return self.decoder.decode_batch(request, inputs)


def audited_adapters(experiment, *, replacement=False):
    """Use existing external baseline or M7 replacement adapters, never a new decoder."""
    choices = replacement_adapters(experiment) if replacement else dict(
        boundary_decoders=experiment.boundary_decoders,
        readout_decoders=experiment.readout_decoders,
    )
    calls = []
    return {
        kind: {module: AuditedDecoder(decoder, calls, module) for module, decoder in items.items()}
        for kind, items in choices.items()
    }, calls


def assert_knill_analysis_equal(actual, reference):
    """All physical/offline outputs match; phase wall times are observations only."""
    for name in (
        "raw_measurements", "physical_events", "physical_observable_flips",
        "interpreted_measurements", "logical_values", "failures", "final_x", "final_z",
    ):
        assert_exact(getattr(actual, name), getattr(reference, name))
    assert actual.errors == reference.errors
    assert actual.logical_error_rate == reference.logical_error_rate
    assert len(actual.diagnostics) == len(reference.diagnostics)
    for a, b in zip(actual.diagnostics, reference.diagnostics, strict=True):
        module, events, decoded, sector = a
        other, other_events, other_decoded, other_sector = b
        assert module == other
        assert_exact(events, other_events)
        assert_exact(sector, other_sector)
        for name in ("correction", "predicted_record_errors", "net_sector"):
            assert_exact(getattr(decoded, name), getattr(other_decoded, name))


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
@pytest.mark.parametrize("p", [0, .003])
def test_three_patch_knill_same_raw_stages_frames_labels_and_ler(
    monkeypatch, distance, basis, bit, p,
):
    parameters = dict(distance=distance, basis=basis, bit=bit)
    actual, reference = compile_pair(
        knill_source(**parameters), knill_operations(**parameters), distance=distance, count=3,
        noise=NoiseModel.uniform_depolarizing(p),
    )
    a, b = prepare_compiled(actual), prepare_compiled(reference)
    assert_exact(a.frame_plan, b.frame_plan)
    assert_exact(a.requests, b.requests)
    assert_exact(a.conditional_models, b.conditional_models)
    assert len(a.conditional_models) == 3
    for request in a.requests.boundaries:
        assert len(request.target_ids) == len(request.checks) + (request.preparation is not None)
        assert sum(i.name == "MPP" for i in request.model_circuit) == len(request.target_ids)
        assert all(actual.measurements[i].key.block_use_id == request.block_use_id
                   for i in request.last_record_ids)
    for model in a.conditional_models:
        first = actual.circuit[model.start_instruction]
        assert first.tag == model.resource_entangling_module_id and first.name == "CX"
        assert model.output_preparation_module_id in {p.module_id for p in actual.preparations}
    if (distance, basis, bit, p) == (3, "Z", 0, .003):
        from tests.test_patch_reuse_knill_e2e import assert_physical_conditional_atoms

        for model in a.conditional_models:
            assert_physical_conditional_atoms(actual, model)
    raw = assert_experiment_equal(actual, reference, shots=33, seed=822)
    before, canonical = raw.copy(), actual.circuit.detector_error_model()
    prohibit_quantum_execution(monkeypatch)
    for replacement in (False, True):
        a_adapters, a_calls = audited_adapters(a, replacement=replacement)
        b_adapters, b_calls = audited_adapters(b, replacement=replacement)
        text_result = analyze_knill(a, raw, **a_adapters)
        direct_result = analyze_knill(b, raw, **b_adapters)
        assert_knill_analysis_equal(text_result, direct_result)
        assert_exact(a_calls, b_calls)
        assert [module for module, _, _ in a_calls] == [m for _, m in a.requests.order]
        expected = np.column_stack([
            np.bitwise_xor.reduce(
                text_result.interpreted_measurements[:, o.readout_measurement_indices], axis=1,
            ) ^ o.expected_value
            for o in actual.observables
        ])
        np.testing.assert_array_equal(text_result.failures, expected)
        if p == 0:
            assert text_result.errors == 0 and (text_result.logical_values == bit).all()
    assert_exact(raw, before)
    assert a.global_dem == b.global_dem == canonical == actual.circuit.detector_error_model()


def assert_chunked_analysis(full, chunks):
    """Concatenation must commute with every stage prediction and frame application."""
    for name in (
        "raw_measurements", "physical_events", "physical_observable_flips",
        "interpreted_measurements", "logical_values", "failures", "final_x", "final_z",
    ):
        np.testing.assert_array_equal(
            np.concatenate([getattr(chunk, name) for chunk in chunks]), getattr(full, name),
        )
    assert full.errors == sum(chunk.errors for chunk in chunks)
    for index, (module, events, result, sector) in enumerate(full.diagnostics):
        assert all(c.diagnostics[index][0] == module for c in chunks)
        np.testing.assert_array_equal(
            np.concatenate([c.diagnostics[index][1] for c in chunks]), events,
        )
        np.testing.assert_array_equal(
            np.concatenate([c.diagnostics[index][2].correction.bits for c in chunks]),
            result.correction.bits,
        )
        for name in ("predicted_record_errors", "net_sector"):
            value = getattr(result, name)
            if value is not None:
                np.testing.assert_array_equal(
                    np.concatenate([getattr(c.diagnostics[index][2], name) for c in chunks]), value,
                )
        if sector is not None:
            np.testing.assert_array_equal(
                np.concatenate([c.diagnostics[index][3] for c in chunks]), sector,
            )


@pytest.mark.parametrize("basis,bit", [("X", 1), ("Z", 0)])
def test_knill_257_shots_replayed_as_13_134_110_without_resampling(monkeypatch, basis, bit):
    params = dict(basis=basis, bit=bit)
    actual, reference = compile_pair(
        knill_source(**params), knill_operations(**params), count=3,
        noise=NoiseModel.uniform_depolarizing(.01),
    )
    a, b = prepare_compiled(actual), prepare_compiled(reference)
    compile_calls, sample_calls = [], []
    original_compile = stim.Circuit.compile_sampler

    class CountSampler:
        def __init__(self, sampler):
            self.sampler = sampler

        def sample(self, shots):
            sample_calls.append(shots)
            return self.sampler.sample(shots)

    def compile_spy(circuit, **kwargs):
        compile_calls.append(circuit)
        return CountSampler(original_compile(circuit, **kwargs))

    monkeypatch.setattr(stim.Circuit, "compile_sampler", compile_spy)
    raw = actual.circuit.compile_sampler(seed=823).sample(257)
    before, dem = raw.copy(), a.global_dem.copy()
    prohibit_quantum_execution(monkeypatch)
    for replacement in (False, True):
        a_adapters, a_calls = audited_adapters(a, replacement=replacement)
        b_adapters, b_calls = audited_adapters(b, replacement=replacement)
        full_a = analyze_knill(a, raw, **a_adapters)
        full_b = analyze_knill(b, raw, **b_adapters)
        assert_knill_analysis_equal(full_a, full_b)
        assert_exact(a_calls, b_calls)
        stage_inputs = tuple(a_calls)
        a_calls.clear()
        b_calls.clear()
        slices = ((0, 13), (13, 147), (147, 257))
        chunks_a = [analyze_knill(a, raw[i:j], **a_adapters) for i, j in slices]
        chunks_b = [analyze_knill(b, raw[i:j], **b_adapters) for i, j in slices]
        assert_exact(a_calls, b_calls)
        for x, y in zip(chunks_a, chunks_b, strict=True):
            assert_knill_analysis_equal(x, y)
        assert_chunked_analysis(full_a, chunks_a)
        assert_chunked_analysis(full_b, chunks_b)
        for index, (module, use, inputs) in enumerate(stage_inputs):
            parts = [a_calls[i * len(stage_inputs) + index] for i in range(3)]
            assert all(m == module and u == use for m, u, _ in parts)
            for name in ("events", "records", "expected_sector"):
                value = getattr(inputs, name)
                if value is not None:
                    np.testing.assert_array_equal(
                        np.concatenate([getattr(part[2], name) for part in parts]), value,
                    )
    assert compile_calls == [actual.circuit] and sample_calls == [257]
    assert_exact(raw, before)
    assert a.global_dem == b.global_dem == dem == actual.circuit.detector_error_model()


def test_encoded_reference_and_all_bell_branches_with_independent_physical_tableaux():
    source = declarations(3, 4) + """BIND R P3
BIND D P0
BIND A0 P1
BIND B0 P2
BELL_PREP[encoded_reference](3) R D
KNILL_EC[cycle0](3) D A0 B0
BIND A1 P0
BIND B1 P1
KNILL_EC[cycle1](3) D A1 B1
BIND A2 P2
BIND B2 P0
KNILL_EC[cycle2](3) D A2 B2
"""
    operations = (
        BindPatch("R", "P3"), BindPatch("D", "P0"), BindPatch("A0", "P1"), BindPatch("B0", "P2"),
        BellStatePrep("R", "D", 3, operation_id="encoded_reference"),
        KnillEC("D", "A0", "B0", rounds=3, operation_id="cycle0"),
        BindPatch("A1", "P0"), BindPatch("B1", "P1"),
        KnillEC("D", "A1", "B1", rounds=3, operation_id="cycle1"),
        BindPatch("A2", "P2"), BindPatch("B2", "P0"),
        KnillEC("D", "A2", "B2", rounds=3, operation_id="cycle2"),
    )
    actual, reference = compile_pair(source, operations, count=4, open_outputs=True)
    assert_experiment_equal(actual, reference)
    assert actual.circuit.num_qubits == 68  # Three working patches plus the untouched reference.
    assert all("encoded_reference" in f.composite_ids
               for f in actual.fragments if "P3" in f.block_ids)
    raw, simulators = simulate(actual, range(32))
    corrections = preparation_corrections(actual, raw)
    result = actual.evaluate_frames(raw, corrections)
    for bell in actual.bell_measurements:
        mx = bell.x_readout.logical_parity.evaluate(
            result.corrected_measurements, actual.measurement_index_by_key,
        )
        mz = bell.z_readout.logical_parity.evaluate(
            result.corrected_measurements, actual.measurement_index_by_key,
        )
        assert len(set(zip(mx, mz, strict=True))) == 4
    for shot, simulator in enumerate(simulators):
        frames = [result.final_frames[q][shot] for q in ("R", "D")]
        for basis in "XZ":
            operator = pauli(actual, "R", basis) * pauli(actual, "D", basis)
            assert corrected_expectation(simulator, actual, operator, frames) == 1
            assert simulator.peek_observable_expectation(pauli(actual, "D", basis)) == 0
    physical = explicit_reference(
        actual, result.corrected_measurements[0], {k: v[:1] for k, v in corrections.items()},
    )
    for basis in "XZ":
        assert physical.peek_observable_expectation(
            pauli(actual, "R", basis) * pauli(actual, "D", basis),
        ) == 1


def test_reset_extinguishes_physical_fault_but_preserves_historical_bell_feedback():
    from tests.test_patch_reuse_knill_e2e import injected_fault

    actual, reference = compile_pair(
        knill_source(open_outputs=True), knill_operations(open_outputs=True),
        count=3, open_outputs=True,
    )
    raw, simulators = simulate(actual, range(16))
    corrections = preparation_corrections(actual, raw)
    good = actual.evaluate_frames(raw, corrections)
    wrong_raw = raw.copy()
    first_bell = actual.bell_measurements[0]
    key = first_bell.z_readout.logical_parity.terms[0]
    wrong_raw[:, actual.measurement_index_by_key[key]] ^= True
    wrong = actual.evaluate_frames(wrong_raw, corrections, validation="hypothesis")
    assert any(
        corrected_expectation(sim, actual, pauli(actual, "D", "Z"), [wrong.final_frames["D"][i]])
        != corrected_expectation(sim, actual, pauli(actual, "D", "Z"), [good.final_frames["D"][i]])
        for i, sim in enumerate(simulators)
    )
    assert_exact(good, reference.evaluate_frames(raw, corrections))
    fresh = next(p for p in actual.preparations if p.block_use_id == BlockUseId("P0", 2))
    reset = next(i for i, inst in enumerate(actual.ideal_circuit)
                 if inst.tag == fresh.module_id and inst.name in ("R", "RX"))
    signatures = []
    for before in (True, False):
        oracle = stim.FlipSimulator(batch_size=1, num_qubits=51,
                                    disable_stabilizer_randomization=True)
        oracle.do(injected_fault(actual, reset, before=before))
        x, z = oracle.to_numpy(transpose=True, output_xs=True, output_zs=True)[:2]
        signatures.append(np.concatenate((x, z), axis=1))
    assert not signatures[0].any()
    assert signatures[1].any()
