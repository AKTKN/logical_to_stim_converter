"""Three fixed working patches: occupancy, independent tableaux and physical faults."""

from collections import Counter

import numpy as np
import pytest
import stim

from examples.knill_memory_offline_decoding import build_knill
from examples.knill_memory_three_patch_reuse import (
    THREE_PATCH_SCHEDULE,
    build_explicit_three_patch_knill,
    explicit_three_patch_program,
)
from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    BlockUseId,
    CircuitCompiler,
    CodeSpec,
    DetectorSelector,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    NoiseModel,
    NoiseParameters,
)
from logical_to_stim_converter.decoding import make_conditional_readout_model, make_stage_requests
from tests.helpers.decoder_view_physics import assert_marginal_equivalent, physical_instructions
from tests.helpers.knill_physics import (
    corrected_expectation,
    explicit_reference,
    make_compiler,
    pauli,
    simulate,
)
from tests.helpers.preparation_matching import preparation_corrections
from tests.test_epoch_views_noise import assert_exact_reuse_noise


@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("d,t", [(3, t) for t in range(1, 6)] + [(5, t) for t in range(1, 4)])
def test_explicit_occupancy_schedule_fixed_width_and_unique_history(d, t, basis):
    """Reconstruct expected epochs from the declared triples, never final aliases."""
    c = build_explicit_three_patch_knill(distance=d, basis=basis, teleportations=t)
    assert {b for b, _ in c.physical_qubit_map} == {"P0", "P1", "P2"}
    assert c.circuit.num_qubits == 3 * (2 * d * d - 1)
    assert len(c.block_uses) == 1 + 2 * t
    assert len(c.binding_history) == 2 * (t - 1)
    assert len(set(m.key for m in c.measurements)) == len(c.measurements)
    assert [m.index for m in c.measurements] == list(range(len(c.measurements)))
    epochs, current = Counter({"P0": 0, "P1": -1, "P2": -1}), BlockUseId("P0", 0)
    by_use = {u.use_id: u for u in c.block_uses}
    for cycle, (bell, relocation) in enumerate(
        zip(c.bell_measurements, c.relocation_history, strict=True)
    ):
        input_patch, a, b = THREE_PATCH_SCHEDULE[cycle % 3]
        epochs[a] += 1
        epochs[b] += 1
        assert bell.data_use_id == current and current.block_id == input_patch
        assert bell.first_resource_use_id == BlockUseId(a, epochs[a])
        assert bell.output_use_id == BlockUseId(b, epochs[b])
        assert relocation.logical_id == "D" and relocation.source_use_id == current
        assert relocation.output_use_id == bell.output_use_id
        assert set(relocation.retired_logical_ids) == {f"A{cycle}", f"B{cycle}"}
        for use in (bell.data_use_id, bell.first_resource_use_id):
            assert by_use[use].terminal_module_id is not None
        owners = by_use[bell.output_use_id].logical_owner_history
        assert [o.logical_id for o in owners] == [f"B{cycle}", "D"]
        current = bell.output_use_id
    assert c.logical_to_block == {"D": current.block_id}
    if t == 3:
        assert current == BlockUseId("P0", 2)
    for p in c.preparations:
        assert by_use[p.block_use_id].reset_module_id == p.module_id
        assert all(k.block_use_id == p.block_use_id for h in p.checks for k in h.measurements)
    for layer in c.time_layers:
        assert len(layer.active_use_ids) == len({u.block_id for u in layer.active_use_ids})
    c.validate_metadata()
    c.ideal_circuit.detector_error_model()


