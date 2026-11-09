"""M9 structural boundaries and exact physical resource-preparation noise."""

from dataclasses import FrozenInstanceError, replace

import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    ResourcePreparationNoise,
    TransversalCNOT,
)
from logical_to_stim_converter.noise.resource_preparation import (
    resolve_resource_preparation_boundaries,
)
from tests.helpers.knill_physics import make_compiler
from tests.helpers.lstim_equivalence import compile_pair
from tests.helpers.lstim_programs import knill_operations, knill_source


def special(p=0, **kwargs):
    return NoiseModel(resource_preparation=ResourcePreparationNoise(True, p), **kwargs)


@pytest.mark.parametrize("enabled", [0, 1, None, "true", [], object()])
def test_invalid_enable(enabled):
    with pytest.raises(ValueError, match="boolean"):
        ResourcePreparationNoise(enabled)


@pytest.mark.parametrize("p", [True, False, None, "0.1", -.1, 1.1, float("nan"),
                              float("inf"), -float("inf"), complex(.1)])
def test_invalid_probability(p):
    with pytest.raises(ValueError, match="probability"):
        ResourcePreparationNoise(True, p)


def test_immutable_config_and_wrong_types():
    for value in (None, True, {}, .1):
        with pytest.raises(ValueError, match="ResourcePreparationNoise"):
            NoiseModel(resource_preparation=value)
    with pytest.raises(FrozenInstanceError):
        ResourcePreparationNoise().enabled = True
    assert NoiseModel().resource_preparation == ResourcePreparationNoise(False, 0)
    assert not NoiseModel.uniform_depolarizing(.01).resource_preparation.enabled


@pytest.mark.parametrize("explicit", [False, True])
def test_structural_preparation_boundaries(explicit):
    ops = [LogicalInit("D", "Z", 1)]
    if explicit:
        ops += [BellStatePrep("A", "B", 1), KnillEC("D", "A", "B", prepare_resource=False)]
    else:
        ops += [KnillEC("D", "A", "B", rounds=1)]
    ops += [LogicalMeasure("D", "Z")]
    c = make_compiler().compile(ops, noise_model=special())
    assert len(c.resource_preparation_boundaries) == 2
    for b in c.resource_preparation_boundaries:
        f = next(f for f in c.fragments if f.module_id == b.preparation_module_id)
        assert f.operation_type == "LogicalInit" and f.logical_id != "D"
        assert b.block_use_id == f.block_use_ids[0]
        assert len(b.data_sites) == 9
        assert c.ideal_circuit[b.ideal_boundary_instruction-1].name == "TICK"
        assert b.final_se_layer >= b.first_layer
    assert c.resource_preparation_boundaries[0].bell_preparation_id == (
        c.resource_preparation_boundaries[1].bell_preparation_id)


def test_bare_initializations_are_excluded_and_ideal_compile_stays_ideal():
    ops = [[LogicalInit("A", "X", 1), LogicalInit("B", "Z", 1)],
           TransversalCNOT("A", "B")]
    c = make_compiler().compile(ops, allow_open_outputs=True, noise_model=special(.2))
    assert not c.resource_preparation_boundaries
    ideal = make_compiler().compile([BellStatePrep("A", "B")], allow_open_outputs=True)
    assert ideal.noisy_circuit is None and not ideal.resource_preparation_boundaries


def test_three_cycle_boundaries_use_distinct_epochs():
    c, _ = compile_pair(knill_source(), knill_operations(), count=3, noise=special())
    bs = c.resource_preparation_boundaries
    assert len(bs) == 6
    assert len({b.block_use_id for b in bs}) == 6
    assert len({b.bell_preparation_id for b in bs}) == 3
    assert [b.block_use_id.epoch for b in bs] == [0, 0, 1, 1, 1, 2]


