"""Logical oracle comparisons, frame interpretation, and interacting-block regressions."""

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    CompilerContext,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    OperationContext,
    ParityExpression,
    PauliFrame,
    RotatedSurfaceCodeBackend,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from logical_to_stim_converter.core.compiler_context import MeasurementKey


def two_blocks(d=3):
    code = CodeSpec.rotated_surface(d)
    return [
        LogicalBlock.placed("physical" + q, code, patch_index=i) for i, q in enumerate(("A", "B"))
    ]


def compiler(blocks):
    return CircuitCompiler(blocks, logical_to_block={"A": "physicalA", "B": "physicalB"})


def assert_readout(compiled, expected, seed=3):
    samples = compiled.ideal_circuit.compile_sampler(seed=seed).sample(32)
    assert (compiled.interpreted_measurements(samples) == np.asarray(expected)).all()
    assert [o.expected_value for o in compiled.observables] == list(expected)
    # Independently check that the exported OBS parities and affine constants agree.
    for observable in compiled.observables:
        parity = np.bitwise_xor.reduce(samples[:, observable.measurement_indices], axis=1)
        interpreted = parity ^ observable.frame_correction.constant
        assert (interpreted == expected[observable.index]).all()
    compiled.ideal_circuit.detector_error_model()
    for detector in compiled.detectors:
        assert not np.bitwise_xor.reduce(samples[:, detector.measurement_indices], axis=1).any()
        assert detector.supporting_block_ids == tuple(
            sorted({key.block_id for key in detector.measurement_keys})
        )


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("orientation", [(0, 0), (0, 1), (1, 0), (1, 1)])
@pytest.mark.parametrize("bits", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_cnot_truth_table(d, orientation, bits):
    blocks = two_blocks(d)
    init = [LogicalInit(q, "X" if orientation[i] else "Z", 1) for i, q in enumerate(("A", "B"))]
    operations = [init]
    hs = [TransversalH(q) for i, q in enumerate(("A", "B")) if orientation[i]]
    if hs:
        operations.append(hs)
    for i, q in enumerate(("A", "B")):
        if bits[i]:
            operations.append(LogicalPauli(q, "X"))
    operations.extend(
        [
            TransversalCNOT(control="A", target="B"),
            SyndromeExtraction(("A", "B"), 1),
            LogicalMeasure(("A", "B"), "Z"),
        ]
    )
    result = compiler(blocks).compile(operations)
    oracle = stim.TableauSimulator()
    oracle.set_num_qubits(2)
    for i, bit in enumerate(bits):
        if bit:
            oracle.x(i)
    oracle.cx(0, 1)
    expected = [int(oracle.peek_z(i) == -1) for i in range(2)]
    assert_readout(result, expected)
    # Raw data parity, independently selected in each physical code orientation.
    raw = result.ideal_circuit.compile_sampler(seed=5).sample(32)
    for i, q in enumerate(("A", "B")):
        dcols = (
            range(d) if not orientation[i] else range(d - 1, d * d, d)
        )  # Frame 1 logical Z is the physical northern row.
        indices = [
            m.index
            for m in result.measurements
            if m.key.block_id == "physical" + q
            and m.key.kind == "readout"
            and m.key.local_id in {f"D{j + 1}" for j in dcols}
        ]
        assert len(indices) == d
        assert (np.bitwise_xor.reduce(raw[:, indices], axis=1) == expected[i]).all()


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_h_then_se_and_h_squared(d, basis):
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(d))
    c = CircuitCompiler([block], logical_to_block={"q": "p"})
    result = c.compile(
        [
            LogicalInit("q", basis, 1),
            TransversalH("q"),
            SyndromeExtraction("q", d),
            LogicalMeasure("q", "Z" if basis == "X" else "X"),
        ]
    )
    assert result.orientations["q"] == 1
    assert_readout(result, [0])
    twice = c.compile(
        [
            LogicalInit("q", basis, 1),
            TransversalH("q"),
            SyndromeExtraction("q", 1),
            TransversalH("q"),
            LogicalMeasure("q", basis),
        ]
    )
    assert twice.orientations["q"] == 0
    assert twice.physical_qubit_map == result.physical_qubit_map
    assert_readout(twice, [0])


