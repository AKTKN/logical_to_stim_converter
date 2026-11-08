"""Exact existing-object lowering and logical barriers, without circuit compilation."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from logical_to_stim_converter.language import LogicalProgram, parse_logical_circuit
from logical_to_stim_converter.language.errors import LSTIMSemanticError

PREFIX = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
PATCH P1 sc index=1
PATCH P2 sc index=2
BIND D P0
BIND A P1
BIND B P2
"""


@pytest.mark.parametrize("command,expected", [
    ("INIT_Z(3) D", LogicalInit("D", "Z", 3)),
    ("INIT_X(2) D", LogicalInit("D", "X", 2)),
    ("SE(4) D", SyndromeExtraction("D", 4)),
    ("H D", TransversalH("D")), ("CX A D", TransversalCNOT("A", "D")),
    ("X D", LogicalPauli("D", "X")), ("Y D", LogicalPauli("D", "Y")),
    ("Z D mode=physical", LogicalPauli("D", "Z", mode="physical")),
    ("X D mode=frame", LogicalPauli("D", "X", mode="frame")),
    ("Y D mode=frame", LogicalPauli("D", "Y", mode="frame")),
    ("Z D mode=frame", LogicalPauli("D", "Z", mode="frame")),
    ("MX D", LogicalMeasure("D", "X")), ("MZ D", LogicalMeasure("D", "Z")),
    ("MX D mode=deterministic", LogicalMeasure("D", "X", mode="deterministic")),
    ("MZ D mode=random", LogicalMeasure("D", "Z", mode="random")),
    ("BELL_PREP A B", BellStatePrep("A", "B")),
    ("BELL_PREP(3) A B", BellStatePrep("A", "B", 3)),
    ("KNILL_EC D A B", KnillEC("D", "A", "B")),
    ("KNILL_EC(5) D A B prepare_resource=true", KnillEC("D", "A", "B", rounds=5)),
    ("KNILL_EC D A B prepare_resource=false", KnillEC("D", "A", "B", prepare_resource=False)),
])
@pytest.mark.parametrize("label", [None, "source_label"])
def test_each_operation_is_the_exact_existing_type_with_exact_fields(command, expected, label):
    if label:
        from dataclasses import replace

        opcode_end = min((i for i in (command.find("("), command.find(" ")) if i >= 0))
        command = command[:opcode_end] + f"[{label}]" + command[opcode_end:]
        # These custom constructors expose ordered operands instead of targets=.
        if isinstance(expected, TransversalCNOT):
            expected = TransversalCNOT(*expected.targets, operation_id=label)
        elif isinstance(expected, BellStatePrep):
            expected = BellStatePrep(*expected.targets, expected.rounds, operation_id=label)
        elif isinstance(expected, KnillEC):
            expected = KnillEC(
                *expected.targets, rounds=expected.rounds,
                prepare_resource=expected.prepare_resource, operation_id=label,
            )
        else:
            expected = replace(expected, operation_id=label)
    program = parse_logical_circuit(PREFIX + command)
    actual = program.operations[-1]
    assert type(actual) is type(expected)
    assert actual == expected
    assert actual.noise is None
    assert program.operations[:3] == (
        BindPatch("D", "P0"), BindPatch("A", "P1"), BindPatch("B", "P2"),
    )
    if label:
        assert program.label_spans[label] == program.operation_spans[-1]


def test_nested_repeat_and_parallel_expand_to_independent_ordered_objects():
    source = PREFIX + """H D
REPEAT 2 {
    SE(1) D
    REPEAT 2 {
        PARALLEL {
            X D mode=frame
            H A
        }
    }
    CX A D
}
MZ D mode=random
"""
    program = parse_logical_circuit(source, "nested.lstim")
    body = (
        SyndromeExtraction("D", 1),
        (LogicalPauli("D", "X", mode="frame"), TransversalH("A")),
        (LogicalPauli("D", "X", mode="frame"), TransversalH("A")),
        TransversalCNOT("A", "D"),
    )
    expected = (
        BindPatch("D", "P0"), BindPatch("A", "P1"), BindPatch("B", "P2"), TransversalH("D"),
        *body, *body, LogicalMeasure("D", "Z", mode="random"),
    )
    assert program.to_operations() == expected
    assert program.expanded_operation_count == 17
    assert isinstance(program.operations[5], tuple)
    leaves = [
        op for entry in program.operations
        for op in (entry if isinstance(entry, tuple) else (entry,))
    ]
    assert len({id(op) for op in leaves}) == len(leaves)
    assert program.operation_spans[4] == program.operation_spans[8]
    assert program.operation_spans[5] == program.operation_spans[6]
    assert len(program.operation_spans[5]) == 2
    assert program.source_name == "nested.lstim"
    assert program.source == source
    assert program.ast.statements[-2].count == 2


