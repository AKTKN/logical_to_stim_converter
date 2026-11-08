"""Use-scoped temporal/Bell models and independent frame physics across real resets."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    BlockUseId,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    TransversalH,
)
from logical_to_stim_converter.decoding import (
    CorrectionBatch,
    DecoderViewError,
    SourceMismatchError,
    make_conditional_readout_model,
    make_stage_requests,
)
from logical_to_stim_converter.decoding.stages import make_boundary_request, module_end
from tests.helpers.knill_physics import explicit_reference, pauli
from tests.helpers.preparation_matching import preparation_corrections
from tests.test_epoch_views_noise import placed_compiler


@pytest.fixture(scope="module", params=[3, 5])
def reused_protocol(request):
    """P0 first holds independent X memory, then a Z Bell output; roles later swap."""
    comp = placed_compiler(request.param, 5,
                           {"old": "P0", "D": "P1", "A": "P2", "S": "P3", "T": "P4"})
    program = [LogicalInit("old", "X", 2), TransversalH("old"),
               LogicalMeasure("old", "Z"), BindPatch("B", "P0"),
               [LogicalInit("D", "Z", 2), LogicalInit("S", "X", 1), LogicalInit("T", "Z", 1)],
               KnillEC("D", "A", "B", rounds=2), TransversalH("D"),
               BindPatch("A1", "P1"), BindPatch("B1", "P2"),
               KnillEC("D", "A1", "B1", rounds=1), TransversalH("D"),
               SyndromeExtraction("D", 2)]
    c = comp.compile(program, allow_open_outputs=True,
                     noise_model=NoiseModel.uniform_depolarizing(.001))
    return c, make_stage_requests(c)


def test_boundary_and_readout_source_uses_and_causal_order(reused_protocol):
    c, requests = reused_protocol
    by_use = {p.block_use_id: p for p in c.preparations}
    fragments = {f.module_id: f for f in c.fragments}
    order = [f.module_id for f in c.fragments
             if f.operation_type in ("LogicalInit", "SyndromeExtraction", "LogicalMeasure")]
    assert [module for _, module in requests.order] == order
    for r in requests.boundaries:
        assert r.source_preparation == by_use[r.block_use_id]
        assert r.block_use_id == fragments[r.module_id].block_use_ids[0]
        assert all(k.block_use_id == r.block_use_id for h in r.checks for k in h.measurements)
        assert r.last_record_ids == tuple(c.measurement_index_by_key[h.measurements[-1]]
                                          for h in r.checks)
        prefix = c.circuit[:module_end(c.circuit, r.module_id)]
        assert r.model_circuit.num_measurements == prefix.num_measurements + len(r.target_ids)
        assert r.detector_error_model.num_observables == len(r.target_ids)
        assert all(set(d.measurement_indices) <= set(r.view.measurement_map.global_ids)
                   for d in r.view.detectors)
        assert not any(i.name == "MPP" for i in r.view.source_circuit)
    for r in requests.readouts:
        assert r.source_preparation == by_use[r.block_use_id]
        assert all(c.measurements[i].key.block_use_id == r.block_use_id for i in r.record_ids)
    old, current = (by_use[BlockUseId("P0", epoch)] for epoch in (0, 1))
    assert old.basis == "X" and current.basis == "Z"
    assert requests.readouts[0].readout.orientation == 1
    with pytest.raises(DecoderViewError, match="different module/use"):
        make_boundary_request(c, fragments[current.module_id], old)


@pytest.mark.parametrize("which", ["early", "late"])
def test_model_only_boundary_targets_against_physical_result_faults(reused_protocol, which):
    c, requests = reused_protocol
    # Both historical P0 uses and the final ordinary SE boundary are checked.
    selected = [r for r in requests.boundaries if r.block_id == "P0"] + [requests.boundaries[-1]]
    for r in selected:
        check = r.checks[0]
        target = c.measurement_index_by_key[check.measurements[0 if which == "early" else -1]]
        model = r.model_circuit
        physical, cursor = stim.Circuit(), 0
        for inst in model:
            if inst.name in ("M", "MX") and cursor <= target < cursor + inst.num_measurements:
                for j, t in enumerate(inst.targets_copy()):
                    physical.append(inst.name, [t], int(cursor + j == target), tag=inst.tag)
            else:
                one = stim.Circuit()
                one.append(inst)
                physical += one.without_noise()
            cursor += inst.num_measurements
        raw = physical.compile_sampler(seed=821).sample(32)
        _, labels = model.compile_m2d_converter().convert(
            measurements=raw, separate_observables=True)
        expected = np.zeros_like(labels)
        if which == "late":
            expected[:, 0] = True
        np.testing.assert_array_equal(labels, expected)
    assert not any(i.name == "MPP" for i in c.circuit)


def test_signed_sector_transfer_and_surviving_prior_use_dependency(reused_protocol):
    c, requests = reused_protocol
    raw = c.ideal_circuit.compile_sampler(seed=822).sample(64)
    sector = np.zeros((len(raw), len(requests.sector_input_ids)), dtype=bool)
    for b in requests.boundaries:
        for j, check in enumerate(b.checks):
            sector[:, requests.sector_input_ids.index((b.module_id, check.check_id))] = (
                raw[:, b.last_record_ids[j]])
    for r in requests.readouts:
        predicted = r.sector_map.apply(sector) ^ r.sector_constant
        measured = raw[:, r.record_ids].astype(np.uint8) @ r.check_matrix.T % 2
        np.testing.assert_array_equal(predicted, measured)
    # A's first resource use P2/0 is measured and P2 is reset as B1. Its old
    # sector still contributes to the surviving P0/1 data check through real CXs.
    first_a = next(p for p in c.preparations if p.logical_id == "A")
    later_data = next(r for r in requests.readouts
                      if r.readout.module_id == c.bell_measurements[1].x_readout.module_id)
    columns = [i for i, (module, _) in enumerate(requests.sector_input_ids)
               if module == first_a.module_id]
    assert later_data.sector_map.incidence_matrix[columns, :].nnz
    new_b = next(p for p in c.preparations if p.logical_id == "B1")
    reset_event = next(e for e in c.ancestry_events if e.event_id == new_b.module_id)
    assert reset_event.preparation_dependencies == (new_b.module_id,)
    assert reset_event.input_use_ids == ()
    assert reset_event.output_use_ids == (BlockUseId("P2", 1),)


def assert_conditional_atoms(c, model):
    """Propagate every categorical atom independently with Stim's Pauli simulator."""
    oracle = stim.FlipSimulator(batch_size=len(model.faults), num_qubits=c.circuit.num_qubits,
                                disable_stabilizer_randomization=True)
    grouped, at = {}, {}
    for row, f in enumerate(model.faults):
        grouped.setdefault(f.exclusive_group, []).append(f)
        at.setdefault(f.instruction_index, []).append((row, f))
        assert model.start_instruction <= f.instruction_index < model.end_instruction
    for group in grouped.values():
        assert sum(f.probability for f in group) == pytest.approx(.001)
        if group[0].channel == "DEPOLARIZE2":
            assert len(group) == 15
    cursor = 0
    for i, inst in enumerate(c.circuit[:model.end_instruction]):
        entries = at.get(i, ())
        for axis in "XYZ":
            mask = np.zeros((c.circuit.num_qubits, len(model.faults)), dtype=bool)
            for row, f in entries:
                if f.measurement_record is not None:
                    q = inst.targets_copy()[f.measurement_record - cursor].value
                    if axis == ("Z" if inst.name == "MX" else "X"):
                        mask[q, row] = True
            if mask.any():
                oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
        one = stim.Circuit()
        one.append(inst)
        oracle.do(one.without_noise())
        for axis in "XYZ":
            mask = np.zeros((c.circuit.num_qubits, len(model.faults)), dtype=bool)
            for row, f in entries:
                for q, a in f.paulis:
                    if a == axis:
                        mask[q, row] = True
            if mask.any():
                oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
        cursor += inst.num_measurements
    xs, zs, flips, _, _ = oracle.to_numpy(
        transpose=True, output_xs=True, output_zs=True, output_measure_flips=True)
    ids = [c.physical_qubit_map[model.output_use_id.block_id, q] for q in model.output_data_ids]
    np.testing.assert_array_equal(model.raw_flip_map.incidence_matrix.toarray(),
                                  flips[:, model.readout_record_ids])
    np.testing.assert_array_equal(model.output_x_map.incidence_matrix.toarray(), xs[:, ids])
    np.testing.assert_array_equal(model.output_z_map.incidence_matrix.toarray(), zs[:, ids])


