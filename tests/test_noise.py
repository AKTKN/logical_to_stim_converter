"""Exact fault-location counts and precedence, without statistical thresholds."""

from collections import Counter

import pytest
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    NoiseOverride,
    NoiseParameters,
    SyndromeExtraction,
)
from logical_to_stim_converter.compiler._parallel import moments


def channel_locations(circuit):
    locations = Counter()
    for layer, instructions in enumerate(moments(circuit)):
        for inst in instructions:
            if inst.name not in ("DEPOLARIZE1", "DEPOLARIZE2", "X_ERROR", "Z_ERROR"):
                continue
            targets = [t.value for t in inst.targets_copy()]
            size = 2 if inst.name == "DEPOLARIZE2" else 1
            for k in range(0, len(targets), size):
                locations[
                    (layer, inst.name, tuple(targets[k : k + size]), inst.gate_args_copy()[0])
                ] += 1
    return locations


def assert_noise_locations(compiled, model):
    expected = Counter()
    fragments = {f.module_id: f for f in compiled.fragments}
    for layer_index, instructions in enumerate(moments(compiled.ideal_circuit)):
        used = set()
        params_by_block = {}
        for inst in instructions:
            if inst.tag not in fragments:
                continue
            fragment = fragments[inst.tag]
            params = model.resolve(fragment.operation_type, fragment.noise)
            params_by_block[fragment.block_id] = params
            targets = [t.value for t in inst.targets_copy()]
            used.update(targets)
            if inst.name in ("R", "RX"):
                channel, p = ("Z_ERROR" if inst.name == "RX" else "X_ERROR"), params.reset
                for target in targets:
                    if p:
                        expected[(layer_index, channel, (target,), p)] += 1
            if inst.name == "CX" and params.two_qubit:
                for a, b in zip(targets[::2], targets[1::2], strict=True):
                    expected[(layer_index, "DEPOLARIZE2", (a, b), params.two_qubit)] += 1
        for block in compiled.time_layers[layer_index].active_blocks:
            params = params_by_block.get(block, model.default)
            indices = {
                index for (bid, _), index in compiled.physical_qubit_map.items() if bid == block
            }
            for index in indices - used:
                if params.idle:
                    expected[(layer_index, "DEPOLARIZE1", (index,), params.idle)] += 1
    assert channel_locations(compiled.circuit) == expected
    # Adding gate/idle noise must preserve all raw-record annotation targets.
    assert compiled.circuit.without_noise() == compiled.ideal_circuit
    ideal_ms = [i for i in compiled.ideal_circuit if i.name in ("M", "MX")]
    noisy_ms = [i for i in compiled.circuit if i.name in ("M", "MX")]
    for ideal, noisy in zip(ideal_ms, noisy_ms, strict=True):
        fragment = fragments[ideal.tag]
        p = model.resolve(fragment.operation_type, fragment.noise).measurement
        assert noisy.gate_args_copy() == ([p] if p else [])
        assert noisy.targets_copy() == ideal.targets_copy()
    assert compiled.circuit.num_measurements == compiled.ideal_circuit.num_measurements
    assert compiled.circuit.num_detectors == compiled.ideal_circuit.num_detectors
    assert compiled.circuit.num_observables == compiled.ideal_circuit.num_observables


@pytest.mark.parametrize("bases", [("Z",), ("Z", "X"), ("X", "Z", "X")])
def test_exact_fault_locations(memory, bases):
    model = NoiseModel(
        NoiseParameters(reset=0.01, one_qubit=0.02, two_qubit=0.03, measurement=0.04, idle=0.05)
    )
    compiled = memory(bases=bases, rounds=2, noise_model=model)
    assert_noise_locations(compiled, model)
    compiled.circuit.detector_error_model()
    a = compiled.circuit.compile_detector_sampler(seed=8).sample(32, append_observables=True)
    b = compiled.circuit.compile_detector_sampler(seed=8).sample(32, append_observables=True)
    assert (a == b).all()


def test_zero_noise_equivalence(memory):
    compiled = memory(bases=("Z", "X"), noise_model=NoiseModel())
    assert compiled.noisy_circuit == compiled.ideal_circuit
    assert not channel_locations(compiled.circuit)
    noiseless = memory(bases=("Z", "X"))
    assert noiseless.noisy_circuit is None
    assert noiseless.ideal_circuit == compiled.ideal_circuit


