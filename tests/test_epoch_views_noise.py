"""Independent reset/use provenance, exact physical noise and DEM marginal checks."""

from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    BindPatch,
    BlockUseId,
    CircuitCompiler,
    CodeSpec,
    DetectorSelector,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    MeasurementKey,
    NoiseInjector,
    NoiseModel,
    NoiseOverride,
    NoiseParameters,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
    observable_local_views,
)
from logical_to_stim_converter.compiler._parallel import moments
from logical_to_stim_converter.core.compiler_context import TimeLayer
from logical_to_stim_converter.decoding import DecoderViewError, SourceMismatchError
from logical_to_stim_converter.decoding.views import source_fingerprint
from tests.helpers.decoder_view_physics import (
    assert_marginal_equivalent,
    hand_artifact,
    physical_instructions,
)
from tests.test_clifford_noise import fault_counter


def placed_compiler(d=3, count=1, mapping=None):
    """Register fixed physical patches, with explicit logical reservations."""
    blocks = [LogicalBlock.placed(f"P{i}", CodeSpec.rotated_surface(d), patch_index=i)
              for i in range(count)]
    return CircuitCompiler(blocks, logical_to_block={"q0": "P0"} if mapping is None else mapping)


@pytest.fixture(scope="module", params=[3, 5])
def independent_reuses(request):
    d = request.param
    program = []
    for epoch, basis in enumerate(("Z", "X", "Z")):
        q = f"q{epoch}"
        if epoch:
            program.append(BindPatch(q, "P0"))
        program += [LogicalInit(q, basis, epoch + 1),
                    LogicalPauli(q, "X" if basis == "Z" else "Z",
                                 mode="physical" if epoch != 1 else "frame"),
                    SyndromeExtraction(q, 1), LogicalMeasure(q, basis)]
    return placed_compiler(d).compile(program, noise_model=NoiseModel.uniform_depolarizing(.001))


def test_global_use_metadata_and_signed_physical_records(independent_reuses):
    c = independent_reuses
    raw = c.ideal_circuit.compile_sampler(seed=811).sample(64)
    events, truth = c.ideal_circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True)
    assert not events.any() and not truth.any()
    assert c.interpreted_measurements(raw).all()
    fragments = {f.module_id: f for f in c.fragments}
    for d in c.detectors:
        assert d.source_use_ids == tuple(sorted({c.measurements[i].key.block_use_id
                                                for i in d.measurement_indices}))
        assert d.anchor_use_id == fragments[d.anchor_module_id].block_use_ids[0]
        assert d.source_use_ids == (d.anchor_use_id,)
        assert not np.bitwise_xor.reduce(raw[:, d.measurement_indices], axis=1).any()
        assert len(d.coordinates) == 3
    assert set(c.use_preparation_dependencies) == {BlockUseId("P0", i) for i in range(3)}
    for prep in c.preparations:
        assert c.use_preparation_dependencies[prep.block_use_id] == (prep.module_id,)
    for layer in c.time_layers:
        assert len({u.block_id for u in layer.active_use_ids}) == len(layer.active_use_ids)
        assert tuple(u.block_id for u in layer.active_use_ids) == layer.active_blocks
    bad = list(c.detectors)
    bad[0] = replace(bad[0], anchor_use_id=BlockUseId("P0", 2))
    with pytest.raises(ValueError, match="provenance"):
        replace(c, detectors=tuple(bad)).validate_metadata()
    with pytest.raises(ValueError, match="one active use"):
        TimeLayer(0, ("P0",), {}, frozenset(), (BlockUseId("P0", 0), BlockUseId("P0", 1)))


@pytest.mark.parametrize("membership", ["anchor", "touching", "strict"])
def test_use_views_block_union_and_exact_marginals(independent_reuses, membership):
    c = independent_reuses
    source = c.circuit.copy()
    raw = source.compile_sampler(seed=812).sample(128)
    events, truth = source.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True)
    all_ids = []
    for epoch in range(3):
        use = BlockUseId("P0", epoch)
        view = c.make_decoder_view(
            detector_selector=DetectorSelector(use_ids=(use,), use_membership=membership),
            observable_selector=(f"q{epoch}",),
            measurement_selector=lambda m: m.key.block_use_id == use)
        assert view.schema_version == "decoder-view-v3"
        assert view.audit.region_use_ids == view.audit.requested_use_ids == (use,)
        assert {m.key.epoch for m in view.measurements} == {epoch}
        assert {d.anchor_use_id for d in view.detectors} == {use}
        np.testing.assert_array_equal(view.events_from_raw(raw),
                                      events[:, view.detector_map.global_ids])
        np.testing.assert_array_equal(view.observable_flips_from_raw(raw), truth[:, (epoch,)])
        assert physical_instructions(view.circuit) == physical_instructions(source)
        assert_marginal_equivalent(source.detector_error_model(), view)
        all_ids.extend(view.detector_map.global_ids)
    block = c.make_decoder_view(detector_selector=DetectorSelector(block_ids=("P0",)))
    assert set(all_ids) == set(block.detector_map.global_ids)
    joint = c.make_decoder_view(detector_selector=DetectorSelector(
        use_ids=(BlockUseId("P0", 0), BlockUseId("P0", 2)), use_membership="strict"))
    assert {u.epoch for u in joint.audit.region_use_ids} == {0, 2}
    assert c.circuit == source