def test_conditional_bell_windows_choose_current_resource_use(reused_protocol):
    c, _ = reused_protocol
    windows = []
    for bell in c.bell_measurements:
        m = make_conditional_readout_model(c, bell)
        prep = next(p for p in c.preparations if p.block_use_id == bell.output_use_id)
        assert m.output_preparation_module_id == prep.module_id
        assert m.output_use_id == bell.output_use_id
        assert m.data_use_id == bell.x_readout.block_use_id
        assert m.first_resource_use_id == bell.z_readout.block_use_id
        assert c.circuit[m.start_instruction].tag == m.resource_entangling_module_id
        assert_conditional_atoms(c, m)
        windows.append((m.start_instruction, m.end_instruction))
    assert windows[0][1] < windows[1][0]
    assert c.bell_measurements[0].output_use_id == BlockUseId("P0", 1)
    with pytest.raises(DecoderViewError, match="instance/use"):
        make_conditional_readout_model(c, replace(c.bell_measurements[0],
                                                output_use_id=BlockUseId("P0", 0)))


@pytest.mark.parametrize("reverse", [False, True])
def test_existing_bell_resource_conditional_window_uses_actual_cnot(reverse):
    comp = placed_compiler(3, 3, {"D": "P0", "A": "P1", "B": "P2"})
    resources = ("B", "A") if reverse else ("A", "B")
    c = comp.compile([LogicalInit("D", "Z", 1), BellStatePrep(*resources, 1),
                      KnillEC("D", "A", "B", prepare_resource=False)],
                     allow_open_outputs=True, noise_model=NoiseModel.uniform_depolarizing(.001))
    m = make_conditional_readout_model(c, c.bell_measurements[0])
    assert m.resource_entangling_module_id == next(f.module_id for f in c.fragments
                                                  if f.operation_type == "TransversalCNOT")
    assert_conditional_atoms(c, m)


