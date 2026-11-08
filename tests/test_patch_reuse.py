"""Physical replay and lifecycle proofs for explicitly recycled fixed patches."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest
import stim
import stimflow as sf

from logical_to_stim_converter import (
    BindPatch,
    BlockUseId,
    CircuitCompiler,
    CodeSpec,
    CompilerContext,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    MeasurementKey,
    NoiseModel,
    RotatedSurfaceCodeBackend,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from logical_to_stim_converter.compiler._logical import LogicalFlowTracker
from logical_to_stim_converter.core.compiler_context import BlockStatus


def compiler(d=3, count=1, mapping=None, reverse=False):
    """Place fixed patches; caller supplies explicit initial reservations."""
    blocks = [LogicalBlock.placed(f"P{i}", CodeSpec.rotated_surface(d), patch_index=i)
              for i in range(count)]
    return CircuitCompiler(blocks[::-1] if reverse else blocks,
                           logical_to_block={"old": "P0"} if mapping is None else mapping)


def memory_use(logical, basis, bit=0, mode="physical", rounds=2):
    """Prepare/read one signed logical eigenstate with an optional encoded Pauli."""
    result = [LogicalInit(logical, basis, rounds)]
    if bit:
        result.append(LogicalPauli(logical, "Z" if basis == "X" else "X", mode=mode))
    result += [SyndromeExtraction(logical, 1), LogicalMeasure(logical, basis)]
    return result


def test_use_identity_validation_and_immutability():
    use = BlockUseId("P0", 0)
    assert use == BlockUseId("P0")
    assert len({use, BlockUseId("P0", 0), BlockUseId("P0", 1)}) == 2
    assert MeasurementKey("P0", "D1", "readout").block_use_id == use
    with pytest.raises(FrozenInstanceError):
        use.epoch = 1
    for epoch in (-1, True, 1.0, "0", None):
        with pytest.raises(ValueError, match="nonnegative integer"):
            BlockUseId("P0", epoch)
        with pytest.raises(ValueError, match="nonnegative integer"):
            MeasurementKey("P0", "D1", "readout", epoch=epoch)
    for name in ("", None, 0):
        with pytest.raises(ValueError):
            BlockUseId(name)
        with pytest.raises(ValueError):
            BindPatch(name, "P0")
        with pytest.raises(ValueError):
            BindPatch("new", name)


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bits", [(0, 0), (0, 1), (1, 0), (1, 1)])
@pytest.mark.parametrize("mode", ["physical", "frame"])
def test_two_independent_physical_uses(d, basis, bits, mode):
    c = compiler(d)
    first = c.compile(memory_use("old", basis, bits[0], mode))
    program = [*memory_use("old", basis, bits[0], mode), BindPatch("new", "P0"),
               *memory_use("new", basis, bits[1], mode)]
    r = c.compile(program, noise_model=NoiseModel.uniform_depolarizing(0.001))
    assert r.ideal_circuit.num_qubits == 2 * d * d - 1
    assert r.physical_qubit_map == first.physical_qubit_map
    assert r.ideal_circuit.get_final_qubit_coordinates() == (
        first.ideal_circuit.get_final_qubit_coordinates())
    assert [u.use_id for u in r.block_uses] == [BlockUseId("P0", 0), BlockUseId("P0", 1)]
    assert r.binding_history[0].previous_use == BlockUseId("P0", 0)
    assert r.logical_to_block == {"new": "P0"}
    assert len(r.preparations) == len(r.readouts) == len(r.observables) == 2
    assert len(r.measurement_index_by_key) == len(r.measurements)
    assert [o.logical_id for o in r.observables] == ["new", "old"]
    assert [o.expected_value for o in r.observables] == [bits[1], bits[0]]
    for epoch, use in enumerate(r.block_uses):
        prep, readout = r.preparations[epoch], r.readouts[epoch]
        assert prep.block_use_id == readout.block_use_id == use.use_id
        assert prep.rounds == 2
        assert {k.epoch for ch in prep.checks for k in ch.measurements} == {epoch}
        assert all(ch.measurements[0].round_index == 0 for ch in prep.checks)
        assert all(k.round_index is None and k.epoch == epoch for k in readout.records)
        assert use.logical_owner_history[0].logical_id == prep.logical_id
        assert use.reset_module_id == prep.module_id
        assert use.terminal_module_id == readout.module_id
        records = [m for m in r.measurements if m.key.block_use_id == use.use_id]
        assert use.measurement_start == records[0].index
        assert use.measurement_stop == records[-1].index + 1
        assert all(use.time_layer_start <= m.time_layer < use.time_layer_stop for m in records)
    assert r.block_uses[0].measurement_stop == r.block_uses[1].measurement_start
    assert r.block_uses[0].time_layer_stop == r.block_uses[1].time_layer_start
    # Read the instruction stream independently, checking absolute and rec offsets.
    cursor = 0
    sites = {i: site for site, i in r.physical_qubit_map.items()}
    fragments = {f.module_id: f for f in r.fragments}
    resets = []
    for inst in r.ideal_circuit:
        if inst.name in ("R", "RX"):
            f = fragments[inst.tag]
            if f.operation_type == "LogicalInit" and any(
                sites[t.value][1] in c.blocks[0].layout.data_ids for t in inst.targets_copy()
            ):
                resets.append(f.block_use_ids[0])
        if stim.gate_data(inst.name).produces_measurements:
            for target in inst.targets_copy():
                m = r.measurements[cursor]
                assert (m.key.block_id, m.key.local_id) == sites[target.value]
                assert m.key.block_use_id in fragments[inst.tag].block_use_ids
                assert r.measurement_index_by_key[m.key] == cursor
                cursor += 1
        if inst.name == "DETECTOR":
            keys = [r.measurements[cursor + t.value].key for t in inst.targets_copy()]
            assert len({k.block_use_id for k in keys}) == 1
    assert resets == [BlockUseId("P0", 0), BlockUseId("P0", 1)]
    raw = r.ideal_circuit.compile_sampler(seed=731).sample(64)
    interpreted = r.interpreted_measurements(raw)
    np.testing.assert_array_equal(interpreted, np.tile([bits[1], bits[0]], (64, 1)))
    for o in r.observables:
        expected_raw = o.expected_value ^ o.frame_correction.constant
        assert np.all(np.bitwise_xor.reduce(raw[:, o.measurement_indices], axis=1) == expected_raw)
    dets, obs = r.ideal_circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True)
    assert not dets.any() and not obs.any()
    r.noisy_circuit.detector_error_model()
    r.validate_metadata()
    assert c.compile(program).ideal_circuit == r.ideal_circuit


def test_binding_reserves_without_starting_a_use_or_physical_time():
    c = compiler(count=2)
    prefix = memory_use("old", "Z")
    before = c.compile(prefix, allow_open_outputs=True,
                       noise_model=NoiseModel.uniform_depolarizing(0.001))
    after = c.compile([*prefix, BindPatch("new", "P0"), BindPatch("unused", "P1")],
                      allow_open_outputs=True,
                      noise_model=NoiseModel.uniform_depolarizing(0.001))
    assert before.ideal_circuit == after.ideal_circuit
    assert before.noisy_circuit == after.noisy_circuit
    assert before.time_layers == after.time_layers
    assert before.block_uses == after.block_uses
    assert after.block_status == {"P0": BlockStatus.UNINITIALIZED,
                                  "P1": BlockStatus.UNINITIALIZED}
    assert after.binding_history[1].previous_use is None
    assert "new" not in after.preparation_dependencies
    ctx = CompilerContext(c.blocks, {})
    ctx2 = ctx.bind_patch(BindPatch("fresh", "P0"), "b")
    assert ctx.epochs == ctx2.epochs == {"P0": -1, "P1": -1}
    assert ctx.logical_to_block == {} and ctx2.logical_to_block == {"fresh": "P0"}


@pytest.mark.parametrize("tail, message", [
    ([BindPatch("fresh", "missing")], "Unknown physical block"),
    ([BindPatch("old", "P1")], "already live"),
    ([BindPatch("fresh", "P0")], "active or reserved"),
    ([[BindPatch("a", "P1"), BindPatch("b", "P1")]], "same physical block"),
    ([[BindPatch("a", "P0"), LogicalInit("old", "Z", 1)]], "same physical block"),
    ([BindPatch("a", "P1"), BindPatch("b", "P1")], "active or reserved"),
    ([SyndromeExtraction("old", 1)], "active"),
    ([LogicalMeasure("old", "Z")], "active"),
    ([LogicalInit("unknown", "Z", 1)], "Unknown logical"),
])
def test_binding_and_uninitialized_operand_failures(tail, message):
    with pytest.raises(ValueError, match=message):
        compiler(count=2).compile(tail, allow_open_outputs=True)


@pytest.mark.parametrize("op", [LogicalInit("old", "Z", 1), SyndromeExtraction("old", 1),
                               LogicalMeasure("old", "Z"), TransversalH("old")])
def test_retired_alias_cannot_operate_on_a_recycled_patch(op):
    prefix = memory_use("old", "Z")
    for suffix in ([op], [BindPatch("new", "P0"), LogicalInit("new", "Z", 1), op]):
        with pytest.raises(ValueError, match="Retired logical handle"):
            compiler().compile([*prefix, *suffix], allow_open_outputs=True)
    with pytest.raises(ValueError, match="already retired"):
        compiler().compile([*prefix, BindPatch("old", "P0")], allow_open_outputs=True)


def test_active_binding_and_parallel_reset_readout_conflicts():
    c = compiler()
    with pytest.raises(ValueError, match="active or reserved"):
        c.compile([LogicalInit("old", "Z", 1), BindPatch("new", "P0")])
    with pytest.raises(ValueError, match="same physical block"):
        c.compile([LogicalInit("old", "Z", 1),
                   [LogicalMeasure("old", "Z"), BindPatch("new", "P0")]])
    with pytest.raises(ValueError, match="same physical block"):
        c.compile([[LogicalInit("old", "Z", 1), LogicalMeasure("old", "Z")]])


def test_cross_reset_stabilizer_flow_is_rejected():
    c = compiler()
    backend = RotatedSurfaceCodeBackend()
    block = c.blocks[0]
    reset = backend.initialization(block, "fresh", "Z")
    check = backend.stabilizer_code(block, "fresh", 0).tiles[0].to_pauli_map()
    bad = reset.with_edits(flows=(*reset.flows, sf.Flow(start=check, end=check, sign=False)))
    with pytest.raises(ValueError):
        bad.verify()


def test_independent_epochs_spectators_and_registration_order():
    program = [LogicalInit("old", "X", 1),
               [LogicalMeasure("old", "X"), LogicalInit("spectator", "Z", 1)],
               [BindPatch("new", "P0"), SyndromeExtraction("spectator", 2)],
               [LogicalInit("new", "Z", 2), SyndromeExtraction("spectator", 1)],
               LogicalMeasure(("new", "spectator"), "Z")]
    mapping = {"old": "P0", "spectator": "P1"}
    first = compiler(count=2, mapping=mapping).compile(program)
    reverse = compiler(count=2, mapping=mapping, reverse=True).compile(program)
    assert first.ideal_circuit == reverse.ideal_circuit
    assert first.block_uses == reverse.block_uses
    assert first.measurements == reverse.measurements
    assert [u.use_id for u in first.block_uses] == [BlockUseId("P0", 0), BlockUseId("P1", 0),
                                                 BlockUseId("P0", 1)]
    assert {m.key.epoch for m in first.measurements if m.key.block_id == "P1"} == {0}
    dets, obs = first.circuit.compile_detector_sampler(seed=5).sample(32, separate_observables=True)
    assert not dets.any() and not obs.any()


def test_knill_relocation_then_explicit_recycled_preparation(monkeypatch):
    mapping = {"data": "P0", "anc0": "P1", "out0": "P2"}
    c = compiler(count=3, mapping=mapping)
    snapshots = []
    through = LogicalFlowTracker.through

    def capture(self, parts):
        result = through(self, parts)
        snapshots.append((self.logical_state.num_qubits,
                          self.context.observable_ids["data"]))
        return result

    monkeypatch.setattr(LogicalFlowTracker, "through", capture)
    prefix = [LogicalInit("data", "Z", 1), KnillEC("data", "anc0", "out0", rounds=1)]
    r = c.compile([*prefix, BindPatch("new", "P0"), LogicalInit("new", "X", 1)],
                  allow_open_outputs=True)
    assert r.logical_to_block == r.open_logical_outputs == {"data": "P2", "new": "P0"}
    assert r.relocation_history[0].logical_id == "data"
    assert r.relocation_history[0].source_use_id == BlockUseId("P0", 0)
    assert r.relocation_history[0].output_use_id == BlockUseId("P2", 0)
    assert [e.logical_id for e in r.block_uses[2].logical_owner_history] == ["out0", "data"]
    prep = r.preparations[-1]
    assert prep.block_use_id == BlockUseId("P0", 1)
    assert r.preparation_dependencies["new"] == (prep.module_id,)
    assert set(r.frames["new"].preparation_syndromes) == set(prep.gauge_measurements)
    assert r.orientations["new"] == 0
    assert all(n == 3 and slot == 1 for n, slot in snapshots)
    for retired in ("anc0", "out0"):
        with pytest.raises(ValueError, match="Retired"):
            c.compile([*prefix, LogicalInit(retired, "Z", 1)], allow_open_outputs=True)
    # Expansion must resolve new resource names only after their explicit binds.
    again = c.compile([*prefix, BindPatch("anc1", "P0"), BindPatch("out1", "P1"),
                       KnillEC("data", "anc1", "out1", rounds=1)], allow_open_outputs=True)
    assert again.logical_to_block == {"data": "P1"}
    assert again.relocation_history[-1].source_use_id == BlockUseId("P2", 0)
    assert again.relocation_history[-1].output_use_id == BlockUseId("P1", 1)


def test_many_fresh_resources_reuse_bounded_tableau_slots(monkeypatch):
    sizes = []
    through = LogicalFlowTracker.through

    def capture(self, parts):
        result = through(self, parts)
        sizes.append((self.context.num_logical_slots, self.logical_state.num_qubits,
                      self.context.logical_state.num_qubits))
        return result

    monkeypatch.setattr(LogicalFlowTracker, "through", capture)
    program = memory_use("old", "Z", 1)
    for i in range(12):
        program += [BindPatch(f"fresh{i}", "P0"), *memory_use(f"fresh{i}", "XZ"[i % 2], i % 2)]
    r = compiler().compile(program)
    assert len(r.block_uses) == len(r.observables) == 13
    assert set(sizes) == {(1, 1, 1)}
    dets, obs = r.circuit.compile_detector_sampler(seed=7).sample(16, separate_observables=True)
    assert not dets.any() and not obs.any()


def test_recycled_h_cnot_flow_and_independent_bases():
    c = compiler(count=2, mapping={"old": "P0", "other": "P1"})
    r = c.compile([*memory_use("old", "X", 1), BindPatch("new", "P0"),
                   LogicalInit(("new", "other"), "Z", 1), TransversalH("new"),
                   TransversalCNOT("new", "other"),
                   LogicalMeasure(("new", "other"), "Z", mode="random")])
    assert len(r.readouts) == 3
    assert r.readouts[-1].block_use_id == BlockUseId("P1", 0)
    assert r.readouts[-2].block_use_id == BlockUseId("P0", 1)
    assert r.ideal_circuit.num_observables == 1
    # Metadata corruption must not silently alias the two readout epochs.
    wrong = list(r.measurements)
    i = next(m.index for m in wrong if m.key.epoch == 1)
    wrong[i] = replace(wrong[i], key=replace(wrong[i].key, epoch=0))
    with pytest.raises(ValueError, match="measurement|Measurement"):
        replace(r, measurements=tuple(wrong)).validate_metadata()
