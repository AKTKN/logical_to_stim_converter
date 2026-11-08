"""Real compiler delegation, independent Python equivalence and lifecycle failures."""

from unittest.mock import patch

import numpy as np
import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    BlockUseId,
    CircuitCompiler,
    CodeSpec,
    CompiledCircuit,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from logical_to_stim_converter.language import parse_logical_circuit
from logical_to_stim_converter.language.errors import LSTIMCompileError


def declarations(count=1, distance=3):
    return (
        f"FORMAT(1)\nCODE sc ROTATED_SURFACE({distance})\n"
        + "".join(f"PATCH P{i} sc index={i}\n" for i in range(count))
    )


def blocks(count=1, distance=3):
    code = CodeSpec.rotated_surface(distance)
    return tuple(LogicalBlock.placed(f"P{i}", code, patch_index=i) for i in range(count))


def assert_equivalent(actual, reference):
    """Compare physical circuits and canonical metadata, then independently verify flows."""
    assert type(actual) is CompiledCircuit
    assert actual.ideal_circuit == reference.ideal_circuit
    assert actual.noisy_circuit == reference.noisy_circuit
    assert (
        actual.ideal_circuit.detector_error_model()
        == reference.ideal_circuit.detector_error_model()
    )
    if actual.noisy_circuit is not None:
        assert (
            actual.noisy_circuit.detector_error_model()
            == reference.noisy_circuit.detector_error_model()
        )
    for attribute in (
        "physical_qubit_map", "logical_to_block", "measurement_index_by_key", "measurements",
        "detectors", "observables", "time_layers", "block_uses", "binding_history",
        "relocation_history", "composites", "detector_boundary_candidates", "orientations",
        "preparation_dependencies", "use_preparation_dependencies", "ancestry_events",
    ):
        assert getattr(actual, attribute) == getattr(reference, attribute), attribute
    assert (
        actual.ideal_circuit.get_detector_coordinates()
        == reference.ideal_circuit.get_detector_coordinates()
    )
    assert [
        (f.module_id, f.operation_id, f.composite_ids, f.block_use_ids) for f in actual.fragments
    ] == [
        (f.module_id, f.operation_id, f.composite_ids, f.block_use_ids) for f in reference.fragments
    ]
    for fragment in actual.fragments:
        fragment.verify()
    actual.validate_metadata()
    detectors, observables = actual.ideal_circuit.compile_detector_sampler(seed=83).sample(
        32, separate_observables=True,
    )
    assert not detectors.any() and not observables.any()


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_memory_text_matches_independent_python_signed_frame_and_noise(distance, basis):
    axis = "Z" if basis == "X" else "X"
    source = declarations(distance=distance) + f"""BIND D P0
INIT_{basis}[input](2) D
{axis}[flip] D mode=frame
REPEAT 2 {{
    SE(1) D
}}
H D
H D
M{basis}[output] D
"""
    program = parse_logical_circuit(source)
    noise = NoiseModel.uniform_depolarizing(0.003)
    reference = CircuitCompiler(blocks(distance=distance), logical_to_block={}).compile((
        BindPatch("D", "P0"), LogicalInit("D", basis, 2, operation_id="input"),
        LogicalPauli("D", axis, mode="frame", operation_id="flip"),
        SyndromeExtraction("D", 1), SyndromeExtraction("D", 1), TransversalH("D"),
        TransversalH("D"), LogicalMeasure("D", basis, operation_id="output"),
    ), noise_model=noise)
    actual = program.compile(noise_model=noise)
    assert_equivalent(actual, reference)
    assert actual.observables[0].expected_value == 1
    assert actual.block_uses[0].use_id == BlockUseId("P0", 0)
    assert len([f for f in actual.fragments if f.operation_type == "SyndromeExtraction"]) == 2