def test_primitive_and_instance_overrides():
    model = NoiseModel(
        NoiseParameters(reset=0.01, two_qubit=0.02, measurement=0.03, idle=0.04),
        {
            "LogicalInit": NoiseOverride(two_qubit=0.05, reset=0.06),
            "SyndromeExtraction": NoiseOverride(two_qubit=0.07, idle=0.08),
            "LogicalMeasure": NoiseOverride(measurement=0.09),
        },
    )
    assert model.resolve("LogicalInit").two_qubit == 0.05
    assert model.resolve("LogicalInit").measurement == 0.03
    assert model.resolve("LogicalInit", NoiseOverride(two_qubit=0)).two_qubit == 0
    blocks = [
        LogicalBlock.placed(name, CodeSpec.rotated_surface(3), patch_index=i)
        for i, name in enumerate(["a", "b"])
    ]
    compiled = CircuitCompiler(blocks).compile(
        [
            [
                LogicalInit("a", "Z", 1, noise=NoiseOverride(two_qubit=0.1)),
                LogicalInit("b", "X", 1),
            ],
            [
                SyndromeExtraction("a", 1, noise=NoiseOverride(reset=0, idle=0)),
                SyndromeExtraction("b", 1),
            ],
            [
                LogicalMeasure("a", "Z", noise=NoiseOverride(measurement=0)),
                LogicalMeasure("b", "X"),
            ],
        ],
        noise_model=model,
    )
    assert_noise_locations(compiled, model)
    assert {key[3] for key in channel_locations(compiled.circuit) if key[1] == "DEPOLARIZE2"} == {
        0.1,
        0.05,
        0.07,
    }


def test_waiting_and_retired_blocks():
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed(name, code, patch_index=i) for i, name in enumerate(["a", "b"])]
    model = NoiseModel(
        NoiseParameters(idle=0.012), {"SyndromeExtraction": NoiseOverride(idle=0.025)}
    )
    compiled = CircuitCompiler(blocks).compile(
        [
            LogicalInit("a", "Z", 1),
            LogicalInit("b", "X", 1),
            LogicalMeasure("a", "Z"),
            SyndromeExtraction("b", 1),
            LogicalMeasure("b", "X"),
        ],
        noise_model=model,
    )
    assert_noise_locations(compiled, model)
    a_indices = {index for (block, _), index in compiled.physical_qubit_map.items() if block == "a"}
    assert compiled.time_layers[0].active_blocks == ("a",)
    assert compiled.time_layers[7].active_blocks == ("a", "b")
    assert all(layer.active_blocks == ("b",) for layer in compiled.time_layers[15:])
    # The waiting block receives exactly global idle, independently of b's SE override.
    idle = channel_locations(compiled.circuit)
    for layer in compiled.time_layers:
        if layer.index >= 15:
            assert not any(k[0] == layer.index and set(k[2]) & a_indices for k in idle)


def test_single_qubit_rule_and_probability_validation():
    model = NoiseParameters(one_qubit=0.1).to_stimflow()
    noisy = model.noisy_circuit(stim.Circuit("H 0"))
    assert str(noisy) == "H 0\nDEPOLARIZE1(0.1) 0"
    for p in [-0.1, 1.1, float("nan"), float("inf"), True]:
        with pytest.raises(ValueError):
            NoiseParameters(idle=p)
    with pytest.raises(ValueError):
        NoiseParameters(reset=None)
    with pytest.raises(ValueError):
        NoiseModel(operation_overrides={"KnillEC": NoiseOverride()})


def test_no_reinjection(memory):
    from logical_to_stim_converter import NoiseInjector

    compiled = memory(noise_model=NoiseModel.uniform_depolarizing(0.001))
    with pytest.raises(ValueError, match="once"):
        NoiseInjector().apply(
            compiled.noisy_circuit,
            model=NoiseModel(),
            physical_map=compiled.physical_qubit_map,
            layers=compiled.time_layers,
            fragments=compiled.fragments,
        )