def test_manually_written_directives_and_zero_duration_bindings():
    """A standard compiler accepts the same schedule without the example authoring helper."""
    blocks = [
        LogicalBlock.placed(f"P{i}", CodeSpec.rotated_surface(3), patch_index=i) for i in range(3)
    ]
    compiler = CircuitCompiler(blocks, logical_to_block={"D": "P0", "A0": "P1", "B0": "P2"})
    manual = [
        LogicalInit("D", "Z", 3),
        KnillEC("D", "A0", "B0", rounds=3),
        BindPatch("A1", "P0"),
        BindPatch("B1", "P1"),
        KnillEC("D", "A1", "B1", rounds=3),
        BindPatch("A2", "P2"),
        BindPatch("B2", "P0"),
        KnillEC("D", "A2", "B2", rounds=3),
    ]
    model = NoiseModel.uniform_depolarizing(0.001)
    c = compiler.compile(manual, noise_model=model, allow_open_outputs=True)
    authored = build_explicit_three_patch_knill(
        post_rounds=0, noise_model=model, allow_open_outputs=True
    )
    assert c.circuit == authored.circuit and c.time_layers == authored.time_layers
    moved = manual[:]
    moved[2], moved[3] = moved[3], moved[2]
    assert compiler.compile(moved, noise_model=model, allow_open_outputs=True).circuit == c.circuit
    assert not any("BindPatch" in f.operation_type for f in c.fragments)
    for event in c.binding_history:
        next_use = next(
            u
            for u in c.block_uses
            if u.use_id.block_id == event.block_id
            and u.use_id.epoch == event.previous_use.epoch + 1
        )
        assert next_use.time_layer_start >= next(
            u.time_layer_stop for u in c.block_uses if u.use_id == event.previous_use
        )
        assert any(i.name in ("R", "RX") and i.tag == next_use.reset_module_id for i in c.circuit)


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
def test_three_cycles_signed_physical_tableaux_random_gauges_and_bell_branches(d, basis, bit):
    """Independent tableaux plus actual correction execution certify each sampled branch."""
    c = build_explicit_three_patch_knill(distance=d, basis=basis, bit=bit, allow_open_outputs=True)
    raw, simulators = simulate(c, range(32))
    corrections = preparation_corrections(c, raw)
    evaluated = c.evaluate_frames(raw, corrections)
    assert any(
        raw[:, [c.measurement_index_by_key[k] for k in p.gauge_measurements]].any()
        for p in c.preparations
    )
    for bell in c.bell_measurements:
        mx = bell.x_readout.logical_parity.evaluate(
            evaluated.corrected_measurements, c.measurement_index_by_key
        )
        mz = bell.z_readout.logical_parity.evaluate(
            evaluated.corrected_measurements, c.measurement_index_by_key
        )
        assert len(set(zip(mx, mz, strict=True))) == 4
    plan = c.make_frame_plan()
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    from logical_to_stim_converter.decoding import CorrectionBatch

    for prep in c.preparations:
        boundary = plan.boundary_by_id[prep.module_id]
        bits = np.array(
            [
                [q in f.x_support for q in prep.data_ids]
                + [q in f.z_support for q in prep.data_ids]
                for f in corrections[prep.module_id]
            ],
            dtype=bool,
        )
        state.apply(
            CorrectionBatch(
                plan.source_fingerprint, prep.module_id, bits, prep.block_use_id, boundary.input_ids
            )
        )
    np.testing.assert_array_equal(state.interpreted_measurements, evaluated.corrected_measurements)
    for shot, sim in enumerate(simulators):
        frames = [evaluated.final_frames["D"][shot]]
        assert corrected_expectation(sim, c, pauli(c, "D", basis), frames) == (-1) ** bit
        if shot < 2:
            physical = explicit_reference(
                c,
                state.interpreted_measurements[shot],
                {k: v[shot : shot + 1] for k, v in corrections.items()},
            )
            assert physical.peek_observable_expectation(pauli(c, "D", basis)) == (-1) ** bit


@pytest.mark.parametrize("d", [3, 5])
def test_encoded_reference_is_untouched_through_three_teleports_reused_and_fresh(d):
    """Three working patches plus one encoded reference preserve XX/ZZ entanglement."""
    code = CodeSpec.rotated_surface(d)
    compiler = CircuitCompiler(
        [
            LogicalBlock.placed(b, code, patch_index=i)
            for i, b in enumerate(("R", "P0", "P1", "P2"))
        ],
        logical_to_block={"R": "R", "D": "P0", "A0": "P1", "B0": "P2"},
    )
    tail = explicit_three_patch_program(distance=d, post_rounds=0, allow_open_outputs=True)[1:]
    reused = compiler.compile([BellStatePrep("R", "D", rounds=d)] + tail, allow_open_outputs=True)
    fresh_names = ["R", "D"] + [q for t in range(3) for q in (f"A{t}", f"B{t}")]
    fresh = make_compiler(d, fresh_names).compile(
        [BellStatePrep("R", "D", rounds=d)]
        + [op for t in range(3) for op in (KnillEC("D", f"A{t}", f"B{t}", rounds=d),)],
        allow_open_outputs=True,
    )
    for c in (reused, fresh):
        raw, sims = simulate(c, range(12))
        corrections = preparation_corrections(c, raw)
        result = c.evaluate_frames(raw, corrections)
        reference_preps = [p for p in c.preparations if p.logical_id == "R"]
        reference_ids = {reference_preps[0].block_id}
        assert len(reference_preps) == 1
        for f in c.fragments:
            if f.module_id not in {p.module_id for p in c.preparations[:2]} and (
                f.operation_type != "TransversalCNOT" or f.module_id != c.fragments[2].module_id
            ):
                assert not reference_ids.intersection(f.block_ids)
        for shot, sim in enumerate(sims):
            frames = [result.final_frames[q][shot] for q in ("R", "D")]
            for basis in "XZ":
                joint = pauli(c, "R", basis) * pauli(c, "D", basis)
                assert corrected_expectation(sim, c, joint, frames) == 1
                assert sim.peek_observable_expectation(pauli(c, "D", basis)) == 0
            if shot == 0:
                actual = explicit_reference(
                    c,
                    result.corrected_measurements[shot],
                    {k: v[:1] for k, v in corrections.items()},
                )
                for basis in "XZ":
                    assert (
                        actual.peek_observable_expectation(
                            pauli(c, "R", basis) * pauli(c, "D", basis)
                        )
                        == 1
                    )