def test_parallel_boundaries_and_unequal_rounds_keep_the_same_physical_schedule():
    source = declarations(2) + """BIND D P0
BIND A P1
PARALLEL {
    INIT_Z(2) D
    INIT_X(1) A
}
REPEAT 2 {
    PARALLEL {
        SE(1) D
        SE(2) A
    }
}
PARALLEL {
    H D
    H A
}
PARALLEL {
    MX D
    MZ A
}
"""
    noise = NoiseModel.uniform_depolarizing(0.001)
    reference = CircuitCompiler(blocks(2), logical_to_block={}).compile((
        BindPatch("D", "P0"), BindPatch("A", "P1"),
        (LogicalInit("D", "Z", 2), LogicalInit("A", "X", 1)),
        (SyndromeExtraction("D", 1), SyndromeExtraction("A", 2)),
        (SyndromeExtraction("D", 1), SyndromeExtraction("A", 2)),
        (TransversalH("D"), TransversalH("A")),
        (LogicalMeasure("D", "X"), LogicalMeasure("A", "Z")),
    ), noise_model=noise)
    assert_equivalent(parse_logical_circuit(source).compile(noise_model=noise), reference)


@pytest.mark.parametrize("rounds", [None, 1])
def test_bell_prep_default_and_explicit_rounds_match_existing_composite(rounds):
    argument = "" if rounds is None else "(1)"
    source = declarations(2) + f"""BIND A P0
BIND B P1
BELL_PREP[bell]{argument} A B
CX[undo] A B
PARALLEL {{
    MX A
    MZ B
}}
"""
    noise = NoiseModel.uniform_depolarizing(0.002)
    reference = CircuitCompiler(blocks(2), logical_to_block={}).compile((
        BindPatch("A", "P0"), BindPatch("B", "P1"),
        BellStatePrep("A", "B", rounds, operation_id="bell"),
        TransversalCNOT("A", "B", operation_id="undo"),
        (LogicalMeasure("A", "X"), LogicalMeasure("B", "Z")),
    ), noise_model=noise)
    actual = parse_logical_circuit(source).compile(noise_model=noise)
    assert_equivalent(actual, reference)
    assert any(c.composite_id == "bell" for c in actual.composites)
    assert any("bell" in f.composite_ids for f in actual.fragments)


@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("prepare_resource", [True, False])
def test_one_cycle_knill_with_default_or_existing_resource_matches_python(basis, prepare_resource):
    prep = "" if prepare_resource else "BELL_PREP[resource](1) A B\n"
    source = declarations(3) + f"""BIND D P0
BIND A P1
BIND B P2
INIT_{basis}(1) D
{prep}KNILL_EC[cycle] D A B prepare_resource={str(prepare_resource).lower()}
SE(1) D
M{basis} D
"""
    operations = [
        BindPatch("D", "P0"), BindPatch("A", "P1"), BindPatch("B", "P2"),
        LogicalInit("D", basis, 1),
    ]
    if not prepare_resource:
        operations.append(BellStatePrep("A", "B", 1, operation_id="resource"))
    operations.extend((
        KnillEC("D", "A", "B", prepare_resource=prepare_resource, operation_id="cycle"),
        SyndromeExtraction("D", 1), LogicalMeasure("D", basis),
    ))
    noise = NoiseModel.uniform_depolarizing(0.001)
    reference = CircuitCompiler(blocks(3), logical_to_block={}).compile(
        operations, noise_model=noise,
    )
    program = parse_logical_circuit(source, "knill.lstim")
    actual = program.compile(noise_model=noise)
    assert_equivalent(actual, reference)
    assert actual.relocation_history[0].composite_id == "cycle"
    assert actual.relocation_history[0].output_block_id == "P2"
    cycle = next(c for c in actual.composites if c.composite_id == "cycle")
    children = [f for f in actual.fragments if "cycle" in f.composite_ids]
    assert children
    assert set(cycle.child_operation_ids) == {f.operation_id for f in children}
    assert program.label_spans["cycle"].source_name == "knill.lstim"


