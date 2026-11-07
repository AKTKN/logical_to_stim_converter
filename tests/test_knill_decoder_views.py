"""Exact boundary targets, conditional fault actions and software frame physics."""

import numpy as np
import pytest
import stim

from examples.knill_memory_offline_decoding import (
    analyze_knill,
    prepare_compiled,
    prepare_experiment,
)
from logical_to_stim_converter import (
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    SyndromeExtraction,
    TransversalH,
)
from logical_to_stim_converter.decoding import (
    CorrectionBatch,
    DecoderViewError,
    SourceMismatchError,
    make_stage_requests,
)
from tests.helpers.knill_physics import explicit_reference, make_compiler


def noiseless_with_fault(circuit, fault):
    """TEST-ONLY physical injection. Preserve every record and annotation."""
    result = stim.Circuit()
    cursor = 0
    for i, inst in enumerate(circuit):
        if i == fault.instruction_index and fault.measurement_record is not None:
            for j, t in enumerate(inst.targets_copy()):
                result.append(
                    inst.name, [t], int(cursor + j == fault.measurement_record), tag=inst.tag
                )
        else:
            single = stim.Circuit()
            single.append(inst)
            result += single.without_noise()
        if i == fault.instruction_index:
            for q, axis in fault.paulis:
                result.append(axis + "_ERROR", [q], 1)
        cursor += inst.num_measurements
    return result