@pytest.fixture(scope="module", params=[3, 5])
def noisy_three_cycles(request):
    """Full d-round preparations and three teleports with distinct channel probabilities."""
    model = NoiseModel(NoiseParameters(0.001, 0.002, 0.003, 0.004, 0.005))
    return build_explicit_three_patch_knill(distance=request.param, noise_model=model), model


def test_all_p0_epochs_global_parities_local_marginals_noise_and_bell_atoms(noisy_three_cycles):
    """Check exact model marginals and independently propagated physical noise atoms."""
    c, model = noisy_three_cycles
    assert_exact_reuse_noise(c, model)
    raw = c.circuit.compile_sampler(seed=903).sample(64)
    events, truth = c.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    ideal = c.ideal_circuit.compile_sampler(seed=904).sample(32)
    assert (
        not c.ideal_circuit.compile_m2d_converter()
        .convert(measurements=ideal, separate_observables=True)[0]
        .any()
    )
    for detector in c.detectors:
        assert detector.coordinates == tuple(c.circuit.get_detector_coordinates()[detector.index])
        assert not np.bitwise_xor.reduce(ideal[:, detector.measurement_indices], axis=1).any()
        assert detector.source_use_ids == tuple(
            sorted({c.measurements[i].key.block_use_id for i in detector.measurement_indices})
        )
    union = set()
    for epoch in range(3):
        use = BlockUseId("P0", epoch)
        view = c.make_decoder_view(
            detector_selector=DetectorSelector(use_ids=(use,)),
            measurement_selector=lambda m: m.key.block_use_id == use,
        )
        assert all(m.key.block_use_id == use for m in view.measurements)
        assert physical_instructions(view.circuit) == physical_instructions(c.circuit)
        assert_marginal_equivalent(c.circuit.detector_error_model(), view)
        np.testing.assert_array_equal(
            view.events_from_raw(raw), events[:, view.detector_map.global_ids]
        )
        np.testing.assert_array_equal(view.observable_flips_from_raw(raw), truth)
        flips = np.zeros_like(raw)
        flips[:, view.measurement_map.global_ids[0]] = True
        changed_events, _ = c.circuit.compile_m2d_converter().convert(
            measurements=raw ^ flips, separate_observables=True
        )
        np.testing.assert_array_equal(
            view.events_from_raw(raw ^ flips), changed_events[:, view.detector_map.global_ids]
        )
        np.testing.assert_array_equal(
            view.update_detection_events(events, flips), view.events_from_raw(raw ^ flips)
        )
        union.update(view.detector_map.global_ids)
    wide = c.make_decoder_view(detector_selector=DetectorSelector(block_ids=("P0",)))
    assert set(wide.detector_map.global_ids) == union
    for bell in c.bell_measurements:
        assert_physical_conditional_atoms(c, make_conditional_readout_model(c, bell))