def test_full_three_patch_contract_bindings_start_only_actual_reset_epochs():
    source = declarations(3) + """BIND D P0
BIND A0 P1
BIND B0 P2
INIT_Z(3) D
KNILL_EC[cycle0](3) D A0 B0
SE(1) D
BIND A1 P0
BIND B1 P1
KNILL_EC[cycle1](3) D A1 B1
SE(1) D
BIND A2 P2
BIND B2 P0
KNILL_EC[cycle2](3) D A2 B2
SE(1) D
MZ D
"""
    reference = CircuitCompiler(blocks(3), logical_to_block={}).compile((
        BindPatch("D", "P0"), BindPatch("A0", "P1"), BindPatch("B0", "P2"),
        LogicalInit("D", "Z", 3), KnillEC("D", "A0", "B0", rounds=3, operation_id="cycle0"),
        SyndromeExtraction("D", 1), BindPatch("A1", "P0"), BindPatch("B1", "P1"),
        KnillEC("D", "A1", "B1", rounds=3, operation_id="cycle1"), SyndromeExtraction("D", 1),
        BindPatch("A2", "P2"), BindPatch("B2", "P0"),
        KnillEC("D", "A2", "B2", rounds=3, operation_id="cycle2"), SyndromeExtraction("D", 1),
        LogicalMeasure("D", "Z"),
    ))
    actual = parse_logical_circuit(source).compile()
    assert_equivalent(actual, reference)
    assert actual.circuit.num_qubits == 51
    assert [use.use_id for use in actual.block_uses] == [
        BlockUseId("P0", 0), BlockUseId("P1", 0), BlockUseId("P2", 0),
        BlockUseId("P0", 1), BlockUseId("P1", 1), BlockUseId("P2", 1), BlockUseId("P0", 2),
    ]
    assert [b.composite_id for b in actual.bell_measurements] == ["cycle0", "cycle1", "cycle2"]


def test_repeated_compilation_has_independent_noise_and_preserves_source_and_operations():
    source = declarations() + "BIND D P0\nINIT_Z(1) D\nREPEAT 2 {\nSE(1) D\n}\nMZ D"
    program = parse_logical_circuit(source)
    original = (program.ast, program.blocks, program.operations, program.operation_spans)
    first = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.001))
    saved = first.circuit.copy()
    second = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.03))
    ideal = program.compile()
    assert ideal.noisy_circuit is None
    assert first.ideal_circuit == second.ideal_circuit == ideal.ideal_circuit
    assert saved == first.circuit and first.circuit != second.circuit
    assert original == (program.ast, program.blocks, program.operations, program.operation_spans)
    assert all(op.noise is None for op in program.operations if not isinstance(op, BindPatch))
    assert (
        first.make_decoder_view().detector_error_model.flattened()
        == first.circuit.detector_error_model().flattened()
    )
    assert first.make_frame_plan().source_fingerprint != second.make_frame_plan().source_fingerprint


def test_open_outputs_and_standard_artifact_continuation_remain_available():
    source = declarations() + "BIND D P0\nINIT_X(1) D\nH D"
    program = parse_logical_circuit(source)
    opened = program.compile(allow_open_outputs=True)
    assert opened.open_logical_outputs == {"D": "P0"}
    assert opened.open_interface is not None
    closed = opened.append((LogicalMeasure("D", "Z"),))
    reference = CircuitCompiler(blocks(), logical_to_block={}).compile((
        BindPatch("D", "P0"), LogicalInit("D", "X", 1), TransversalH("D"), LogicalMeasure("D", "Z"),
    ))
    assert_equivalent(closed, reference)


