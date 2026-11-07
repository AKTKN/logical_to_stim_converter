"""Independent sampling, record parity, distance, placement, and concurrency checks."""

from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter.backends.surface_code import RotatedSurfaceCodeBackend
from logical_to_stim_converter.compiler.circuit_compiler import CircuitCompiler
from logical_to_stim_converter.core.code_spec import CodeSpec
from logical_to_stim_converter.core.compiler_context import BlockStatus
from logical_to_stim_converter.core.logical_block import LogicalBlock
from logical_to_stim_converter.noise.model import NoiseModel
from logical_to_stim_converter.operations.initialization import LogicalInit
from logical_to_stim_converter.operations.measurement import LogicalMeasure
from logical_to_stim_converter.operations.syndrome_extraction import SyndromeExtraction


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("bases", [("Z",), ("X",), ("Z", "Z"), ("Z", "X"), ("Z", "X", "Z")])
@pytest.mark.parametrize("rounds", [1, 3, 5])
def test_memories(memory, d, bases, rounds):
    compiled = memory(d=d, bases=bases, rounds=rounds)
    ideal = compiled.ideal_circuit
    count = len(bases)
    total_rounds = rounds + 1  # LogicalInit has its own first SE round.
    assert ideal.num_qubits == count * (2 * d * d - 1)
    assert ideal.num_measurements == count * (total_rounds * (d * d - 1) + d * d)
    assert ideal.num_detectors == count * total_rounds * (d * d - 1)
    assert ideal.num_observables == count
    assert len(compiled.physical_qubit_map) == ideal.num_qubits
    assert len(set(compiled.physical_qubit_map.values())) == ideal.num_qubits
    assert len(compiled.time_layers) == ideal.num_ticks + 1 == 6 * total_rounds + 2
    assert len(compiled.measurements) == ideal.num_measurements
    assert len(compiled.detectors) == ideal.num_detectors
    ideal.detector_error_model()
    dets, obs = ideal.compile_detector_sampler(seed=99).sample(64, separate_observables=True)
    assert not dets.any()
    assert not obs.any()
    raw = ideal.compile_sampler(seed=15).sample(64)
    lookup = {m.key: m for m in compiled.measurements}
    for detector in compiled.detectors:
        assert not np.bitwise_xor.reduce(raw[:, detector.measurement_indices], axis=1).any()
        assert {key.block_id for key in detector.measurement_keys} == {detector.block_id}
        basis = bases[int(detector.block_id.removeprefix("physical"))]
        if len(detector.measurement_keys) == 1:
            record = lookup[detector.measurement_keys[0]]
            assert record.basis == basis and record.key.round_index == 0
        elif all(key.kind == "syndrome" for key in detector.measurement_keys):
            a, b = detector.measurement_keys
            assert a.local_id == b.local_id == detector.check_id
            assert abs(a.round_index - b.round_index) == 1
        else:
            data = [key.local_id for key in detector.measurement_keys if key.kind == "readout"]
            block = LogicalBlock.placed("unused", CodeSpec.rotated_surface(d))
            assert set(data) == set(block.layout.check_for_ancilla(detector.check_id).support)
    assert Counter(len(info.measurement_keys) == 1 for info in compiled.detectors)[True] == (
        count * (d * d - 1) // 2
    )
    for info in compiled.observables:
        assert info.logical_id == f"logical{info.index}"
        # Explicit geometry: logical X is the southern row, Z the western column.
        columns = range(0, d * d, d) if info.basis == "X" else range(d)
        expected_data = {f"D{i + 1}" for i in columns}
        actual = {compiled.measurements[i].key.local_id for i in info.measurement_indices}
        assert actual == expected_data
        assert {compiled.measurements[i].key.block_id for i in info.measurement_indices} == {
            info.block_id
        }
        assert not np.bitwise_xor.reduce(raw[:, info.measurement_indices], axis=1).any()
    assert all(state == BlockStatus.MEASURED for state in compiled.block_status.values())
    for logical, frame in compiled.frames.items():
        assert frame.x_terms == frame.z_terms == ()
        assert len(frame.preparation_syndromes) == (d * d - 1) // 2
        assert all(
            lookup[key].basis != bases[int(logical.removeprefix("logical"))]
            for key in frame.preparation_syndromes
        )
    # Reconstruct record parities independently using Stim's measurement converter.
    converted_dets, converted_obs = ideal.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    assert not converted_dets.any() and not converted_obs.any()


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_circuit_distance(memory, d, basis):
    compiled = memory(
        d=d, bases=(basis,), rounds=d - 1, noise_model=NoiseModel.uniform_depolarizing(0.001)
    )
    # Independent fault search catches a distance-reducing hook/CNOT schedule.
    assert len(compiled.circuit.shortest_graphlike_error()) == d
    reference = stim.Circuit.generated(
        "surface_code:rotated_memory_" + basis.lower(),
        distance=d,
        rounds=d,
        after_clifford_depolarization=0.001,
        before_measure_flip_probability=0.001,
    )
    assert len(reference.shortest_graphlike_error()) == d