@pytest.mark.parametrize("axis", ["X", "Y", "Z"])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("mode", ["physical", "frame"])
def test_logical_pauli_readout(axis, basis, mode):
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(3))
    result = CircuitCompiler([block], logical_to_block={"q": "p"}).compile(
        [LogicalInit("q", basis, 1), LogicalPauli("q", axis, mode), LogicalMeasure("q", basis)]
    )
    expected = int(axis != basis)
    assert_readout(result, [expected])
    if mode == "physical":
        fragment = next(f for f in result.fragments if f.operation_type == "LogicalPauli")
        assert len(fragment.physical_positions) == (5 if axis == "Y" else 3)
        assert len(fragment.interface_positions) == 9
        raw = result.circuit.compile_sampler(seed=9).sample(32)
        assert (
            np.bitwise_xor.reduce(raw[:, result.observables[0].readout_measurement_indices], axis=1)
            == expected
        ).all()
    else:
        fragment = next(f for f in result.fragments if f.operation_type == "LogicalPauli")
        assert fragment.components == ()
        assert fragment.physical_positions == frozenset()
        assert result.time_layers[-1].index == 7


def test_symbolic_affine_frame_rules_and_preserved_preparation_info():
    context = CompilerContext(two_blocks(), {"A": "physicalA", "B": "physicalB"})
    a = MeasurementKey("physicalA", "X1", "syndrome", 0)
    b = MeasurementKey("physicalB", "Z1", "syndrome", 0)
    context.frames["A"] = PauliFrame(x_terms=(a,), z_constant=True, preparation_syndromes=(a,))
    context.frames["B"] = PauliFrame(z_terms=(b,), x_constant=True, preparation_syndromes=(b,))
    context.propagate_frames("CX", ("A", "B"))
    assert context.frames["A"].x == ParityExpression((a,))
    assert context.frames["A"].z == ParityExpression((b,), True)
    assert context.frames["B"].x == ParityExpression((a,), True)
    assert context.frames["B"].z == ParityExpression((b,))
    context.propagate_frames("H", ("A",))
    assert context.frames["A"].x == ParityExpression((b,), True)
    assert context.frames["A"].z == ParityExpression((a,))
    assert context.frames["A"].preparation_syndromes == (a,)
    # Duplicate symbolic terms cancel, and expressions evaluate on actual records.
    expression = ParityExpression((a, a, b), True)
    assert expression == ParityExpression((b,), True)
    assert expression.evaluate(np.array([[0, 1], [1, 0]]), {a: 0, b: 1}).tolist() == [False, True]


@pytest.mark.parametrize("mode", ["physical", "frame"])
def test_frame_pauli_conjugation_and_cnot_propagation(mode):
    result = compiler(two_blocks()).compile(
        [
            LogicalInit(("A", "B"), "Z", 1),
            LogicalPauli("A", "X", mode),
            TransversalCNOT("A", "B"),
            TransversalH("A"),
            SyndromeExtraction(("A", "B"), 1),
            [LogicalMeasure("A", "X"), LogicalMeasure("B", "Z")],
        ]
    )
    assert_readout(result, [1, 1])
    if mode == "frame":
        assert result.frames["A"].z_constant and result.frames["B"].x_constant


def test_multi_operand_identity_ordering_and_overlap_rejection():
    blocks = two_blocks()
    operations = [
        LogicalInit(("A", "B"), "Z", 1),
        TransversalCNOT("B", "A"),
        TransversalCNOT("B", "A"),
        LogicalMeasure(("A", "B"), "Z"),
    ]
    result = compiler(blocks).compile(operations)
    reverse_registration = compiler(list(reversed(blocks))).compile(operations)
    assert result.circuit == reverse_registration.circuit
    assert result.physical_qubit_map == reverse_registration.physical_qubit_map
    gates = [f for f in result.fragments if f.operation_type == "TransversalCNOT"]
    assert len(gates) == 2
    assert all(f.logical_ids == ("B", "A") for f in gates)
    assert all(f.block_ids == ("physicalB", "physicalA") for f in gates)
    assert len({f.module_id for f in result.fragments}) == len(result.fragments)
    with pytest.raises(ValueError, match="multi-operand"):
        _ = gates[0].block_id
    with pytest.raises(ValueError, match="same physical block"):
        compiler(blocks).compile(
            [LogicalInit(("A", "B"), "Z", 1), [TransversalCNOT("A", "B"), TransversalH("A")]]
        )
    for operation in [TransversalH("A"), TransversalCNOT("A", "B"), LogicalPauli("A", "X")]:
        with pytest.raises(ValueError):
            compiler(blocks).compile([operation])
    with pytest.raises(ValueError):
        TransversalCNOT("A", "A")
    with pytest.raises(ValueError, match="nondeterministic"):
        compiler(blocks).compile(
            [
                LogicalInit(("A", "B"), "Z", 1),
                TransversalH("A"),
                TransversalCNOT("A", "B"),
                LogicalMeasure(("A", "B"), "Z"),
            ]
        )
    with pytest.raises(ValueError):
        TransversalCNOT("A", "B").build(
            RotatedSurfaceCodeBackend(),
            {"B": blocks[1], "A": blocks[0]},
            OperationContext("wrong", {"A": 0, "B": 0}),
        )