@pytest.mark.parametrize("bad", ["children", "missing_use", "duplicate_use", "missing_record"])
def test_reject_ambiguous_resource_metadata(bad):
    compiler = make_compiler()
    c = compiler.compile([BellStatePrep("A", "B", 1)], allow_open_outputs=True)
    if bad == "children":
        c = replace(c, composites=(replace(c.composites[0], child_operation_ids=()),))
    elif bad in ("missing_use", "duplicate_use"):
        fs = list(c.fragments)
        fs[0] = replace(fs[0], block_use_ids=() if bad == "missing_use" else fs[1].block_use_ids)
        c = replace(c, fragments=tuple(fs))
    else:
        c = replace(c, measurements=())
    with pytest.raises(ValueError):
        resolve_resource_preparation_boundaries(c, {b.block_id: b for b in compiler.blocks})


def assert_exact_policy_locations(c, model, resource_logicals):
    """Independent location oracle from authored operand roles and physical moments."""
    from collections import Counter

    from logical_to_stim_converter.compiler._parallel import moments
    from tests.test_clifford_noise import fault_counter

    fs = {f.module_id: f for f in c.fragments}
    resources = {f.module_id for f in c.fragments
                 if f.operation_type == "LogicalInit" and f.logical_id in resource_logicals}
    spans = {}
    for layer, instructions in enumerate(moments(c.ideal_circuit)):
        for inst in instructions:
            if inst.tag in resources:
                spans.setdefault(inst.tag, []).append(layer)
    suppressed = {fs[m].block_use_ids[0]: (min(ls), max(ls)) for m, ls in spans.items()}
    expected = Counter()
    for layer, instructions in enumerate(moments(c.ideal_circuit)):
        for inst in instructions:
            if inst.tag not in fs:
                continue
            f = fs[inst.tag]
            p = model.resolve(f.operation_type, f.noise)
            ts = [t.value for t in inst.targets_copy()]
            if inst.name in ("M", "MX"):
                actual = [i for i in c.circuit if i.tag == inst.tag and i.name == inst.name]
                probability = 0 if inst.tag in resources else p.measurement
                assert all(i.gate_args_copy() == ([probability] if probability else [])
                           for i in actual)
            elif inst.tag not in resources:
                width = 2 if inst.name == "CX" else 1
                if inst.name == "CX":
                    channel, probability = "DEPOLARIZE2", p.two_qubit
                elif inst.name in ("R", "RX"):
                    channel = "X_ERROR" if inst.name == "R" else "Z_ERROR"
                    probability = p.reset
                else:
                    channel, probability = "DEPOLARIZE1", p.one_qubit
                for offset in range(0, len(ts), width):
                    if probability:
                        expected[layer, channel, tuple(ts[offset:offset+width]), probability] += 1
        info = c.time_layers[layer]
        for use in info.active_use_ids:
            interval = suppressed.get(use)
            if interval is not None and interval[0] <= layer <= interval[1]:
                continue
            module = info.operation_by_block.get(use.block_id)
            p = (model.resolve(fs[module].operation_type, fs[module].noise)
                 if module else model.default)
            sites = {v for (b, _), v in c.physical_qubit_map.items() if b == use.block_id}
            for q in sites - info.used_qubits:
                if p.idle:
                    expected[layer, "DEPOLARIZE1", (q,), p.idle] += 1
    for module, layers in spans.items():
        f = fs[module]
        # Physical data IDs are independently read from the registered layout.
        block = next(b for b in c._compiler.blocks if b.block_id == f.block_id)
        for q in block.layout.data_ids:
            if model.resource_preparation.p_st_transversal:
                expected[max(layers)+1, "DEPOLARIZE1", (c.physical_qubit_map[f.block_id, q],),
                         model.resource_preparation.p_st_transversal] += 1
    assert fault_counter(c.circuit) == expected
    assert c.circuit.without_noise() == c.ideal_circuit
    assert c.circuit.num_ticks == c.ideal_circuit.num_ticks


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("full_rounds", [False, True])
def test_exact_gate_idle_and_post_se_channels(distance, basis, full_rounds):
    from logical_to_stim_converter import NoiseOverride, NoiseParameters

    model = special(.013, default=NoiseParameters(.001, .002, .003, .004, .005),
                    operation_overrides={"LogicalInit": NoiseOverride(reset=.006, idle=.007)})
    ops = [LogicalInit("D", basis, 1),
           KnillEC("D", "A", "B", rounds=distance if full_rounds else 1,
                   noise=NoiseOverride(.021, .022, .023, .024, .025)),
           LogicalMeasure("D", basis)]
    c = make_compiler(distance).compile(ops, noise_model=model)
    baseline = make_compiler(distance).compile(ops, noise_model=NoiseModel(
        model.default, model.operation_overrides))
    assert c.ideal_circuit == baseline.ideal_circuit
    assert c.measurements == baseline.measurements and c.detectors == baseline.detectors
    assert c.observables == baseline.observables and c.time_layers == baseline.time_layers
    assert_exact_policy_locations(c, model, {"A", "B"})
    for b in c.resource_preparation_boundaries:
        channel = c.circuit[b.channel_instruction]
        assert channel.name == "DEPOLARIZE1" and channel.tag == b.channel_tag
        assert len(channel.targets_copy()) == distance**2
        assert channel.gate_args_copy() == [.013]
        assert b.channel_instruction < next(i for i, inst in enumerate(c.circuit)
                                             if inst.tag == b.resource_entangling_module_id)
    c.circuit.detector_error_model()