def test_placement_reindexing_and_reproducibility(memory):
    first = memory(bases=("Z", "X", "Z"), rounds=3)
    reverse = memory(bases=("Z", "X", "Z"), rounds=3, reverse=True)
    assert first.ideal_circuit == reverse.ideal_circuit
    assert first.physical_qubit_map == reverse.physical_qubit_map
    assert first.observables == reverse.observables
    positions = first.ideal_circuit.get_final_qubit_coordinates()
    for (block_id, local), index in first.physical_qubit_map.items():
        patch = int(block_id.removeprefix("physical"))
        block = LogicalBlock.placed(block_id, CodeSpec.rotated_surface(3), patch_index=patch)
        assert complex(*positions[index]) == block.position(local)
        assert block.local_site(block.global_site(local)) == local
    # Local builder indices differ from final Stim indices even for a single patch.
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(3))
    chunk = RotatedSurfaceCodeBackend().initialization(block, "q", "Z")
    single = CircuitCompiler([block], logical_to_block={"q": "p"}).compile(
        [LogicalInit("q", "Z", 1), LogicalMeasure("q", "Z")]
    )
    assert any(
        chunk.q2i[block.position(local)] != single.physical_qubit_map[("p", local)]
        for local in block.layout.data_ids
    )
    i2block = {index: block for (block, _), index in first.physical_qubit_map.items()}
    for instruction in first.ideal_circuit:
        if instruction.name == "CX":
            ts = instruction.targets_copy()
            assert all(
                i2block[a.value] == i2block[b.value] for a, b in zip(ts[::2], ts[1::2], strict=True)
            )


def test_bad_placement_and_layout():
    code = CodeSpec.rotated_surface(3)
    a = LogicalBlock.placed("a", code)
    with pytest.raises(ValueError, match="overlapping"):
        CircuitCompiler([a, replace(a, block_id="b")])
    with pytest.raises(ValueError, match="distinct"):
        CircuitCompiler([a, a])
    with pytest.raises(KeyError):
        a.local_site(("different-block", "D1"))
    layout = a.layout
    with pytest.raises(ValueError):
        replace(layout, cnot_layers=(layout.cnot_layers[0] * 2, *layout.cnot_layers[1:]))
    with pytest.raises(ValueError, match="order"):
        replace(layout, cnot_layers=tuple(reversed(layout.cnot_layers)))
    with pytest.raises(ValueError, match="coordinate"):
        replace(layout, coordinates={**layout.coordinates, "D1": layout.coordinates["D2"]})


@pytest.mark.parametrize(
    "ops",
    [
        [SyndromeExtraction("q", 1)],
        [LogicalMeasure("q", "Z")],
        [LogicalInit("q", "Z", 1), LogicalInit("q", "Z", 1)],
        [LogicalInit("q", "Z", 1), LogicalMeasure("q", "Z"), SyndromeExtraction("q", 1)],
        [LogicalInit("q", "Z", 1), LogicalMeasure("q", "X")],
        [LogicalInit("q", "Z", 1)],
        [LogicalInit("unknown", "Z", 1)],
        [[LogicalInit("q", "Z", 1), LogicalInit("q", "Z", 1)]],
    ],
)
def test_lifecycle_rejections(ops):
    block = LogicalBlock.placed("block", CodeSpec.rotated_surface(3))
    with pytest.raises(ValueError):
        CircuitCompiler([block], logical_to_block={"q": "block"}).compile(ops)