def test_bridge_passes_the_exact_immutable_program_empty_mapping_and_flags_once():
    program = parse_logical_circuit(declarations() + "BIND D P0\nINIT_Z(1) D")
    noise = NoiseModel.uniform_depolarizing(0.001)
    sentinel = object()
    with patch(
        "logical_to_stim_converter.compiler.circuit_compiler.CircuitCompiler", autospec=True,
    ) as compiler:
        compiler.return_value.compile.return_value = sentinel
        assert program.compile(noise_model=noise, allow_open_outputs=True) is sentinel
        compiler.assert_called_once_with(program.blocks, logical_to_block={})
        compiler.return_value.compile.assert_called_once_with(
            program.operations, noise_model=noise, allow_open_outputs=True,
        )


@pytest.mark.parametrize("body,reason", [
    ("H D", "operands must be active"),
    ("BIND other P0", "active or reserved"),
    ("INIT_Z(1) D\nBIND other P0", "active or reserved"),
    ("INIT_Z(1) D\nMZ D\nH D", "Retired logical handle"),
    ("INIT_Z(1) D\nMZ D\nINIT_X(1) D", "Retired logical handle"),
    ("INIT_Z(1) D\nPARALLEL {\nH D\nX D\n}", "same physical block twice"),
    ("INIT_Z(1) D\nMX D", "nondeterministic"),
    ("INIT_Z(1) D\nH[op0000] D", "Operation IDs must be unique"),
])
def test_existing_compiler_rejects_invalid_memory_lifecycle_and_keeps_original_cause(body, reason):
    source = declarations() + "BIND D P0\n" + body
    program = parse_logical_circuit(source, "invalid.lstim")
    with pytest.raises(LSTIMCompileError, match=reason) as caught:
        program.compile()
    error = caught.value
    assert isinstance(error.__cause__, ValueError)
    assert error.original_error is error.__cause__
    assert error.source_name == "invalid.lstim"
    assert error.span is error.line is error.column is None
    with pytest.raises(ValueError) as direct:
        CircuitCompiler(program.blocks, logical_to_block={}).compile(program.operations)
    assert str(direct.value) == str(error.original_error)


def test_invalid_existing_knill_resource_and_stale_resource_alias_fail_in_existing_compiler():
    prefix = declarations(3) + "BIND D P0\nBIND A P1\nBIND B P2\nINIT_Z(1) D\n"
    for body, reason in [
        ("INIT_Z(1) A\nINIT_Z(1) B\nKNILL_EC D A B prepare_resource=false", "Bell XX=ZZ"),
        ("INIT_Z(1) A\nKNILL_EC D A B", "resources must be uninitialized"),
        ("KNILL_EC(1) D A B\nH B", "Retired logical handle"),
    ]:
        program = parse_logical_circuit(prefix + body)
        with pytest.raises(LSTIMCompileError, match=reason) as caught:
            program.compile()
        assert isinstance(caught.value.__cause__, ValueError)


def test_unique_indices_can_still_collide_and_only_the_compiler_checks_geometry():
    source = """FORMAT(1)
CODE small ROTATED_SURFACE(3)
CODE large ROTATED_SURFACE(5)
PATCH P0 small index=3
PATCH P1 large index=2
"""
    program = parse_logical_circuit(source, "collision.lstim")
    assert program.blocks[0].origin == program.blocks[1].origin == 24
    with pytest.raises(LSTIMCompileError, match="overlapping physical coordinates") as caught:
        program.compile(allow_open_outputs=True)
    assert isinstance(caught.value.original_error, ValueError)
    assert caught.value.source_name == "collision.lstim" and caught.value.span is None


def test_random_readout_keeps_raw_measurements_without_deterministic_observables():
    source = declarations() + "BIND D P0\nINIT_Z(1) D\nMX D mode=random"
    actual = parse_logical_circuit(source).compile()
    reference = CircuitCompiler(blocks(), logical_to_block={}).compile((
        BindPatch("D", "P0"), LogicalInit("D", "Z", 1), LogicalMeasure("D", "X", mode="random"),
    ))
    assert_equivalent(actual, reference)
    assert actual.circuit.num_observables == 0
    assert actual.readouts[0].mode == "random"
    assert np.any(actual.circuit.compile_sampler(seed=831).sample(32))
