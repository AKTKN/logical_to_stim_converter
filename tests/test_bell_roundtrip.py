"""Actual-physical Bell stabilizers, raw round-trip readout, and correlated faults."""

import numpy as np
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
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)


def bell_program(rounds):
    return [
        LogicalInit(("A", "B"), "Z", 1),
        TransversalH("A"),
        TransversalCNOT("A", "B"),
        SyndromeExtraction(("A", "B"), rounds),
        TransversalCNOT("A", "B"),
        TransversalH("A"),
        LogicalMeasure(("A", "B"), "Z"),
    ]


def bell_blocks(d):
    code = CodeSpec.rotated_surface(d)
    return [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate(("A", "B"))]


def physical_logical(compiled, block, axis, d, orientation):
    if axis == "X":
        columns = range(d) if orientation else range(0, d * d, d)
    else:
        columns = range(d - 1, d * d, d) if orientation else range(d)
    result = stim.PauliString(compiled.ideal_circuit.num_qubits)
    for column in columns:
        result[compiled.physical_qubit_map[(block, f"D{column + 1}")]] = axis
    return result


@pytest.mark.parametrize("d,rounds", [(3, 1), (3, 3), (5, 1), (5, 5)])
def test_bell_roundtrip_and_intermediate_state(d, rounds):
    blocks = bell_blocks(d)
    result = CircuitCompiler(blocks).compile(
        bell_program(rounds), noise_model=NoiseModel.uniform_depolarizing(0.001)
    )
    assert result.orientations == {"A": 0, "B": 0}
    assert result.ideal_circuit.num_ticks + 1 == 6 * (rounds + 1) + 6
    assert result.ideal_circuit.num_detectors == 2 * (d * d - 1) * (rounds + 1)
    assert len([f for f in result.fragments if f.operation_type == "TransversalCNOT"]) == 2
    for fragment in result.fragments:
        fragment.verify()
    first = next(f for f in result.fragments if f.operation_type == "TransversalCNOT")
    assert first.logical_ids == ("A", "B")
    assert first.orientations_before == (1, 0)
    for seed in (17, 53):
        simulator = stim.TableauSimulator(seed=seed)
        for instruction in result.ideal_circuit:
            simulator.do(instruction)
            if instruction.tag == first.module_id:
                break
        for axis in "XZ":
            a = physical_logical(result, "A", axis, d, 1)
            b = physical_logical(result, "B", axis, d, 0)
            assert simulator.peek_observable_expectation(a * b) == 1
            assert simulator.peek_observable_expectation(a) == 0
            assert simulator.peek_observable_expectation(b) == 0
    raw = result.ideal_circuit.compile_sampler(seed=25).sample(64)
    for block in ("A", "B"):
        # Direct original-frame logical Z, independent of exported observable definitions.
        indices = [
            m.index
            for m in result.measurements
            if m.key.block_id == block
            and m.key.kind == "readout"
            and m.key.local_id in {f"D{i + 1}" for i in range(d)}
        ]
        assert len(indices) == d
        assert not np.bitwise_xor.reduce(raw[:, indices], axis=1).any()
    assert not result.interpreted_measurements(raw).any()
    cross = [det for det in result.detectors if len(det.supporting_block_ids) > 1]
    assert cross
    for detector in result.detectors:
        assert not np.bitwise_xor.reduce(raw[:, detector.measurement_indices], axis=1).any()
        assert detector.anchor_block_id in detector.supporting_block_ids
        assert detector.anchor_check_id in {
            c.check_id for c in blocks[0 if detector.anchor_block_id == "A" else 1].layout.checks
        }
    result.ideal_circuit.detector_error_model()
    result.circuit.detector_error_model()
    a = result.circuit.compile_detector_sampler(seed=12).sample(64, append_observables=True)
    b = result.circuit.compile_detector_sampler(seed=12).sample(64, append_observables=True)
    assert np.array_equal(a, b)
    assert result.circuit.without_noise() == result.ideal_circuit


def test_cnot_fault_correlations():
    noise = NoiseModel(operation_overrides={"TransversalCNOT": NoiseOverride(two_qubit=0.01)})
    result = CircuitCompiler(bell_blocks(3)).compile(bell_program(1), noise_model=noise)
    dem = result.circuit.detector_error_model().flattened()
    correlated = []
    for instruction in dem:
        if instruction.type != "error":
            continue
        anchors = {
            result.detectors[t.val].anchor_block_id
            for t in instruction.targets_copy()
            if t.is_relative_detector_id()
        }
        if anchors == {"A", "B"}:
            correlated.append(instruction)
    assert correlated
    # Only the two actual transversal CNOT layers are noisy in this model.
    fault_pairs = sum(len(i.targets_copy()) // 2 for i in result.circuit if i.name == "DEPOLARIZE2")
    assert fault_pairs == 18


def test_corrupted_cross_block_annotation_is_physics_failure():
    result = CircuitCompiler(bell_blocks(3)).compile(bell_program(1))
    cross = next(d for d in result.detectors if len(d.supporting_block_ids) == 2)
    changed = stim.Circuit()
    detector_index = 0
    for instruction in result.ideal_circuit:
        if instruction.name == "DETECTOR":
            if detector_index == cross.index:
                targets = instruction.targets_copy()
                # A real, earlier raw record from a different check is still a valid
                # Stim target; it breaks the physical parity relation.
                targets[0] = stim.target_rec(targets[0].value - 1)
                changed.append(
                    "DETECTOR", targets, instruction.gate_args_copy(), tag=instruction.tag
                )
                detector_index += 1
                continue
            detector_index += 1
        changed.append(instruction)
    with pytest.raises(ValueError, match="non-deterministic detectors"):
        changed.detector_error_model()