@pytest.mark.parametrize("axis", ["X", "Z"])
def test_old_physical_frame_extinguished_but_teleported_classical_effect_survives(
    reused_protocol, axis
):
    c, _ = reused_protocol
    plan = c.make_frame_plan()
    old = c.preparations[0]
    boundary = plan.boundary_by_id[old.module_id]
    offset = 0 if axis == "X" else len(old.data_ids)
    bits = np.zeros((1, len(boundary.input_ids)), dtype=bool)
    bits[0, offset] = True
    delta = boundary.record_map.apply(bits)
    # Use exact semantic keys for all measurements outside the retired warmup.
    future = [m.index for m in c.measurements if m.key.block_use_id != old.block_use_id]
    assert not delta[:, future].any()
    assert not boundary.final_x_map.apply(bits).any()
    assert not boundary.final_z_map.apply(bits).any()
    data = next(p for p in c.preparations if p.logical_id == "D")
    carried = plan.boundary_by_id[data.module_id]
    bits = np.zeros((1, len(carried.input_ids)), dtype=bool)
    support = data.logical_x if axis == "X" else data.logical_z
    for q in support:
        bits[0, data.data_ids.index(q) + (0 if axis == "X" else len(data.data_ids))] = True
    final = carried.final_x_map.apply(bits) | carried.final_z_map.apply(bits)
    assert final.any()
    output = c.open_logical_outputs["D"]
    assert {i for i in np.flatnonzero(final[0])} <= {
        i for (b, _), i in c.physical_qubit_map.items() if b == output}
    fresh = next(p for p in c.preparations if p.logical_id == "A1")
    new_records = [m.index for m in c.measurements if m.module_id == fresh.module_id]
    assert not carried.record_map.apply(bits)[:, new_records].any()


