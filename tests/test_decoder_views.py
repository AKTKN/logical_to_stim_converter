"""One experiment supplies exact offline inputs/models for many decoder regions."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    DEMOptions,
    DetectorSelector,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    TransversalH,
    observable_local_views,
)
from logical_to_stim_converter.decoding import (
    DecoderViewError,
    DEMConstructionError,
    SourceMismatchError,
    UndefinedObservableError,
    UnsupportedProjectionError,
)
from tests.helpers.decoder_view_physics import (
    assert_marginal_equivalent,
    hand_artifact,
    mechanisms,
    physical_instructions,
)
from tests.helpers.knill_physics import make_compiler
from tests.test_bell_roundtrip import bell_blocks, bell_program


@pytest.fixture(scope="module", params=[("memory", 3), ("memory", 5), ("knill", 3), ("knill", 5)])
def source(request):
    kind, d = request.param
    if kind == "memory":
        compiler = make_compiler(d, "AB")
        program = [
            [LogicalInit("A", "X", 1), LogicalInit("B", "Z", 1)],
            SyndromeExtraction(("A", "B"), d),
            [LogicalMeasure("A", "X"), LogicalMeasure("B", "Z")],
        ]
    else:
        compiler = make_compiler(d)
        program = [
            LogicalInit("D", "X", 1),
            KnillEC("D", "A", "B"),
            SyndromeExtraction("D", 2),
            TransversalH("D"),
            LogicalMeasure("D", "Z"),
        ]
    return compiler.compile(program, noise_model=NoiseModel.uniform_depolarizing(0.003))


def test_identity_view_is_global_physical_model(source):
    before = source.circuit.copy()
    view = source.make_decoder_view()
    assert (
        view.detector_error_model.flattened() == source.circuit.detector_error_model().flattened()
    )
    assert view.detector_map.global_ids == tuple(range(len(source.detectors)))
    assert view.observable_map.global_ids == tuple(range(len(source.observables)))
    assert view.measurement_map.global_ids == tuple(range(len(source.measurements)))
    assert physical_instructions(view.circuit) == physical_instructions(source.circuit)
    assert source.circuit == before
    view.assert_source(source)
    # Neither caller mutation nor assignment can alter the immutable snapshot.
    copy = view.circuit
    copy.append("X", [0])
    dem_copy = view.detector_error_model
    dem_copy.append("error", 0.1, [stim.target_relative_detector_id(0)])
    assert view.circuit != copy and view.detector_error_model != dem_copy
    with pytest.raises(FrozenInstanceError):
        view.source_fingerprint = "bad"
    with pytest.raises(ValueError):
        view.reference_sample[0] ^= True


def test_permutation_sparse_records_and_bidirectional_maps(source):
    ids = (len(source.detectors) - 1, 0, 5, 2)
    obs_ids = tuple(reversed(range(len(source.observables))))
    record_ids = (len(source.measurements) - 1, 3, 0)
    view = source.make_decoder_view(
        detector_selector=ids,
        observable_selector=obs_ids,
        measurement_selector=[source.measurements[i].key for i in record_ids],
    )
    assert view.detector_map.global_ids == ids
    assert view.measurement_map.global_ids == record_ids
    for mapping in (view.detector_map, view.observable_map, view.measurement_map):
        assert (
            tuple(mapping.global_to_local[g] for g in mapping.local_to_global) == mapping.local_ids
        )
        with pytest.raises(TypeError):
            mapping.global_to_local[0] = 500
    assert view.circuit.get_detector_coordinates() == {
        i: list(source.detectors[g].coordinates) for i, g in enumerate(ids)
    }
    assert_marginal_equivalent(source.circuit.detector_error_model(), view)


def test_many_views_share_one_raw_batch_and_reference_alignment(source):
    raw = source.circuit.compile_sampler(seed=71).sample(128)
    before = raw.copy()
    events, flips = source.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    block = source.preparations[0].block_id
    stage = source.preparations[-1].stage_id
    selectors = [
        None,
        DetectorSelector(block_ids=(block,)),
        DetectorSelector(block_ids=(block,), block_membership="strict"),
        DetectorSelector(basis="X"),
        DetectorSelector(basis="Z"),
        DetectorSelector(stage_ids=(stage,), stage_membership="strict"),
        DetectorSelector(stage_ids=(stage,)) | DetectorSelector(block_ids=(block,)),
        lambda d: d.coordinates[2] >= 1,
    ]
    for selector in selectors:
        view = source.make_decoder_view(detector_selector=selector)
        ids = view.detector_map.global_ids
        assert np.array_equal(view.events_from_raw(raw), events[:, ids])
        assert np.array_equal(view.project_detection_events(events), events[:, ids])
        assert np.array_equal(view.project_observable_flips(flips), flips)
        assert np.array_equal(view.observable_flips_from_raw(raw), flips)
        assert np.array_equal(view.project_raw_measurements(raw), raw)
        for i, d in enumerate(view.detectors):
            parity = np.bitwise_xor.reduce(raw[:, d.measurement_indices], axis=1)
            parity ^= np.bitwise_xor.reduce(view.reference_sample[list(d.measurement_indices)])
            assert np.array_equal(parity, events[:, ids[i]])
        assert physical_instructions(view.circuit) == physical_instructions(source.circuit)
    assert np.array_equal(raw, before)


def test_record_frame_event_update_matches_stim_reconversion(source):
    raw = source.circuit.compile_sampler(seed=72).sample(48)
    converter = source.circuit.compile_m2d_converter()
    events, _ = converter.convert(measurements=raw, separate_observables=True)
    masks = np.random.default_rng(73).integers(0, 2, raw.shape, dtype=np.uint8)
    corrected = raw ^ masks.astype(bool)
    expected, expected_obs = converter.convert(measurements=corrected, separate_observables=True)
    view = source.make_decoder_view(detector_selector=tuple(reversed(range(0, len(events[0]), 3))))
    assert np.array_equal(
        view.update_detection_events(events, masks), expected[:, view.detector_map.global_ids]
    )
    batch = view.inputs_from_raw(
        raw, record_flips=masks, source_fingerprint=view.source_fingerprint
    )
    assert np.array_equal(batch.detection_events, view.events_from_raw(corrected))
    assert np.array_equal(batch.observable_flips, expected_obs)
    assert np.array_equal(batch.records, corrected)
    assert batch.source_fingerprint == view.source_fingerprint
    assert not batch.records.flags.writeable


def test_observable_local_regions_and_global_observable_ids(source):
    views = observable_local_views(source)
    raw = source.circuit.compile_sampler(seed=74).sample(64)
    events, obs = source.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    for i, view in enumerate(views):
        assert view.observable_map.global_ids == (i,)
        assert view.observable_map.global_to_local[i] == 0
        assert view.detector_error_model.num_observables == 1
        assert np.array_equal(view.observable_flips_from_raw(raw), obs[:, i : i + 1])
        assert np.array_equal(view.events_from_raw(raw), events[:, view.detector_map.global_ids])
    if len(source.observables) == 2:
        assert not set(views[0].detector_map.global_ids) & set(views[1].detector_map.global_ids)
    override = observable_local_views(
        source, observable_selector=(len(views) - 1,), region_selector=lambda o: (1, 0)
    )
    assert override[0].detector_map.global_ids == (1, 0)


@pytest.fixture(scope="module")
def interacting():
    return CircuitCompiler(bell_blocks(3)).compile(
        bell_program(2), noise_model=NoiseModel.uniform_depolarizing(0.004)
    )


def test_cross_block_policy_strict_joint_and_correlated_models(interacting):
    source = interacting
    anchor = source.make_decoder_view(detector_selector=DetectorSelector(block_ids=("A",)))
    strict = source.make_decoder_view(
        detector_selector=DetectorSelector(block_ids=("A",), block_membership="strict")
    )
    joint = source.make_decoder_view(
        detector_selector=DetectorSelector(block_ids=("A", "B"), block_membership="strict"),
        cross_region_policy="joint",
    )
    omitted = source.make_decoder_view(cross_region_policy="omit")
    assert set(strict.detector_map.global_ids) < set(anchor.detector_map.global_ids)
    assert joint.audit.region_block_ids == ("A", "B")
    assert joint.audit.crossing_detector_ids
    assert omitted.audit.omitted_detector_ids == joint.audit.crossing_detector_ids
    assert all(len(d.supporting_block_ids) == 1 for d in omitted.detectors)
    # Default observable regions include real interactions, even after the inverse CX.
    assert all(v.audit.region_block_ids == ("A", "B") for v in observable_local_views(source))
    global_dem = source.circuit.detector_error_model()
    assert any(len(s) > 2 for _, s in mechanisms(global_dem))
    for view in (anchor, strict, joint, omitted):
        assert_marginal_equivalent(global_dem, view)
    # Validate emitted check basis against actual MX/M anchor readout, including H.
    for d in source.detectors:
        anchor_record = next(
            (
                m
                for m in source.measurements
                if m.module_id == d.anchor_module_id and m.key.local_id == d.check_id
            ),
            next(m for m in source.measurements if m.module_id == d.anchor_module_id),
        )
        assert d.basis == anchor_record.basis


def test_exact_fault_is_retained_when_another_detector_is_removed():
    source = hand_artifact(
        stim.Circuit("""
        R 0 1
        X_ERROR(0.1) 0
        TICK
        X_ERROR(0.2) 0
        CX 0 1
        M 0 1
        DETECTOR(0, 0, 0) rec[-2]
        DETECTOR(1, 0, 0) rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-1]
    """)
    )
    view = source.make_decoder_view(detector_selector=(1,))
    terms = mechanisms(view.detector_error_model)
    assert len(terms) == 1 and terms[0][1] == (0, 1)
    assert terms[0][0] == pytest.approx(0.1 + 0.2 - 2 * 0.1 * 0.2)
    assert_marginal_equivalent(source.circuit.detector_error_model(), view)
    # Enumerate the physical X fault, independently of any DEM reader.
    for fault in (False, True):
        physical = stim.Circuit("R 0 1")
        if fault:
            physical.append("X", [0])
        physical += stim.Circuit("CX 0 1\nM 0 1")
        raw = physical.compile_sampler(seed=75).sample(8)
        assert (view.events_from_raw(raw) == fault).all()
        assert (view.observable_flips_from_raw(raw) == fault).all()


def test_hyperedge_and_correlated_separator_semantics():
    hyper = hand_artifact(
        stim.Circuit("""
        R 0 1 2
        CORRELATED_ERROR(0.125) X0 X1 X2
        M 0 1 2
        DETECTOR(0, 0, 0) rec[-3]
        DETECTOR(1, 0, 0) rec[-2]
        DETECTOR(2, 0, 0) rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-3]
        OBSERVABLE_INCLUDE(1) rec[-1]
    """)
    )
    full = hyper.make_decoder_view()
    assert mechanisms(full.detector_error_model) == [(0.125, (0, 1, 2, 3, 4))]
    view = hyper.make_decoder_view(detector_selector=(2, 0), observable_selector=(1,))
    assert mechanisms(view.detector_error_model) == [(0.125, (0, 1, 2))]
    assert_marginal_equivalent(full.detector_error_model, view)
    with pytest.raises(DEMConstructionError, match="decompose"):
        hyper.make_decoder_view(dem_options=DEMOptions(decompose_errors=True))
    bell = hand_artifact(
        stim.Circuit("""
        R 0 1
        H 0
        CX 0 1
        DEPOLARIZE1(0.03) 0
        CX 0 1
        H 0
        M 0 1
        DETECTOR(0, 0, 0) rec[-2]
        DETECTOR(1, 0, 0) rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-2]
        OBSERVABLE_INCLUDE(1) rec[-1]
    """)
    )
    decomposed = bell.circuit.detector_error_model(decompose_errors=True)
    assert " ^ " in str(decomposed)
    for ids in ((0, 1), (1,), (0,)):
        local = bell.make_decoder_view(
            detector_selector=ids,
            observable_selector=(1, 0),
            dem_options=DEMOptions(decompose_errors=True),
        )
        assert_marginal_equivalent(decomposed, local)


def test_repeat_shifts_nonzero_reference_sign_and_statistics():
    source = hand_artifact(
        stim.Circuit("""
        REPEAT 3 {
            R 0
            X 0
            X_ERROR(0.17) 0
            M 0
            DETECTOR(1, 2, 0) rec[-1]
            SHIFT_COORDS(0, 0, 1)
            TICK
        }
        OBSERVABLE_INCLUDE(0) rec[-1]
    """)
    )
    view = source.make_decoder_view(
        detector_selector=(2, 0), dem_options=DEMOptions(flatten_loops=True)
    )
    assert physical_instructions(view.circuit) == physical_instructions(source.circuit)
    raw = source.circuit.compile_sampler(seed=80).sample(25000)
    events, obs = source.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    assert np.array_equal(view.events_from_raw(raw), events[:, (2, 0)])
    assert np.array_equal(view.observable_flips_from_raw(raw), obs)
    assert np.array_equal(
        view.events_from_raw(raw, reference_sample=source.circuit.reference_sample()),
        view.events_from_raw(raw),
    )
    with pytest.raises(DecoderViewError, match="Reference sample"):
        view.events_from_raw(raw, reference_sample=np.zeros(raw.shape[1], dtype=bool))
    # Independent streams: compare distributions with an uncertainty-aware bound.
    local_events = view.circuit.compile_detector_sampler(seed=81).sample(25000)
    global_codes = events[:, (2, 0)] @ np.array([1, 2])
    local_codes = local_events @ np.array([1, 2])
    p = np.bincount(global_codes, minlength=4) / len(raw)
    q = np.bincount(local_codes, minlength=4) / len(raw)
    sigma = np.sqrt((p * (1 - p) + q * (1 - q)) / len(raw))
    assert np.all(np.abs(p - q) < 7 * sigma + 8 / len(raw))
    assert_marginal_equivalent(source.circuit.detector_error_model(), view)


@pytest.mark.parametrize(
    "bad",
    [
        "detector",
        "duplicate",
        "observable",
        "random",
        "records",
        "metadata",
        "basis",
        "support",
        "fingerprint",
        "width",
        "nonbinary",
        "model",
        "options",
        "undefined",
    ],
)
def test_invalid_view_requests_fail_clearly(source, bad):
    options = {}
    if bad == "detector":
        options["detector_selector"] = (source.circuit.num_detectors,)
    elif bad == "duplicate":
        options["detector_selector"] = (0, 0)
    elif bad == "observable":
        options["observable_selector"] = (100,)
    elif bad == "random":
        options["observable_selector"] = ("random_bell_module",)
    elif bad == "records":
        options["measurement_selector"] = (source.circuit.num_measurements,)
    elif bad == "metadata":
        source = replace(source, measurements=source.measurements[:-1])
    elif bad in ("basis", "support"):
        d = replace(
            source.detectors[0], **({"basis": ""} if bad == "basis" else {"physical_support": ()})
        )
        source = replace(source, detectors=(d, *source.detectors[1:]))
    elif bad == "fingerprint":
        options["expected_source_fingerprint"] = "another-source"
    elif bad in ("width", "nonbinary"):
        view = source.make_decoder_view()
        raw = np.zeros((2, len(source.measurements) - (bad == "width")), dtype=np.uint8)
        if bad == "nonbinary":
            raw[0, 0] = 2
        with pytest.raises(DecoderViewError):
            view.events_from_raw(raw)
        return
    elif bad == "model":
        options["model_source"] = "global_dem"
    elif bad == "options":
        options["dem_options"] = {"approximate_disjoint_errors": True}
    else:
        source = replace(
            source,
            observables=(
                replace(source.observables[0], expected_value=None),
                *source.observables[1:],
            ),
        )
    with pytest.raises(DecoderViewError):
        source.make_decoder_view(**options)


def test_fingerprint_catches_noise_and_metadata_changes_and_random_readout_requests(source):
    view = source.make_decoder_view()
    changed = source.circuit.copy()
    changed.append("X_ERROR", [0], 0.1)
    with pytest.raises(SourceMismatchError):
        view.assert_source(replace(source, noisy_circuit=changed))
    with pytest.raises(SourceMismatchError):
        view.project_detection_events(
            np.zeros((1, len(source.detectors)), bool), source_fingerprint="bad"
        )
    d = replace(source.detectors[0], stage_id="wrong")
    with pytest.raises(SourceMismatchError):
        view.assert_source(replace(source, detectors=(d, *source.detectors[1:])))
    if source.bell_measurements:
        (bell,) = source.bell_measurements
        for readout in (bell.x_readout, bell.z_readout):
            with pytest.raises(UndefinedObservableError):
                source.make_decoder_view(observable_selector=(readout.module_id,))


def test_unsupported_disjoint_noise_fails_without_silent_approximation():
    source = hand_artifact(
        stim.Circuit("""
        R 0 1
        H 0
        CX 0 1
        PAULI_CHANNEL_1(0.1, 0.2, 0.3) 0
        CX 0 1
        H 0
        M 0 1
        DETECTOR(0, 0, 0) rec[-2]
        DETECTOR(1, 0, 0) rec[-1]
    """)
    )
    with pytest.raises(DEMConstructionError, match="approximate_disjoint_errors"):
        source.make_decoder_view()
    with pytest.raises(UnsupportedProjectionError):
        source.make_decoder_view(model_source="line_filtered_dem")


@pytest.mark.parametrize("d", [3, 5])
def test_open_knill_views_have_no_added_measurements_or_observables(d):
    source = make_compiler(d).compile(
        [LogicalInit("D", "X", 1), KnillEC("D", "A", "B")],
        allow_open_outputs=True,
        noise_model=NoiseModel.uniform_depolarizing(0.002),
    )
    view = source.make_decoder_view()
    assert view.circuit.num_measurements == source.circuit.num_measurements
    assert not view.observable_map.global_ids and view.circuit.num_observables == 0
    assert not any(i.name == "MPP" for i in view.circuit)
    assert (
        view.detector_error_model.flattened() == source.circuit.detector_error_model().flattened()
    )
    raw = source.circuit.compile_sampler(seed=91).sample(128)
    events = source.circuit.compile_m2d_converter().convert(
        measurements=raw, append_observables=False
    )
    assert np.array_equal(view.events_from_raw(raw), events)
    stage = source.preparations[-1].stage_id
    stage_view = source.make_decoder_view(
        detector_selector=DetectorSelector(stage_ids=(stage,), stage_membership="strict", basis="X")
    )
    assert stage_view.detectors
    assert all(d.source_stage_ids == (stage,) and d.basis == "X" for d in stage_view.detectors)


def test_ideal_source_fallback_and_empty_views(source):
    ideal = replace(source, noisy_circuit=None)
    view = ideal.make_decoder_view(
        detector_selector=(), observable_selector=(), measurement_selector=()
    )
    assert view.source_circuit == ideal.ideal_circuit
    assert view.detector_error_model.num_detectors == view.detector_error_model.num_observables == 0
    assert physical_instructions(view.circuit) == physical_instructions(ideal.circuit)
    raw = ideal.circuit.compile_sampler(seed=92).sample(4)
    inputs = view.inputs_from_raw(raw)
    assert (
        inputs.detection_events.shape
        == inputs.observable_flips.shape
        == inputs.records.shape
        == (4, 0)
    )


@pytest.mark.parametrize("field", ["basis", "physical_support"])
def test_compiler_rejects_corrupted_physical_check_metadata(interacting, field):
    d = interacting.detectors[0]
    change = (
        {"basis": "Z" if d.basis == "X" else "X"} if field == "basis" else {"physical_support": ()}
    )
    bad = replace(interacting, detectors=(replace(d, **change), *interacting.detectors[1:]))
    with pytest.raises(ValueError, match="basis or data support"):
        bad.validate_metadata()


def test_cross_stage_boundary_policy_is_explicit_and_auditable(source):
    view = source.make_decoder_view(cross_region_policy="omit")
    expected = tuple(
        d.index
        for d in source.detectors
        if len(d.supporting_block_ids) > 1 or len(d.source_stage_ids) > 1
    )
    assert view.audit.omitted_detector_ids == expected
    assert view.audit.requested_detector_ids == tuple(range(len(source.detectors)))
    assert view.audit.cross_region_policy == "omit"
    assert not set(expected) & set(view.detector_map.global_ids)
    assert physical_instructions(view.circuit) == physical_instructions(source.circuit)


def test_view_preserves_exact_probabilities_and_fingerprints(monkeypatch):
    # Stim 1.15 circuit text rounds to six significant digits; the Windows DEM
    # printer uses only 16. Neither is a lossless snapshot of arbitrary doubles.
    probability = 0.12345678901234566
    assert float(format(probability, ".16g")) != probability
    circuit = stim.Circuit("R 0")
    circuit.append("X_ERROR", [0], probability, tag="fault]tag")
    circuit.append("M", [0])
    circuit.append("DETECTOR", [stim.target_rec(-1)], [0.12345678901234566])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
    source = hand_artifact(circuit)
    expected = circuit.detector_error_model()

    def lossy_dem_text(model):
        # This is the single-error model above, emulating the Windows precision.
        return f"error({model[0].args_copy()[0]:.16g}) D0 L0"

    monkeypatch.setattr(stim.DetectorErrorModel, "__str__", lossy_dem_text)
    view = source.make_decoder_view()
    assert view.source_circuit == source.circuit
    assert physical_instructions(view.circuit) == physical_instructions(source.circuit)
    assert view.detector_error_model == expected
    assert view.detector_error_model[0].args_copy() == [probability]
    assert view.detector_error_model[0].tag == "fault]tag"
    assert view.schema_version == "decoder-view-v3"
    other = circuit[:1]
    other.append("X_ERROR", [0], probability + 1e-10, tag="fault]tag")
    other += circuit[2:]
    assert str(other) == str(circuit)  # Text would incorrectly identify these sources.
    with pytest.raises(SourceMismatchError):
        view.assert_source(hand_artifact(other))


def test_exact_snapshots_keep_repeat_shift_separator_and_tags():
    from logical_to_stim_converter.decoding.views import (
        _freeze_circuit,
        _freeze_dem,
        _thaw_circuit,
        _thaw_dem,
    )

    circuit = stim.Circuit("R 0")
    body = stim.Circuit("X_ERROR[fault](0.12345678901234566) 0\nM 0\nR 0")
    circuit.append(stim.CircuitRepeatBlock(3, body, tag="repeated]fault"))
    assert _thaw_circuit(_freeze_circuit(circuit)) == circuit
    model = stim.DetectorErrorModel("""
        repeat 3 {
            error[fault](0.12345678901234566) D0 D1 ^ D2 L0
            detector[coordinate](0.12345678901234566, 2) D0
            shift_detectors(0, 0, 1) 3
        }
        logical_observable[output] L0
    """)
    snapshot = _freeze_dem(model)
    copy = _thaw_dem(snapshot)
    assert copy == model
    assert copy[0].body_copy()[0].args_copy() == [0.12345678901234566]
    copy.append("error", 0.5, [stim.target_relative_detector_id(0)])
    assert _thaw_dem(snapshot) == model  # Returned models cannot mutate the snapshot.
