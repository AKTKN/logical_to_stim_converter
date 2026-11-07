"""Exact primitive and global idle faults inside the Knill composite."""

from collections import Counter

import numpy as np
import pytest

from logical_to_stim_converter import (
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    NoiseOverride,
    NoiseParameters,
    TransversalCNOT,
)
from logical_to_stim_converter.compiler._parallel import moments
from tests.helpers.knill_physics import make_compiler
from tests.test_bell_state_preparation import physical_circuit
from tests.test_clifford_noise import fault_counter


@pytest.mark.parametrize("d", [3, 5])
def test_exact_knill_noise_locations_and_seeded_sampling(d):
    model = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005), {
        "LogicalInit": NoiseOverride(reset=.006, two_qubit=.007),
        "TransversalCNOT": NoiseOverride(two_qubit=.008),
        "LogicalMeasure": NoiseOverride(measurement=.009),
    })
    compiler = make_compiler(d)
    result = compiler.compile([LogicalInit("D", "Z", 1), KnillEC("D", "A", "B"),
                               LogicalPauli("D", "Z", mode="frame"),
                               LogicalMeasure("D", "Z")], noise_model=model)
    expected = Counter()
    modules = {f.module_id: f for f in result.fragments}
    active = set()
    two_block_pair_count = Counter()
    for layer, instructions in enumerate(moments(result.ideal_circuit)):
        used, retiring, rules = set(), set(), {}
        for inst in instructions:
            if inst.tag not in modules:
                continue
            fragment = modules[inst.tag]
            rule = model.resolve(fragment.operation_type, fragment.noise)
            for bid in fragment.block_ids:
                rules[bid] = rule
            if fragment.operation_type == "LogicalInit":
                active.update(fragment.block_ids)
            elif fragment.operation_type == "LogicalMeasure":
                retiring.update(fragment.block_ids)
            targets = [t.value for t in inst.targets_copy()]
            used.update(targets)
            if inst.name in ("M", "MX"):
                noisy = [i for i in result.noisy_circuit
                         if i.tag == inst.tag and i.name == inst.name]
                assert all(i.gate_args_copy() == [rule.measurement] for i in noisy)
                continue
            width = 2 if inst.name == "CX" else 1
            if inst.name == "CX":
                name, p = "DEPOLARIZE2", rule.two_qubit
                if fragment.operation_type == "TransversalCNOT":
                    two_block_pair_count[fragment.module_id] += len(targets)//2
                    assert len(fragment.block_ids) == 2
            elif inst.name in ("R", "RX"):
                name, p = ("X_ERROR" if inst.name == "R" else "Z_ERROR"), rule.reset
            else:
                name, p = "DEPOLARIZE1", rule.one_qubit
            for offset in range(0, len(targets), width):
                if p:
                    expected[(layer, name, tuple(targets[offset:offset+width]), p)] += 1
        assert set(result.time_layers[layer].active_blocks) == active
        for bid in active:
            sites = {i for (b, _), i in result.physical_qubit_map.items() if b == bid}
            rule = rules.get(bid, model.default)
            for site in sites - used:
                expected[(layer, "DEPOLARIZE1", (site,), rule.idle)] += 1
        active -= retiring
    assert sorted(two_block_pair_count.values()) == [d*d, d*d]
    assert fault_counter(result.noisy_circuit) == expected
    assert all(not f.components for f in result.fragments if f.frame_transition == "frame")
    raw1 = result.noisy_circuit.compile_sampler(seed=24).sample(50)
    raw2 = result.noisy_circuit.compile_sampler(seed=24).sample(50)
    assert np.array_equal(raw1, raw2)
    result.noisy_circuit.detector_error_model()
    # Independently spelled-out primitives have identical physical fault sites.
    primitive = compiler.compile([LogicalInit("D", "Z", 1),
        [LogicalInit("A", "X", d), LogicalInit("B", "Z", d)], TransversalCNOT("A", "B"),
        TransversalCNOT("D", "A"), [LogicalMeasure("D", "X", mode="random"),
                                   LogicalMeasure("A", "Z", mode="random")],
        LogicalMeasure("B", "Z", mode="random")], noise_model=model)
    assert physical_circuit(result.noisy_circuit) == physical_circuit(primitive.noisy_circuit)


def test_zero_noise_and_composite_instance_override():
    result = make_compiler().compile([LogicalInit("D", "X", 1),
        KnillEC("D", "A", "B", noise=NoiseOverride(two_qubit=0)), LogicalMeasure("D", "X")],
        noise_model=NoiseModel(operation_overrides={
            "TransversalCNOT": NoiseOverride(two_qubit=.03)}))
    assert result.noisy_circuit == result.ideal_circuit