def test_atomic_context_change_on_bad_two_block_operand():
    blocks = two_blocks()
    context = CompilerContext(blocks, {"A": "physicalA", "B": "physicalB"})
    backend = RotatedSurfaceCodeBackend()
    init = LogicalInit("A", "Z", 1)
    fragment = init.build(backend, {"A": blocks[0]}, OperationContext("init", context.orientations))
    context = context.advanced(init, fragment, backend)
    before_status = dict(context.status)
    before_frames = dict(context.frames)
    operation = TransversalCNOT("A", "B")
    fragment = operation.build(
        backend, {"A": blocks[0], "B": blocks[1]}, OperationContext("bad", context.orientations)
    )
    with pytest.raises(ValueError):
        context.advanced(operation, fragment, backend)
    assert context.status == before_status
    assert context.frames == before_frames
    assert context.orientations == {"A": 0, "B": 0}


def test_partial_readout_parallel_with_other_block_h():
    result = compiler(two_blocks()).compile(
        [
            LogicalInit(("A", "B"), "Z", 1),
            [LogicalMeasure("A", "Z"), TransversalH("B")],
            SyndromeExtraction("B", 1),
            LogicalMeasure("B", "X"),
        ]
    )
    assert_readout(result, [0, 0])
    assert result.ideal_circuit.num_ticks + 1 == 15


def test_random_product_outputs_against_independent_logical_tableau():
    rng = np.random.default_rng(142)
    accepted = 0
    for _ in range(100):
        oracle = stim.TableauSimulator()
        oracle.set_num_qubits(2)
        operations = [LogicalInit(("A", "B"), "Z", 1)]
        for _ in range(7):
            choice = int(rng.integers(8))
            if choice < 2:
                oracle.h(choice)
                operations.append(TransversalH("AB"[choice]))
            elif choice < 4:
                c = choice - 2
                oracle.cx(c, 1 - c)
                operations.append(TransversalCNOT("AB"[c], "AB"[1 - c]))
            else:
                qubit = choice % 2
                axis = "X" if choice < 6 else "Z"
                getattr(oracle, axis.lower())(qubit)
                operations.append(
                    LogicalPauli("AB"[qubit], axis, "frame" if choice % 2 else "physical")
                )
            if len(operations) == 4:
                operations.append(SyndromeExtraction(("A", "B"), 1))
        bases, expected = [], []
        for i in range(2):
            x, z = oracle.peek_x(i), oracle.peek_z(i)
            if not (x or z):
                break
            bases.append("X" if x else "Z")
            expected.append(int((x if x else z) == -1))
        if len(bases) != 2:
            continue
        operations.append([LogicalMeasure(q, basis) for q, basis in zip("AB", bases, strict=True)])
        result = compiler(two_blocks()).compile(operations)
        assert_readout(result, expected)
        accepted += 1
        if accepted == 12:
            break
    assert accepted == 12


def test_incorrect_frame_propagation_fails_signed_physical_readout(monkeypatch):
    original = CompilerContext.propagate_frames

    def broken(self, action, logical_ids, corrections=None):
        if action != "CX":
            original(self, action, logical_ids, corrections)

    monkeypatch.setattr(CompilerContext, "propagate_frames", broken)
    with pytest.raises(ValueError, match="does not realize"):
        compiler(two_blocks()).compile(
            [
                LogicalInit(("A", "B"), "Z", 1),
                LogicalPauli("A", "X", "frame"),
                TransversalCNOT("A", "B"),
                LogicalMeasure(("A", "B"), "Z"),
            ]
        )