def test_locality_keeps_independent_uses_separate_and_explicit_order(independent_reuses):
    c = independent_reuses
    views = observable_local_views(c)
    assert len(views) == 3
    for epoch, v in enumerate(views):
        assert v.audit.region_use_ids == (BlockUseId("P0", epoch),)
        assert v.observable_map.global_ids == (epoch,)
    order = tuple(reversed(views[1].detector_map.global_ids))
    v = c.make_decoder_view(detector_selector=order, observable_selector=(2, 0))
    assert v.detector_map.global_ids == order and v.observable_map.global_ids == (2, 0)
    raw = c.circuit.compile_sampler(seed=813).sample(32)
    events, _ = c.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True)
    flips = np.zeros_like(raw)
    flips[:, c.measurements[-1].index] = True
    np.testing.assert_array_equal(v.events_from_raw(raw ^ flips),
                                  v.update_detection_events(events, flips))
    overridden = observable_local_views(c, region_selector=lambda o: DetectorSelector(
        block_ids=("P0",), block_membership="strict"))
    assert all(len(x.detectors) == len(c.detectors) for x in overridden)


def test_use_fingerprints_and_malformed_metadata(independent_reuses):
    c = independent_reuses
    view = c.make_decoder_view()
    changed = replace(c, binding_history=())
    assert source_fingerprint(c) != source_fingerprint(changed)
    with pytest.raises(SourceMismatchError):
        view.assert_source(changed)
    with pytest.raises(SourceMismatchError):
        c.make_decoder_view(expected_source_fingerprint="decoder-view-v2:stale")
    d = c.detectors[0]
    bad = replace(c, detectors=(replace(d, source_use_ids=(BlockUseId("P0", 99),)),
                                *c.detectors[1:]))
    with pytest.raises(DecoderViewError, match="provenance"):
        bad.make_decoder_view()
    with pytest.raises(DecoderViewError, match="BlockUseId"):
        DetectorSelector(use_ids=(("P0", 1),))


@pytest.mark.parametrize("fault_kind", ["X", "Y", "Z", "CX", "reset", "readout"])
def test_physical_fault_marginals_across_reset(independent_reuses, fault_kind):
    c = independent_reuses
    # Select old-use detectors but retain the final-use observable: a fault on
    # an excluded detector's region must survive if it touches this output.
    v = c.make_decoder_view(detector_selector=DetectorSelector(use_ids=(BlockUseId("P0", 0),)),
                            observable_selector=(2,))
    assert_marginal_equivalent(c.circuit.detector_error_model(), v)
    for epoch in (0, 2):
        prep = c.preparations[epoch]
        module = next(f.module_id for f in c.fragments if f.block_use_ids == (prep.block_use_id,)
                      and f.operation_type == ("LogicalMeasure" if fault_kind == "readout"
                                               else "LogicalInit"))
        physical = stim.Circuit()
        inserted = False
        for inst in c.ideal_circuit:
            if inst.tag == module and not inserted:
                targets = inst.targets_copy()
                if fault_kind == "readout" and inst.name in ("M", "MX"):
                    for j, t in enumerate(targets):
                        physical.append(inst.name, [t], int(j == 0), tag=inst.tag)
                    inserted = True
                    continue
                if fault_kind == "CX" and inst.name == "CX":
                    physical.append(inst)
                    physical.append("X_ERROR", [targets[0]], 1)
                    physical.append("Z_ERROR", [targets[1]], 1)
                    inserted = True
                    continue
                if fault_kind in ("X", "Y", "Z", "reset") and inst.name in ("R", "RX"):
                    physical.append(inst)
                    axis = (("X" if inst.name == "R" else "Z")
                            if fault_kind == "reset" else fault_kind)
                    physical.append(axis + "_ERROR", [targets[0]], 1)
                    inserted = True
                    continue
            physical.append(inst)
        assert inserted
        oracle = stim.FlipSimulator(batch_size=1, num_qubits=c.circuit.num_qubits,
                                    disable_stabilizer_randomization=True)
        oracle.do(physical)
        _, _, _, expected_events, expected_obs = oracle.to_numpy(
            transpose=True, output_detector_flips=True, output_observable_flips=True)
        raw = physical.compile_sampler(seed=814).sample(16)
        np.testing.assert_array_equal(
            v.events_from_raw(raw), np.repeat(expected_events[:, v.detector_map.global_ids], 16, 0))
        np.testing.assert_array_equal(v.observable_flips_from_raw(raw),
                                      np.repeat(expected_obs[:, (2,)], 16, 0))