@pytest.mark.parametrize("p", [0, .019, 1])
def test_explicit_preparation_waiting_spectator_and_probability_extremes(p):
    import numpy as np

    from logical_to_stim_converter import NoiseParameters, SyndromeExtraction
    from tests.test_epoch_views_noise import placed_compiler

    compiler = placed_compiler(3, 4, {"D": "P0", "A": "P1", "B": "P2", "S": "P3"})
    model = special(p, default=NoiseParameters(.001, .002, .003, .004, .005))
    c = compiler.compile([
        [LogicalInit("D", "X", 1), LogicalInit("S", "Z", 1)],
        [BellStatePrep("A", "B", 1), SyndromeExtraction("S", 4)],
        SyndromeExtraction("S", 1),  # A/B now wait under ordinary idle noise.
        KnillEC("D", "A", "B", prepare_resource=False),
        [LogicalMeasure("D", "X"), LogicalMeasure("S", "Z")],
    ], noise_model=model)
    assert_exact_policy_locations(c, model, {"A", "B"})
    channels = [i for i in c.circuit if i.tag in
                {b.channel_tag for b in c.resource_preparation_boundaries}]
    assert len(channels) == (2 if p else 0)
    assert len(c.resource_preparation_boundaries) == 2
    np.testing.assert_array_equal(c.circuit.compile_sampler(seed=91).sample(32),
                                  c.circuit.compile_sampler(seed=91).sample(32))
    if p > .75:
        with pytest.raises(ValueError, match="over-mixing"):
            c.circuit.detector_error_model()
    else:
        c.circuit.detector_error_model()


def test_simultaneous_bell_preparations_are_injected_once_each():
    from tests.test_epoch_views_noise import placed_compiler

    compiler = placed_compiler(3, 4, {"A": "P0", "B": "P1", "C": "P2", "E": "P3"})
    c = compiler.compile([[BellStatePrep("A", "B", 1), BellStatePrep("C", "E", 1)]],
                         noise_model=special(.02), allow_open_outputs=True)
    bs = c.resource_preparation_boundaries
    assert len(bs) == 4 and len({b.ideal_boundary_instruction for b in bs}) == 1
    assert len({b.channel_instruction for b in bs}) == 4
    assert sum(len(c.circuit[b.channel_instruction].targets_copy()) for b in bs) == 36
    assert_exact_policy_locations(c, special(.02), {"A", "B", "C", "E"})


