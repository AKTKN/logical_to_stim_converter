"""Exact multi-block and single-qubit fault provenance, including virtual gates."""

from collections import Counter

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    NoiseOverride,
    NoiseParameters,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from logical_to_stim_converter.compiler._parallel import moments


def fault_counter(circuit):
    result = Counter()
    for layer, instructions in enumerate(moments(circuit)):
        for inst in instructions:
            if inst.name not in ("X_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"):
                continue
            targets = [t.value for t in inst.targets_copy()]
            width = 2 if inst.name == "DEPOLARIZE2" else 1
            for i in range(0, len(targets), width):
                result[
                    (layer, inst.name, tuple(targets[i : i + width]), inst.gate_args_copy()[0])
                ] += 1
    return result


def test_exact_clifford_noise_in_disjoint_parallel_operations():
    blocks = [
        LogicalBlock.placed(q, CodeSpec.rotated_surface(3), patch_index=i)
        for i, q in enumerate(("A", "B", "C"))
    ]
    noise = NoiseModel(
        NoiseParameters(
            reset=0.001, one_qubit=0.002, two_qubit=0.003, measurement=0.004, idle=0.005
        ),
        {
            "TransversalH": NoiseOverride(one_qubit=0.007),
            "TransversalCNOT": NoiseOverride(two_qubit=0.009),
            "LogicalPauli": NoiseOverride(one_qubit=0.011),
        },
    )
    program = [
        LogicalInit(("A", "B", "C"), "Z", 1),
        TransversalH("A"),
        [
            TransversalCNOT("A", "B", noise=NoiseOverride(two_qubit=0.01)),
            TransversalH("C", noise=NoiseOverride(one_qubit=0)),
        ],
        SyndromeExtraction(("A", "B", "C"), 1),
        [TransversalCNOT("A", "B"), TransversalH("C")],
        TransversalH("A"),
        LogicalPauli("A", "X"),
        LogicalPauli("B", "X", mode="frame", noise=NoiseOverride(one_qubit=0.99)),
        LogicalMeasure(("A", "B", "C"), "Z"),
    ]
    result = CircuitCompiler(blocks).compile(program, noise_model=noise)
    expected = Counter()
    by_module = {f.module_id: f for f in result.fragments}
    active = set()
    measurement_expected = []
    for layer_index, instructions in enumerate(moments(result.ideal_circuit)):
        used = set()
        rule_by_block = {}
        retiring = set()
        for inst in instructions:
            if inst.tag not in by_module:
                continue
            fragment = by_module[inst.tag]
            params = noise.resolve(fragment.operation_type, fragment.noise)
            for block in fragment.block_ids:
                rule_by_block[block] = params
            if fragment.operation_type == "LogicalInit":
                active.update(fragment.block_ids)
            if fragment.operation_type == "LogicalMeasure":
                retiring.update(fragment.block_ids)
            targets = [t.value for t in inst.targets_copy()]
            used.update(targets)
            if inst.name in ("M", "MX"):
                measurement_expected.append((inst.targets_copy(), params.measurement))
                continue
            if inst.name == "CX":
                name, probability, width = "DEPOLARIZE2", params.two_qubit, 2
            elif inst.name in ("H", "X", "Y", "Z"):
                name, probability, width = "DEPOLARIZE1", params.one_qubit, 1
            else:
                name = "Z_ERROR" if inst.name == "RX" else "X_ERROR"
                probability, width = params.reset, 1
            for index in range(0, len(targets), width):
                if probability:
                    expected[
                        (layer_index, name, tuple(targets[index : index + width]), probability)
                    ] += 1
        for block in active:
            params = rule_by_block.get(block, noise.default)
            sites = {i for (b, _), i in result.physical_qubit_map.items() if b == block}
            for qubit in sites - used:
                if params.idle:
                    expected[(layer_index, "DEPOLARIZE1", (qubit,), params.idle)] += 1
        active -= retiring
    assert fault_counter(result.circuit) == expected
    measured = [
        (i.targets_copy(), i.gate_args_copy()[0]) for i in result.circuit if i.name in ("M", "MX")
    ]
    assert measured == measurement_expected
    assert result.circuit.without_noise() == result.ideal_circuit
    assert result.circuit.num_ticks == result.ideal_circuit.num_ticks
    virtual = next(
        f
        for f in result.fragments
        if f.operation_type == "LogicalPauli" and f.logical_ids == ("B",)
    )
    assert virtual.components == ()
    assert all(
        virtual.module_id not in layer.operation_by_block.values() for layer in result.time_layers
    )
    for f in result.fragments:
        if f.operation_type == "TransversalCNOT":
            layers = [
                layer
                for layer in result.time_layers
                if f.module_id in layer.operation_by_block.values()
            ]
            assert len(layers) == 1
            assert {
                b for b, module in layers[0].operation_by_block.items() if module == f.module_id
            } == {"A", "B"}


def test_virtual_pauli_adds_neither_time_nor_noise():
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(3))
    compiler = CircuitCompiler([block])
    noise = NoiseModel.uniform_depolarizing(0.001)
    baseline = compiler.compile(
        [LogicalInit("p", "Z", 1), LogicalMeasure("p", "Z")], noise_model=noise
    )
    virtual = compiler.compile(
        [LogicalInit("p", "Z", 1), LogicalPauli("p", "X", "frame"), LogicalMeasure("p", "Z")],
        noise_model=noise,
    )

    # Module IDs may differ; remove tags structurally for physical-circuit comparison.
    def untag(circuit):
        import stim

        out = stim.Circuit()
        for inst in circuit:
            out.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
        return out

    assert untag(virtual.ideal_circuit) == untag(baseline.ideal_circuit)
    assert untag(virtual.circuit) == untag(baseline.circuit)
    raw = virtual.ideal_circuit.compile_sampler(seed=5).sample(16)
    assert virtual.interpreted_measurements(raw).all()


def test_zero_noise_cliffords():
    blocks = [
        LogicalBlock.placed(q, CodeSpec.rotated_surface(3), patch_index=i)
        for i, q in enumerate(("A", "B"))
    ]
    program = [
        LogicalInit(("A", "B"), "Z", 1),
        TransversalH("A"),
        TransversalCNOT("A", "B"),
        TransversalCNOT("A", "B"),
        TransversalH("A"),
        LogicalPauli("A", "Y"),
        LogicalMeasure(("A", "B"), "Z"),
    ]
    result = CircuitCompiler(blocks).compile(program, noise_model=NoiseModel())
    assert result.noisy_circuit == result.ideal_circuit