def assert_exact_reuse_noise(c, model):
    """Read physical resets/readouts independently to derive active-use fault locations."""
    by_module = {f.module_id: f for f in c.fragments}
    active, epochs, expected = {}, Counter(), Counter()
    started, retired, measurement_rules = set(), set(), []
    for layer, instructions in enumerate(moments(c.ideal_circuit)):
        used, rules, releasing = set(), {}, set()
        for inst in instructions:
            if inst.tag not in by_module:
                continue
            f = by_module[inst.tag]
            rule = model.resolve(f.operation_type, f.noise)
            for bid in f.block_ids:
                rules[bid] = rule
            if f.operation_type == "LogicalInit" and f.module_id not in started:
                bid = f.block_id
                active[bid] = BlockUseId(bid, epochs[bid])
                epochs[bid] += 1
                started.add(f.module_id)
            if f.operation_type == "LogicalMeasure":
                releasing.add(f.block_id)
                retired.add(f.module_id)
            ts = [t.value for t in inst.targets_copy()]
            used.update(ts)
            if inst.name in ("M", "MX"):
                measurement_rules.append((inst.name, tuple(ts), rule.measurement, inst.tag))
                continue
            if inst.name == "CX":
                channel, p, width = "DEPOLARIZE2", rule.two_qubit, 2
            elif inst.name in ("R", "RX"):
                channel, p, width = "X_ERROR" if inst.name == "R" else "Z_ERROR", rule.reset, 1
            else:
                channel, p, width = "DEPOLARIZE1", rule.one_qubit, 1
            for j in range(0, len(ts), width):
                if p:
                    expected[layer, channel, tuple(ts[j:j + width]), p] += 1
        assert c.time_layers[layer].active_use_ids == tuple(sorted(active.values()))
        assert c.time_layers[layer].used_qubits == frozenset(used)
        for bid in active:
            sites = {i for (b, _), i in c.physical_qubit_map.items() if b == bid}
            p = rules.get(bid, model.default).idle
            if p:
                for i in sites - used:
                    expected[layer, "DEPOLARIZE1", (i,), p] += 1
        for bid in releasing:
            del active[bid]
    actual_measurements = [(i.name, tuple(t.value for t in i.targets_copy()),
                            i.gate_args_copy()[0] if i.gate_args_copy() else 0, i.tag)
                           for i in c.circuit if i.name in ("M", "MX")]
    assert measurement_rules == actual_measurements
    assert fault_counter(c.circuit) == expected
    assert c.circuit.without_noise() == c.ideal_circuit


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("zero", [False, True])
def test_exact_noise_gaps_reentry_overrides_and_zero_duration(d, zero):
    model = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005), {
        "LogicalInit": NoiseOverride(reset=.006, two_qubit=.007),
        "TransversalCNOT": NoiseOverride(two_qubit=.008),
        "LogicalMeasure": NoiseOverride(measurement=.009)})
    program = [LogicalInit("q0", "Z", 1), LogicalPauli("q0", "X", mode="physical"),
               LogicalMeasure("q0", "Z"), LogicalInit("s", "X", 1),
               BindPatch("q1", "P0"), SyndromeExtraction("s", 1),
               [LogicalInit("q1", "Z", 2, noise=NoiseOverride(reset=0 if zero else .011)),
                SyndromeExtraction("s", 2, noise=NoiseOverride(idle=0))],
               TransversalH("q1"), TransversalCNOT("q1", "s"),
               SyndromeExtraction(("q1", "s"), 1),
               LogicalMeasure(("q1", "s"), "X")]
    comp = placed_compiler(d, 2, {"q0": "P0", "s": "P1"})
    c = comp.compile(program, noise_model=model)
    assert_exact_reuse_noise(c, model)
    # Move a reservation through independent active work: it has no physical exposure.
    moved = list(program)
    moved[3], moved[4] = moved[4], moved[3]
    assert comp.compile(moved, noise_model=model).circuit == c.circuit
    with pytest.raises(ValueError, match="once"):
        NoiseInjector().apply(c.circuit, model=model, physical_map=c.physical_qubit_map,
                              layers=c.time_layers, fragments=c.fragments)
    c.circuit.detector_error_model()