def test_disabled_mode_is_exact_original_injector_and_append_retains_policy():
    from logical_to_stim_converter import NoiseInjector

    ops = [LogicalInit("D", "Z", 1), KnillEC("D", "A", "B", rounds=1)]
    compiler = make_compiler()
    baseline = NoiseModel.uniform_depolarizing(.001)
    disabled = replace(baseline, resource_preparation=ResourcePreparationNoise(False, .9))
    c = compiler.compile(ops, noise_model=disabled, allow_open_outputs=True)
    reference = compiler.compile(ops, noise_model=baseline, allow_open_outputs=True)
    assert c.circuit == reference.circuit
    assert c.circuit.detector_error_model() == reference.circuit.detector_error_model()
    assert not c.resource_preparation_boundaries
    assert c.circuit == NoiseInjector().apply(
        c.ideal_circuit, model=baseline, physical_map=c.physical_qubit_map,
        layers=c.time_layers, fragments=c.fragments)
    model = special(.03)
    opened = compiler.compile(ops, noise_model=model, allow_open_outputs=True)
    continued = opened.append([LogicalMeasure("D", "Z")])
    direct = compiler.compile([*ops, LogicalMeasure("D", "Z")], noise_model=model)
    assert continued.circuit == direct.circuit
    assert continued.resource_preparation_boundaries == direct.resource_preparation_boundaries


def original_noise_reference(c, model):
    """Independent direct Stim spelling of the M1-M8 rule and idle schedule."""
    import stim

    fs = {f.module_id: f for f in c.fragments}
    result, layer = stim.Circuit(), 0

    def idles(index):
        info = c.time_layers[index]
        for use in info.active_use_ids:
            module = info.operation_by_block.get(use.block_id)
            rule = (model.resolve(fs[module].operation_type, fs[module].noise)
                    if module else model.default)
            sites = {i for (b, _), i in c.physical_qubit_map.items() if b == use.block_id}
            targets = sorted(sites - info.used_qubits)
            if rule.idle and targets:
                result.append("DEPOLARIZE1", targets, rule.idle)

    for inst in c.ideal_circuit:
        if inst.name == "TICK":
            idles(layer)
            result.append(inst)
            layer += 1
        elif inst.tag not in fs:
            result.append(inst)
        else:
            f = fs[inst.tag]
            rule = model.resolve(f.operation_type, f.noise)
            if inst.name in ("M", "MX"):
                result.append(inst.name, inst.targets_copy(), rule.measurement, tag=inst.tag)
                continue
            result.append(inst)
            if inst.name in ("R", "RX"):
                channel = "X_ERROR" if inst.name == "R" else "Z_ERROR"
                p = rule.reset
            elif inst.name == "CX":
                channel, p = "DEPOLARIZE2", rule.two_qubit
            else:
                channel, p = "DEPOLARIZE1", rule.one_qubit
            if p:
                result.append(channel, inst.targets_copy(), p)
    idles(layer)
    return result


@pytest.mark.parametrize("distance", [3, 5])
def test_disabled_circuit_dem_and_identity_match_independent_original_rules(distance):
    from logical_to_stim_converter import NoiseOverride, NoiseParameters
    from logical_to_stim_converter.decoding.views import source_fingerprint

    model = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005),
                       {"LogicalInit": NoiseOverride(reset=.007),
                        "TransversalCNOT": NoiseOverride(two_qubit=.008)},
                       ResourcePreparationNoise(False, .123))
    c = make_compiler(distance).compile([
        LogicalInit("D", "Z", 1), KnillEC("D", "A", "B", rounds=1), LogicalMeasure("D", "Z")
    ], noise_model=model)
    expected = original_noise_reference(c, model)
    assert expected == c.circuit
    assert expected.detector_error_model() == c.circuit.detector_error_model()
    restored = replace(c, _noise_model=replace(
        model, resource_preparation=ResourcePreparationNoise()))
    assert source_fingerprint(c) == source_fingerprint(restored)
    assert not c.resource_preparation_boundaries