def test_frame_plan_replay_matches_explicit_physical_execution_and_open_output(reused_protocol):
    c, _ = reused_protocol
    raw = c.ideal_circuit.compile_sampler(seed=823).sample(8)
    original = raw.copy()
    corrections = preparation_corrections(c, raw)
    evaluated = c.evaluate_frames(raw, corrections)
    plan = c.make_frame_plan()
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    by_module = {f.module_id: f for f in c.fragments}
    assert set(plan.boundary_by_id) == {f.module_id for f in c.fragments
                                      if f.operation_type in (
                                          "LogicalInit", "SyndromeExtraction", "LogicalMeasure")}
    for prep in c.preparations:
        b = plan.boundary_by_id[prep.module_id]
        assert b.block_use_id == prep.block_use_id
        bits = np.array([[q in frame.x_support for q in prep.data_ids]
                         + [q in frame.z_support for q in prep.data_ids]
                         for frame in corrections[prep.module_id]], dtype=bool)
        state.apply(CorrectionBatch(plan.source_fingerprint, prep.module_id, bits,
                                     prep.block_use_id, b.input_ids))
        with pytest.raises(DecoderViewError, match="already applied"):
            state.apply(CorrectionBatch(plan.source_fingerprint, prep.module_id, bits))
    np.testing.assert_array_equal(raw, original)
    np.testing.assert_array_equal(state.interpreted_measurements, evaluated.corrected_measurements)
    for logical, frames in evaluated.final_frames.items():
        bid = c.open_logical_outputs[logical]
        data = next(p.data_ids for p in c.preparations if p.block_id == bid)
        ids = [c.physical_qubit_map[bid, q] for q in data]
        np.testing.assert_array_equal(state.final_x[:, ids],
                                      [[q in f.x_support for q in data] for f in frames])
        np.testing.assert_array_equal(state.final_z[:, ids],
                                      [[q in f.z_support for q in data] for f in frames])
    for b in plan.boundaries:
        assert b.block_use_id == by_module[b.boundary_id].block_use_ids[0]
    view = c.make_decoder_view()
    events, _ = c.ideal_circuit.compile_m2d_converter().convert(
        measurements=state.interpreted_measurements, separate_observables=True)
    np.testing.assert_array_equal(state.events(view), events)
    for shot in range(3):
        reference = explicit_reference(c, state.interpreted_measurements[shot],
                                       {k: v[shot:shot + 1] for k, v in corrections.items()})
        assert reference.peek_observable_expectation(pauli(c, "D", "Z")) == 1
        assert reference.peek_observable_expectation(pauli(c, "S", "X")) == 1
        assert reference.peek_observable_expectation(pauli(c, "T", "Z")) == 1
    final_use = next(u.use_id for u in c.block_uses
                     if u.use_id.block_id == c.open_logical_outputs["D"]
                     and u.terminal_module_id is None)
    assert all(f.block_use_id == final_use for f in evaluated.final_frames["D"])


def test_stale_use_keys_input_order_and_hypothesis_validation_fail(reused_protocol):
    c, _ = reused_protocol
    raw = c.ideal_circuit.compile_sampler(seed=824).sample(2)
    plan = c.make_frame_plan()
    prep = next(p for p in c.preparations if p.block_use_id == BlockUseId("P0", 1))
    b = plan.boundary_by_id[prep.module_id]
    bits = np.zeros((len(raw), len(b.input_ids)), dtype=bool)
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    for correction, pattern in (
        (CorrectionBatch(plan.source_fingerprint, b.boundary_id, bits, BlockUseId("P0", 0)),
         "different physical use"),
        (CorrectionBatch(plan.source_fingerprint, b.boundary_id, bits,
                         input_ids=tuple(reversed(b.input_ids))), "ordering"),
        (CorrectionBatch(plan.source_fingerprint, b.boundary_id, bits[:1]), "shot count"),
        (CorrectionBatch(plan.source_fingerprint, b.boundary_id, bits[:, :-1]), "binary"),
    ):
        with pytest.raises(DecoderViewError, match=pattern):
            state.apply(correction)
    with pytest.raises(SourceMismatchError):
        state.apply(CorrectionBatch("decoder-view-v2:stale", b.boundary_id, bits))
    state.apply(CorrectionBatch(plan.source_fingerprint, b.boundary_id, bits, prep.block_use_id))
    corrections = preparation_corrections(c, raw)
    frame = corrections[prep.module_id][0]
    for broken in (replace(frame, block_use_id=BlockUseId("P0", 0)),
                   replace(frame, source_syndromes=tuple(replace(k, epoch=0)
                                                        for k in frame.source_syndromes)),
                   replace(frame, x_support=("unknown_data",))):
        altered = dict(corrections)
        altered[prep.module_id] = (broken,) * len(raw)
        with pytest.raises(ValueError):
            c.evaluate_frames(raw, altered, validation="hypothesis")