@pytest.mark.parametrize("d", [3, 5])
def test_reused_composite_noise_and_causal_component(d):
    comp = placed_compiler(d, 3, {"D": "P0", "A": "P1", "B": "P2"})
    program = [LogicalInit("D", "Z", 1), KnillEC("D", "A", "B", rounds=1),
               BindPatch("A1", "P0"), BindPatch("B1", "P1"),
               KnillEC("D", "A1", "B1", rounds=2, noise=NoiseOverride(two_qubit=.007)),
               LogicalMeasure("D", "Z")]
    model = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005))
    c = comp.compile(program, noise_model=model)
    assert_exact_reuse_noise(c, model)
    v, = observable_local_views(c)
    assert set(v.audit.region_use_ids) == {u.use_id for u in c.block_uses}
    assert v.detector_map.global_ids == tuple(range(len(c.detectors)))
    assert any(len(d.source_use_ids) > 1 for d in c.detectors)
    for membership in ("anchor", "touching", "strict"):
        selected = c.make_decoder_view(detector_selector=DetectorSelector(
            use_ids=(BlockUseId("P0", 1),), use_membership=membership), observable_selector=())
        assert all(DetectorSelector(use_ids=(BlockUseId("P0", 1),),
                                    use_membership=membership)(x) for x in selected.detectors)
        assert_marginal_equivalent(c.circuit.detector_error_model(), selected)


def test_use_view_preserves_hyperedges_correlated_components_and_exact_snapshots():
    probability = .012345678901234567
    circuit = stim.Circuit()
    circuit.append("R", [0, 1, 2])
    circuit.append("DEPOLARIZE2", [0, 1], probability, tag="exact old use")
    circuit.append("CX", [0, 2])
    circuit.append("M", [0, 1, 2])
    for rec in (-3, -2, -1):
        circuit.append("DETECTOR", [stim.target_rec(rec)], [0, 0, 0])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-3)], 0)
    reset = stim.Circuit("SHIFT_COORDS(0, 0, 1)\nR 0 1 2\nM 0 1 2")
    circuit.append(stim.CircuitRepeatBlock(1, reset, tag="fresh use"))
    circuit.append("DETECTOR", [stim.target_rec(-3)], [0, 0, 0])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-3)], 1)
    c = hand_artifact(circuit)
    measurements = tuple(replace(m, key=MeasurementKey(
        m.key.block_id, m.key.local_id, m.key.kind, m.key.round_index, m.index // 3))
                         for m in c.measurements)
    detectors = tuple(replace(d, measurement_keys=tuple(measurements[i].key
                                                       for i in d.measurement_indices),
                              anchor_use_id=BlockUseId("patch", 0 if d.index < 3 else 1),
                              source_use_ids=(BlockUseId("patch", 0 if d.index < 3 else 1),))
                      for d in c.detectors)
    c = replace(c, measurements=measurements, detectors=detectors)
    old = c.make_decoder_view(detector_selector=DetectorSelector(use_ids=(BlockUseId("patch", 0),)),
                              observable_selector=(0,))
    hyperedges = [i for i in old.detector_error_model if i.type == "error"
                  and sum(t.is_relative_detector_id() for t in i.targets_copy()) > 2]
    assert hyperedges
    from logical_to_stim_converter import DEMOptions

    correlated = c.make_decoder_view(
        detector_selector=(2, 0, 1), observable_selector=(0,),
        dem_options=DEMOptions(decompose_errors=True))
    assert any(t.is_separator() for i in correlated.detector_error_model if i.type == "error"
               for t in i.targets_copy())
    for view in (old, correlated):
        assert_marginal_equivalent(c.circuit.detector_error_model(), view)
        assert view.source_circuit == circuit
        assert physical_instructions(view.circuit) == physical_instructions(circuit)
        depolarize = next(i for i in view.circuit if i.name == "DEPOLARIZE2")
        assert depolarize.gate_args_copy()[0] == probability
    assert len(correlated.source_circuit) == len(circuit)