@pytest.mark.parametrize("distance", [3, 5])
def test_stage_partition_gauge_records_and_conditional_sector_metadata(distance):
    ex = prepare_experiment(distance=distance, teleportations=2, p=0.001, post_rounds=2)
    c = ex.compiled
    assert len(c.detector_boundary_candidates) > 0
    for request in ex.requests.boundaries:
        own = set(request.view.measurement_map.global_ids)
        for d in request.view.detectors:
            assert set(d.measurement_indices) <= own
        assert request.detector_error_model.num_observables == len(request.target_ids)
        assert request.model_circuit.num_measurements > max(request.last_record_ids)
        assert (
            request.model_circuit.detector_error_model(decompose_errors=True)
            == request.detector_error_model
        )
        if request.preparation is not None:
            assert request.preparation.gauge_measurements
            for k in request.preparation.gauge_measurements:
                i = c.measurement_index_by_key[k]
                assert i in own
                assert not any(d.measurement_indices == (i,) for d in request.view.detectors)
    for request in ex.requests.readouts:
        assert len(request.record_ids) == distance * distance
        assert request.check_matrix.shape == ((distance * distance - 1) // 2, distance * distance)
        assert request.view.measurement_map.global_ids == request.record_ids
        assert request.sector_map.input_size == len(ex.requests.sector_input_ids)
    assert c.circuit.num_detectors == len(c.detectors)
    assert not any(i.name == "MPP" for i in c.circuit)


def test_expected_bell_sector_is_shot_specific_when_preparation_frames_are_omitted():
    ex = prepare_experiment(p=0, post_rounds=0)
    raw = ex.compiled.circuit.compile_sampler(seed=431).sample(128)

    class UncorrectedSectors:
        def decode_batch(self, request, inputs):
            from logical_to_stim_converter.decoding import StageResult

            indices = request.view.measurement_map.global_to_local
            sector = inputs.records[:, [indices[i] for i in request.last_record_ids]]
            return StageResult(
                CorrectionBatch(
                    inputs.source_fingerprint,
                    request.module_id,
                    np.zeros((len(sector), 2 * len(request.data_ids)), dtype=bool),
                ),
                np.zeros_like(sector),
                sector,
            )

    result = analyze_knill(
        ex,
        raw,
        boundary_decoders={r.module_id: UncorrectedSectors() for r in ex.requests.boundaries},
    )
    assert any(expected is not None and expected.any() for _, _, _, expected in result.diagnostics)
    # Relative syndrome is zero; forcing unconditional zero would invent readout faults.
    for module, _, output, expected in result.diagnostics:
        if expected is not None:
            assert not output.correction.bits.any()
            r = next(r for r in ex.requests.readouts if r.readout.module_id == module)
            samples = result.interpreted_measurements[:, r.record_ids].astype(np.uint8)
            assert np.array_equal(samples @ r.check_matrix.T % 2, expected)


@pytest.mark.parametrize("kind", ["early", "late"])
def test_temporal_preparation_model_has_verified_measurement_error_targets(kind):
    from logical_to_stim_converter import NoiseParameters

    ex = prepare_experiment(noise_model=NoiseModel(NoiseParameters(measurement=0.001)))
    request = ex.requests.boundaries[0]
    check = next(c for c in request.checks if c.basis == request.preparation.basis)
    key = check.measurements[0 if kind == "early" else -1]
    target_record = ex.compiled.measurement_index_by_key[key]
    circuit = request.model_circuit
    cursor = 0
    physical = stim.Circuit()
    for inst in circuit:
        if inst.name in ("M", "MX") and cursor <= target_record < cursor + inst.num_measurements:
            for j, t in enumerate(inst.targets_copy()):
                physical.append(inst.name, [t], int(cursor + j == target_record), tag=inst.tag)
        else:
            one = stim.Circuit()
            one.append(inst)
            physical += one.without_noise()
        cursor += inst.num_measurements
    raw = physical.compile_sampler(seed=432).sample(32)
    events, targets = circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    expected = np.zeros_like(targets)
    if kind == "late":
        expected[:, request.checks.index(check)] = True
    assert np.array_equal(targets, expected)
    predicted = ex.boundary_decoders[request.module_id].temporal.decode_batch(
        events, enable_correlations=True
    )
    assert np.array_equal(predicted, expected)
    # A raw last-sector capacity solver alone cannot distinguish this late result fault.
    if kind == "late":
        last = np.asarray(raw[:, request.last_record_ids], dtype=bool)
        assert last[:, request.checks.index(check)].all()
        assert not (last ^ predicted[:, : len(request.checks)])[
            :, request.checks.index(check)
        ].any()


@pytest.mark.parametrize("distance", [3, 5])
def test_conditional_bell_fault_actions_against_stim_pauli_oracle(distance):
    ex = prepare_experiment(distance=distance, p=0.001, post_rounds=0)
    c = ex.compiled
    model = ex.conditional_models[0]
    atoms = model.faults
    assert any(f.channel == "DEPOLARIZE2" for f in atoms)
    assert any(f.measurement_record is not None for f in atoms)
    grouped = {}
    for f in atoms:
        grouped.setdefault(f.exclusive_group, []).append(f)
    assert all(
        sum(f.probability for f in group) == pytest.approx(0.001) for group in grouped.values()
    )
    # This is a Pauli-action oracle, not quantum sampling. All conditional
    # fault atoms are checked in one vectorized, deterministic Stim batch.
    oracle = stim.FlipSimulator(
        batch_size=len(atoms),
        num_qubits=c.circuit.num_qubits,
        disable_stabilizer_randomization=True,
    )
    by_instruction = {}
    for row, fault in enumerate(atoms):
        by_instruction.setdefault(fault.instruction_index, []).append((row, fault))
    cursor = 0
    for index, inst in enumerate(c.circuit[: model.end_instruction]):
        entries = by_instruction.get(index, ())
        for axis in "XYZ":
            mask = np.zeros((c.circuit.num_qubits, len(atoms)), dtype=bool)
            for row, fault in entries:
                if fault.measurement_record is not None:
                    ts = inst.targets_copy()
                    q = ts[fault.measurement_record - cursor].value
                    if axis == ("Z" if inst.name == "MX" else "X"):
                        mask[q, row] = True
            if mask.any():
                oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
        one = stim.Circuit()
        one.append(inst)
        oracle.do(one.without_noise())
        for axis in "XYZ":
            mask = np.zeros((c.circuit.num_qubits, len(atoms)), dtype=bool)
            for row, fault in entries:
                for q, pauli_axis in fault.paulis:
                    if pauli_axis == axis:
                        mask[q, row] = True
            if mask.any():
                oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
        cursor += inst.num_measurements
    xs, zs, flips, _, _ = oracle.to_numpy(
        transpose=True, output_xs=True, output_zs=True, output_measure_flips=True
    )
    assert np.array_equal(
        model.raw_flip_map.incidence_matrix.toarray(), flips[:, model.readout_record_ids]
    )
    prep = next(p for p in c.preparations if p.block_id == c.bell_measurements[0].output_block_id)
    ids = [c.physical_qubit_map[prep.block_id, q] for q in prep.data_ids]
    assert np.array_equal(model.output_x_map.incidence_matrix.toarray(), xs[:, ids])
    assert np.array_equal(model.output_z_map.incidence_matrix.toarray(), zs[:, ids])
    n = len(c.bell_measurements[0].x_readout.records)
    selected = model.raw_flip_map.incidence_matrix.toarray()
    for offset, readout, transform in (
        (0, c.bell_measurements[0].x_readout, model.x_syndrome_map),
        (n, c.bell_measurements[0].z_readout, model.z_syndrome_map),
    ):
        assert np.array_equal(
            transform.incidence_matrix.toarray(),
            selected[:, offset : offset + n] @ readout.check_matrix(readout.basis).T % 2,
        )
    assert any(f.channel == "DEPOLARIZE2" and len(f.paulis) == 2 for f in atoms)


def test_frame_dependent_future_events_and_independent_physical_correction_reference():
    c = make_compiler().compile(
        [
            LogicalInit("D", "X", 3),
            KnillEC("D", "A", "B"),
            SyndromeExtraction("D", 2),
            LogicalMeasure("D", "X"),
        ]
    )
    plan = c.make_frame_plan()
    raw = c.circuit.compile_sampler(seed=433).sample(8)
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    physical_events, _ = c.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    view = c.make_decoder_view()
    before = state.events(view)
    prep = c.preparations[1]
    bits = np.zeros((len(raw), 2 * len(prep.data_ids)), dtype=bool)
    bits[:, 0] = True
    boundary = plan.boundary_by_id[prep.module_id]
    state.apply(CorrectionBatch(plan.source_fingerprint, prep.module_id, bits))
    after = state.events(view)
    expected_delta = view.detector_record_map.apply(boundary.record_map.apply(bits))
    assert expected_delta.any() and np.array_equal(after ^ before, expected_delta)
    converted, _ = c.circuit.compile_m2d_converter().convert(
        measurements=state.interpreted_measurements, separate_observables=True
    )
    assert np.array_equal(after, converted)
    assert not physical_events.any() and np.array_equal(state.raw_measurements, raw)
    corrections = {
        p.module_id: tuple(
            p.resolve(bits[s, : len(p.data_ids)], bits[s, len(p.data_ids) :])
            if p == prep
            else p.resolve(np.zeros(len(p.data_ids)), np.zeros(len(p.data_ids)))
            for s in range(len(raw))
        )
        for p in c.preparations
    }
    evaluated = c.evaluate_frames(raw, corrections, validation="hypothesis")
    assert np.array_equal(evaluated.corrected_measurements, state.interpreted_measurements)
    explicit_reference(
        c, state.interpreted_measurements[0], {k: v[:1] for k, v in corrections.items()}
    )
    with pytest.raises(DecoderViewError, match="already applied"):
        state.apply(CorrectionBatch(plan.source_fingerprint, prep.module_id, bits))
    with pytest.raises(SourceMismatchError):
        plan.start(raw, source_fingerprint="wrong")
    with pytest.raises(SourceMismatchError):
        plan.start(raw, source_fingerprint=plan.source_fingerprint).apply(
            CorrectionBatch("wrong", prep.module_id, bits)
        )
    with pytest.raises(DecoderViewError):
        plan.start(raw, source_fingerprint=plan.source_fingerprint).apply(
            CorrectionBatch(plan.source_fingerprint, prep.module_id, bits[:, :-1])
        )


@pytest.mark.parametrize("mode", ["physical", "frame"])
def test_actual_h_cnot_orientation_and_virtual_physical_paulis(mode):
    c = make_compiler().compile(
        [
            LogicalInit("D", "Z", 3),
            TransversalH("D"),
            KnillEC("D", "A", "B"),
            TransversalH("D"),
            LogicalPauli("D", "X", mode=mode),
            SyndromeExtraction("D", 2),
            LogicalMeasure("D", "Z"),
        ]
    )
    ex = prepare_compiled(c)
    raw = c.circuit.compile_sampler(seed=434).sample(64)
    result = analyze_knill(ex, raw)
    assert not result.failures.any() and result.logical_values.all()
    assert any(r.readout.orientation == 1 for r in ex.requests.readouts)


def test_parallel_knill_and_spectator_isolation():
    c = make_compiler(3, "DABEFCG").compile(
        [
            [LogicalInit("D", "Z", 3), LogicalInit("E", "X", 3), LogicalInit("G", "Z", 3)],
            [KnillEC("D", "A", "B"), KnillEC("E", "F", "C")],
            [LogicalMeasure("D", "Z"), LogicalMeasure("E", "X"), LogicalMeasure("G", "Z")],
        ]
    )
    ex = prepare_compiled(c)
    raw = c.circuit.compile_sampler(seed=435).sample(64)
    result = analyze_knill(ex, raw)
    assert not result.failures.any()
    spectator = next(p for p in c.preparations if p.logical_id == "G")
    for bell in c.bell_measurements:
        assert spectator.module_id not in bell.preparation_dependencies
    a = next(p for p in c.preparations if p.logical_id == "A")
    boundary = ex.frame_plan.boundary_by_id[a.module_id]
    spectator_records = [m.index for m in c.measurements if m.key.block_id == "physical_G"]
    assert not boundary.record_map.incidence_matrix[:, spectator_records].nnz
    assert make_stage_requests(c).sector_input_ids == ex.requests.sector_input_ids


@pytest.fixture(scope="module")
def fault_experiment():
    return prepare_experiment(p=0.001, post_rounds=2)


@pytest.mark.parametrize(
    "category",
    [
        "data_X",
        "data_Z",
        "early_SE",
        "late_SE",
        "resource_CX",
        "Bell_CX",
        "readout_X",
        "readout_Z",
        "post_SE",
        "logical_X",
    ],
)
def test_known_physical_fault_signatures_and_honest_failure_labels(fault_experiment, category):
    from logical_to_stim_converter.decoding import PauliFault
    from logical_to_stim_converter.decoding.stages import module_end

    ex = fault_experiment
    c = ex.compiled
    atoms = ex.conditional_models[0].faults
    if category in ("resource_CX", "Bell_CX"):
        stage = "resource_entangling" if category == "resource_CX" else "teleportation"
        module = next(
            f.module_id
            for f in c.fragments
            if f.operation_type == "TransversalCNOT" and f.stage.endswith(stage)
        )
        fault = next(
            f
            for f in atoms
            if f.channel == "DEPOLARIZE2"
            and len(f.paulis) == 2
            and c.circuit[f.instruction_index - 1].tag == module
        )
    elif category in ("readout_X", "readout_Z"):
        r = (
            c.bell_measurements[0].x_readout
            if category == "readout_X"
            else c.bell_measurements[0].z_readout
        )
        record = c.measurement_index_by_key[r.records[0]]
        fault = next(f for f in atoms if f.measurement_record == record)
    elif category in ("data_X", "data_Z", "logical_X"):
        boundary = (
            ex.requests.boundaries[-1] if category == "logical_X" else ex.requests.boundaries[0]
        )
        index = module_end(c.circuit, boundary.module_id) - 1
        if category == "logical_X":
            r = c.readouts[-1]
            support = next(p for p in c.preparations if p.block_id == r.block_id).logical_x
        else:
            support = boundary.data_ids[:1]
        paulis = tuple((c.physical_qubit_map[boundary.block_id, q], category[-1]) for q in support)
        fault = PauliFault(index, "test physical Pauli", (index, 0), 1, paulis)
    else:
        boundary = (
            ex.requests.boundaries[-1] if category == "post_SE" else ex.requests.boundaries[0]
        )
        check = boundary.checks[0]
        key = check.measurements[0 if category == "early_SE" else -1]
        record = c.measurement_index_by_key[key]
        cursor = 0
        for index, inst in enumerate(c.circuit):
            if cursor <= record < cursor + inst.num_measurements:
                break
            cursor += inst.num_measurements
        fault = PauliFault(index, inst.name, (index, 0), 1, (), record)
    physical = noiseless_with_fault(c.circuit, fault)
    raw = physical.compile_sampler(seed=437).sample(32)
    events, truth = c.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    oracle = stim.FlipSimulator(
        batch_size=1, num_qubits=c.circuit.num_qubits, disable_stabilizer_randomization=True
    )
    oracle.do(physical)
    _, _, _, expected_events, expected_truth = oracle.to_numpy(
        transpose=True, output_detector_flips=True, output_observable_flips=True
    )
    assert np.array_equal(events, np.repeat(expected_events, len(raw), axis=0))
    assert np.array_equal(truth, np.repeat(expected_truth, len(raw), axis=0))
    result = analyze_knill(ex, raw)  # Decoder never receives the injected fault description.
    assert result.errors == np.count_nonzero(
        result.logical_values[:, 0] != c.observables[0].expected_value
    )
    assert 0 <= result.errors <= len(raw)
    if category == "logical_X":
        assert result.errors == len(raw)  # Undetectable logical fault, no forced-success assertion.


def test_stage_contracts_reject_invalid_batches_and_freeze_caller_arrays():
    from logical_to_stim_converter.decoding import StageInputs, StageResult

    bits = np.zeros((2, 3), dtype=np.uint8)
    correction = CorrectionBatch("source", "module", bits)
    inputs = StageInputs("source", bits, bits, bits)
    result = StageResult(correction, bits, bits)
    bits[:] = 1
    assert not correction.bits.any() and not inputs.records.any() and not result.net_sector.any()
    with pytest.raises(DecoderViewError):
        StageInputs("source", np.zeros((2, 1)), np.zeros((3, 1)))
    with pytest.raises(DecoderViewError):
        CorrectionBatch("", "module", bits)
    with pytest.raises(DecoderViewError):
        StageInputs("source", np.array([[2]]), bits)
    with pytest.raises(DecoderViewError):
        StageResult(correction, net_sector=np.zeros((3, 1)))