def assert_physical_conditional_atoms(c, model):
    """Independently inject every exclusive channel atom, retaining actual probabilities."""
    oracle = stim.FlipSimulator(
        batch_size=len(model.faults),
        num_qubits=c.circuit.num_qubits,
        disable_stabilizer_randomization=True,
    )
    grouped, at = {}, {}
    for row, fault in enumerate(model.faults):
        grouped.setdefault(fault.exclusive_group, []).append(fault)
        at.setdefault(fault.instruction_index, []).append((row, fault))
    for group in grouped.values():
        inst = c.circuit[group[0].instruction_index]
        assert sum(f.probability for f in group) == pytest.approx(inst.gate_args_copy()[0])
        if group[0].channel == "DEPOLARIZE2":
            assert len(group) == 15
            assert {tuple(a for _, a in f.paulis) for f in group}
    cursor = 0
    for i, inst in enumerate(c.circuit[: model.end_instruction]):
        entries = at.get(i, ())
        for axis in "XYZ":
            mask = np.zeros((c.circuit.num_qubits, len(model.faults)), dtype=bool)
            for row, fault in entries:
                if fault.measurement_record is not None:
                    q = inst.targets_copy()[fault.measurement_record - cursor].value
                    if axis == ("Z" if inst.name == "MX" else "X"):
                        mask[q, row] = True
            if mask.any():
                oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
        one = stim.Circuit()
        one.append(inst)
        oracle.do(one.without_noise())
        for axis in "XYZ":
            mask = np.zeros((c.circuit.num_qubits, len(model.faults)), dtype=bool)
            for row, fault in entries:
                for q, a in fault.paulis:
                    if a == axis:
                        mask[q, row] = True
            if mask.any():
                oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
        cursor += inst.num_measurements
    xs, zs, flips, _, _ = oracle.to_numpy(
        transpose=True, output_xs=True, output_zs=True, output_measure_flips=True
    )
    ids = [c.physical_qubit_map[model.output_use_id.block_id, q] for q in model.output_data_ids]
    np.testing.assert_array_equal(
        model.raw_flip_map.incidence_matrix.toarray(), flips[:, model.readout_record_ids]
    )
    np.testing.assert_array_equal(model.output_x_map.incidence_matrix.toarray(), xs[:, ids])
    np.testing.assert_array_equal(model.output_z_map.incidence_matrix.toarray(), zs[:, ids])


def unfolded_physical_sites(compiled):
    """Independently label ideal/noise atoms by reset owner/local site and TICK.

    Read actual reset instructions to advance occupancy. Sorting atoms within a
    layer ignores harmless instruction batching/qubit numbering while preserving
    control/target order, physical time, module and exact channel probabilities.
    """
    reverse = {i: site for site, i in compiled.physical_qubit_map.items()}
    resets = {p.module_id: p for p in compiled.preparations}
    current, started, atoms, layer = {}, set(), Counter(), 0
    ignored = {"QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS"}
    for inst in compiled.circuit:
        if inst.name == "TICK":
            layer += 1
            continue
        if inst.name in ignored:
            continue
        if inst.tag in resets and inst.tag not in started:
            prep = resets[inst.tag]
            current[prep.block_id] = prep.logical_id
            started.add(inst.tag)
        width = 2 if inst.name in ("CX", "DEPOLARIZE2") else 1
        targets = inst.targets_copy()
        for first in range(0, len(targets), width):
            sites = tuple(
                (current[reverse[t.value][0]], reverse[t.value][1])
                for t in targets[first : first + width]
            )
            atoms[layer, inst.name, inst.tag, tuple(inst.gate_args_copy()), sites] += 1
    return atoms


def injected_fault(compiled, instruction, *, before=False, axis="X", target=None, result=False):
    """Return an ideal physical circuit with one deterministic Pauli/result fault."""
    out = stim.Circuit()
    for index, inst in enumerate(compiled.ideal_circuit):
        if index == instruction:
            q = inst.targets_copy()[0].value if target is None else target
            if result:
                for t in inst.targets_copy():
                    out.append(inst.name, [t], float(t.value == q), tag=inst.tag)
                continue
            if before:
                out.append(axis + "_ERROR", [q], 1)
            out.append(inst)
            if not before:
                out.append(axis + "_ERROR", [q], 1)
        else:
            out.append(inst)
    return out