@pytest.mark.parametrize("rounds", [0, -1, True, 1.5])
def test_operation_arguments(rounds):
    with pytest.raises(ValueError):
        LogicalInit("q", "Z", rounds)
    with pytest.raises(ValueError):
        SyndromeExtraction("q", rounds)
    with pytest.raises(ValueError):
        LogicalMeasure("q", "Y")
    with pytest.raises(ValueError):
        SyndromeExtraction(("q", "q"), 1)


def test_different_round_counts_and_sequential_waiting():
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed(name, code, patch_index=i) for i, name in enumerate(["a", "b"])]
    compiler = CircuitCompiler(blocks)
    result = compiler.compile(
        [
            [LogicalInit("a", "Z", 1), LogicalInit("b", "X", 2)],
            SyndromeExtraction("a", 2),
            [LogicalMeasure("a", "Z"), LogicalMeasure("b", "X")],
        ]
    )
    assert result.ideal_circuit.num_detectors == 8 * (3 + 2)
    assert result.ideal_circuit.num_ticks + 1 == 2 + 6 * (2 + 2)
    dets, obs = result.circuit.compile_detector_sampler(seed=3).sample(
        100, separate_observables=True
    )
    assert not dets.any() and not obs.any()
    again = compiler.compile([LogicalInit(("a", "b"), "Z", 1), LogicalMeasure(("a", "b"), "Z")])
    assert again.ideal_circuit.num_detectors == 16


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_random_preparation_syndrome_cannot_be_a_detector(memory, basis):
    compiled = memory(bases=(basis,))
    key = compiled.frames["logical0"].preparation_syndromes[0]
    record = next(m for m in compiled.measurements if m.key == key)
    bad = compiled.ideal_circuit.copy()
    bad.append("DETECTOR", [stim.target_rec(record.index - bad.num_measurements)])
    with pytest.raises(ValueError, match="non-deterministic detectors"):
        bad.detector_error_model()


def test_mixed_phase_parallel_layer():
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed(name, code, patch_index=i) for i, name in enumerate(["a", "b"])]
    compiler = CircuitCompiler(blocks)
    compiled = compiler.compile(
        [
            LogicalInit("a", "Z", 1),
            [LogicalMeasure("a", "Z"), LogicalInit("b", "X", 1)],
            LogicalMeasure("b", "X"),
        ],
        noise_model=NoiseModel.uniform_depolarizing(0.001),
    )
    assert compiled.ideal_circuit.num_ticks + 1 == 15
    assert compiled.time_layers[7].active_blocks == ("a", "b")
    assert compiled.time_layers[8].active_blocks == ("b",)
    assert len(compiled.fragments) == 4
    assert sum(len(f.measurement_records) for f in compiled.fragments) == len(compiled.measurements)
    for fragment in compiled.fragments:
        assert all(
            record.module_id == fragment.module_id for record in fragment.measurement_records
        )
        if fragment.operation_type == "LogicalInit":
            assert fragment.input_logicals == ()
        if fragment.operation_type == "LogicalMeasure":
            assert fragment.output_logicals == ()
    dets, obs = compiled.ideal_circuit.compile_detector_sampler(seed=33).sample(
        32, separate_observables=True
    )
    assert not dets.any() and not obs.any()


def test_user_ids_and_empty_layers():
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(3))
    compiler = CircuitCompiler([block], logical_to_block={"q": "p"})
    for operations in [
        [[]],
        [[object()]],
        [
            LogicalInit("q", "Z", 1, operation_id="same"),
            LogicalMeasure("q", "Z", operation_id="same"),
        ],
    ]:
        with pytest.raises(ValueError):
            compiler.compile(operations)
    with pytest.raises(ValueError):
        CircuitCompiler([block], logical_to_block={"q": "missing"})