def test_repeated_se_is_not_coalesced_into_one_module():
    program = parse_logical_circuit(PREFIX + "REPEAT 3 {\nSE(1) D\n}")
    assert program.operations[3:] == (SyndromeExtraction("D", 1),) * 3
    assert len({id(op) for op in program.operations[3:]}) == 3


def test_patch_declarations_use_exact_code_factories_placement_and_site_maps():
    source = """FORMAT(1)
CODE small ROTATED_SURFACE(3)
CODE large ROTATED_SURFACE(5)
PATCH P2 large index=3
PATCH P0 small index=0
BIND D P0
"""
    program = parse_logical_circuit(source)
    references = (
        LogicalBlock.placed("P2", CodeSpec.rotated_surface(5), patch_index=3),
        LogicalBlock.placed("P0", CodeSpec.rotated_surface(3), patch_index=0),
    )
    for block, reference in zip(program.blocks, references, strict=True):
        assert (block.block_id, block.origin, block.code.d) == (
            reference.block_id, reference.origin, reference.code.d,
        )
        assert dict(block.site_map) == dict(reference.site_map)
        assert block.layout == reference.layout
        assert [block.position(q) for q in block.layout.qubit_ids] == [
            reference.position(q) for q in reference.layout.qubit_ids
        ]
        for name in ("H_X", "H_Z", "L_X", "L_Z"):
            np.testing.assert_array_equal(getattr(block.code, name), getattr(reference.code, name))
    assert program.operations == (BindPatch("D", "P0"),)


def test_later_bindings_and_knill_labels_preserve_the_full_three_patch_schedule():
    source = PREFIX.replace("BIND A P1\nBIND B P2\n", "BIND A0 P1\nBIND B0 P2\n") + """INIT_Z(3) D
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
    expected = (
        BindPatch("D", "P0"), BindPatch("A0", "P1"), BindPatch("B0", "P2"),
        LogicalInit("D", "Z", 3), KnillEC("D", "A0", "B0", rounds=3, operation_id="cycle0"),
        SyndromeExtraction("D", 1), BindPatch("A1", "P0"), BindPatch("B1", "P1"),
        KnillEC("D", "A1", "B1", rounds=3, operation_id="cycle1"), SyndromeExtraction("D", 1),
        BindPatch("A2", "P2"), BindPatch("B2", "P0"),
        KnillEC("D", "A2", "B2", rounds=3, operation_id="cycle2"), SyndromeExtraction("D", 1),
        LogicalMeasure("D", "Z"),
    )
    program = parse_logical_circuit(source)
    assert program.operations == expected
    assert tuple(program.label_spans) == ("cycle0", "cycle1", "cycle2")


def test_program_and_lowered_values_are_immutable_and_inspection_does_not_compile(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("lowering compiled physical circuits")

    monkeypatch.setattr(CircuitCompiler, "__init__", forbidden)
    program = LogicalProgram(PREFIX + "H[tag] D")
    assert program.to_operations() is program.operations
    assert isinstance(program.blocks, tuple)
    for obj, attribute in [
        (program, "source"), (program.ast, "statements"), (program.operations[-1], "operation_id"),
        (program.blocks[0], "origin"),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, attribute, None)
    with pytest.raises(TypeError):
        program.label_spans["tag"] = program.ast.span
    with pytest.raises(TypeError):
        program.blocks[0].site_map["bad"] = ("P0", "bad")
    with pytest.raises(ValueError):
        program.blocks[0].code.H_X[0, 0] = 1


def test_oversized_expansion_is_rejected_before_code_or_patch_allocation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("allocated before checking expansion budget")

    monkeypatch.setattr(CodeSpec, "rotated_surface", forbidden)
    monkeypatch.setattr(LogicalBlock, "placed", forbidden)
    with pytest.raises(LSTIMSemanticError, match="Expansion exceeds"):
        parse_logical_circuit(PREFIX + "REPEAT 1000000000000000000000 {\nH D\n}")


def test_small_configured_budget_and_deep_static_nesting():
    body = "REPEAT 1 {\n" * 64 + "H D\n" + "}\n" * 64
    assert len(parse_logical_circuit(PREFIX + body, max_operations=4).operations) == 4
    with pytest.raises(LSTIMSemanticError, match="Expansion exceeds 3"):
        parse_logical_circuit(PREFIX + body, max_operations=3)