def fault_points(c):
    """Choose matching module/local physical points before/after Bell and reused resets."""
    points = []
    bell = c.bell_measurements[1]
    prep = next(p for p in c.preparations if p.logical_id == "A1")
    after = next(
        f
        for f in c.fragments
        if f.operation_type == "SyndromeExtraction" and f.block_use_ids == (bell.output_use_id,)
    )
    for module, names, before, result in (
        (bell.x_readout.module_id, {"MX"}, True, False),
        (after.module_id, {"R", "RX"}, False, False),
        (prep.module_id, {"R", "RX"}, True, False),
        (prep.module_id, {"R", "RX"}, False, False),
        (prep.module_id, {"CX"}, False, False),
        (c.readouts[-1].module_id, {"M", "MX"}, False, True),
    ):
        index = next(
            i for i, inst in enumerate(c.ideal_circuit) if inst.tag == module and inst.name in names
        )
        points.append((index, before, result))
    return points


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_fresh_resource_unfolding_and_deterministic_fault_truth_tables(d, basis):
    """Same primitives and TICK schedule agree after each reset interval is renamed."""
    model = NoiseModel(NoiseParameters(0.001, 0.002, 0.003, 0.004, 0.005))
    reused = build_explicit_three_patch_knill(
        distance=d, basis=basis, teleportations=3, noise_model=model
    )
    fresh = build_knill(distance=d, basis=basis, teleportations=3, noise_model=model)
    assert reused.circuit.num_qubits == 3 * (2 * d * d - 1)
    assert fresh.circuit.num_qubits == 7 * (2 * d * d - 1)
    assert len(reused.measurements) == len(fresh.measurements)
    assert len(reused.detectors) == len(fresh.detectors)
    assert unfolded_physical_sites(reused) == unfolded_physical_sites(fresh)
    for c in (reused, fresh):
        for p in c.preparations:
            assert p.rounds == d
    for (ir, before, result), (jf, before_f, result_f) in zip(
        fault_points(reused), fault_points(fresh), strict=True
    ):
        assert (before, result) == (before_f, result_f)
        signatures = []
        for c, index in ((reused, ir), (fresh, jf)):
            physical = injected_fault(c, index, before=before, result=result)
            oracle = stim.FlipSimulator(
                batch_size=1, num_qubits=c.circuit.num_qubits, disable_stabilizer_randomization=True
            )
            oracle.do(physical)
            _, _, _, events, labels = oracle.to_numpy(
                transpose=True, output_detector_flips=True, output_observable_flips=True
            )
            raw = physical.compile_sampler(seed=905).sample(16)
            actual, truth = c.ideal_circuit.compile_m2d_converter().convert(
                measurements=raw, separate_observables=True
            )
            np.testing.assert_array_equal(actual, np.repeat(events, 16, axis=0))
            np.testing.assert_array_equal(truth, np.repeat(labels, 16, axis=0))
            view = c.make_decoder_view(
                detector_selector=DetectorSelector(use_ids=(c.bell_measurements[-1].output_use_id,))
            )
            np.testing.assert_array_equal(
                view.events_from_raw(raw), actual[:, view.detector_map.global_ids]
            )
            signatures.append((events, labels))
        for a, b in zip(*signatures, strict=True):
            np.testing.assert_array_equal(a, b)


def test_stale_preparation_wrong_epoch_record_and_reset_frame_negatives():
    """Old use hypotheses must reject or yield demonstrably wrong physical predictions."""
    c = build_explicit_three_patch_knill(allow_open_outputs=True)
    raw, sims = simulate(c, range(32))
    corrections = preparation_corrections(c, raw)
    old = c.preparations[0]
    fresh = next(p for p in c.preparations if p.block_use_id == BlockUseId("P0", 2))
    stale = dict(corrections)
    stale[fresh.module_id] = corrections[old.module_id]
    with pytest.raises(ValueError):
        c.evaluate_frames(raw, stale)
    result = c.evaluate_frames(raw, corrections)
    final_bell = c.bell_measurements[-1]
    key = final_bell.z_readout.logical_parity.terms[0]
    changed = raw.copy()
    changed[:, c.measurement_index_by_key[key]] ^= True
    wrong = c.evaluate_frames(changed, corrections, validation="hypothesis")
    assert any(
        corrected_expectation(sim, c, pauli(c, "D", "Z"), [wrong.final_frames["D"][i]]) == -1
        for i, sim in enumerate(sims)
    )
    reset = next(
        i
        for i, inst in enumerate(c.ideal_circuit)
        if inst.tag == fresh.module_id and inst.name in ("R", "RX")
    )
    signatures = []
    for before in (True, False):
        physical = injected_fault(c, reset, before=before)
        oracle = stim.FlipSimulator(
            batch_size=1, num_qubits=c.circuit.num_qubits, disable_stabilizer_randomization=True
        )
        oracle.do(physical)
        x, z = oracle.to_numpy(transpose=True, output_xs=True, output_zs=True)[:2]
        signatures.append(np.concatenate((x, z), axis=1))
    assert not signatures[0].any()  # Actual reset extinguishes the arriving physical Pauli.
    assert signatures[1].any()  # Incorrectly copying it through reset changes physical output.
    assert not np.array_equal(wrong.corrected_measurements, result.corrected_measurements)


def test_same_physical_site_record_correction_on_wrong_epoch_changes_output():
    """A P0/1 Z-readout correction cannot be substituted by the older P0/0 X record."""
    from logical_to_stim_converter.decoding import CorrectionBatch

    c = build_explicit_three_patch_knill(allow_open_outputs=True)
    raw, sims = simulate(c, range(8))
    corrections = preparation_corrections(c, raw)
    old, later = c.bell_measurements[0].x_readout, c.bell_measurements[1].z_readout
    local = next(
        k.local_id
        for k in old.logical_parity.terms
        if k.local_id in {j.local_id for j in later.logical_parity.terms}
    )
    plan = c.make_frame_plan()
    final = []
    for readout in (old, later):
        b = plan.boundary_by_id[readout.module_id]
        bits = np.zeros((len(raw), len(b.input_ids)), dtype=bool)
        bits[:, [k.local_id for k in readout.records].index(local)] = True
        state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
        for p in c.preparations:
            prep_boundary = plan.boundary_by_id[p.module_id]
            prep_bits = np.array(
                [
                    [q in f.x_support for q in p.data_ids] + [q in f.z_support for q in p.data_ids]
                    for f in corrections[p.module_id]
                ],
                dtype=bool,
            )
            state.apply(
                CorrectionBatch(
                    plan.source_fingerprint,
                    p.module_id,
                    prep_bits,
                    p.block_use_id,
                    prep_boundary.input_ids,
                )
            )
        state.apply(
            CorrectionBatch(
                plan.source_fingerprint, readout.module_id, bits, readout.block_use_id, b.input_ids
            )
        )
        final.append((state.final_x, state.final_z))
        operator = pauli(c, "D", "Z")
        xs, zs = operator.to_numpy()
        for shot, sim in enumerate(sims):
            parity = (
                np.count_nonzero(state.final_x[shot] & zs)
                + np.count_nonzero(state.final_z[shot] & xs)
            ) % 2
            assert sim.peek_observable_expectation(operator) * (-1) ** parity == (
                1 if readout == old else -1
            )
    assert not np.array_equal(final[0][0], final[1][0])


@pytest.mark.parametrize("late", [False, True])
def test_reused_p0_temporal_model_targets_are_physical_not_sampled(noisy_three_cycles, late):
    """Inject early/last result flips in every P0 use's model-only temporal targets."""
    c, _ = noisy_three_cycles
    requests = make_stage_requests(c)
    for r in requests.boundaries:
        if r.block_id != "P0":
            continue
        key = r.checks[0].measurements[-1 if late else 0]
        record = c.measurement_index_by_key[key]
        physical, cursor = stim.Circuit(), 0
        for inst in r.model_circuit.without_noise():
            if inst.name in ("M", "MX") and cursor <= record < cursor + inst.num_measurements:
                for j, target in enumerate(inst.targets_copy()):
                    physical.append(inst.name, [target], int(cursor + j == record), tag=inst.tag)
            else:
                physical.append(inst)
            cursor += inst.num_measurements
        raw = physical.compile_sampler(seed=906).sample(16)
        _, targets = r.model_circuit.compile_m2d_converter().convert(
            measurements=raw, separate_observables=True
        )
        expected = np.zeros_like(targets)
        # A one-round ordinary SE window has the same first and final record.
        expected[:, 0] = record == r.last_record_ids[0]
        np.testing.assert_array_equal(targets, expected)


def test_stage_requests_follow_actual_uses_and_omit_canonical_probes():
    """All three cycles expose current check history, temporal target and causal IDs."""
    c = build_explicit_three_patch_knill()
    requests = make_stage_requests(c)
    prep_by_use = {p.block_use_id: p for p in c.preparations}
    assert [module for _, module in requests.order] == [
        f.module_id
        for f in c.fragments
        if f.operation_type in ("LogicalInit", "SyndromeExtraction", "LogicalMeasure")
    ]
    for request in (*requests.boundaries, *requests.readouts):
        assert request.source_preparation == prep_by_use[request.block_use_id]
        for basis in "XZ":
            np.testing.assert_array_equal(
                request.source_preparation.check_matrix(basis),
                prep_by_use[request.block_use_id].check_matrix(basis),
            )
    assert not any(i.name == "MPP" for i in c.circuit)
    assert all(any(i.name == "MPP" for i in r.model_circuit) for r in requests.boundaries)
