"""Canonical source preserves every typed field and exact existing operation."""

from dataclasses import fields, is_dataclass, replace

import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from logical_to_stim_converter.language import parse_ast, parse_logical_circuit
from logical_to_stim_converter.language.errors import LSTIMSemanticError
from logical_to_stim_converter.language.formatter import format_logical_circuit

PREFIX = """FORMAT(1)
CODE code_alias ROTATED_SURFACE(3)
PATCH P2 code_alias index=2
PATCH P0 code_alias index=0
PATCH P1 code_alias index=1
BIND D P0
BIND A P1
BIND B P2
"""
BINDINGS = (BindPatch("D", "P0"), BindPatch("A", "P1"), BindPatch("B", "P2"))


def signature(value):
    """Independent AST comparison, preserving scalar types/order but excluding spans."""
    if is_dataclass(value):
        return type(value), tuple(
            (field.name, signature(getattr(value, field.name)))
            for field in fields(value) if field.name != "span"
        )
    if isinstance(value, tuple):
        return tuple(signature(item) for item in value)
    return type(value), value


def round_trip(source, expected):
    original = parse_logical_circuit(source, "original.lstim")
    text = format_logical_circuit(original)
    reparsed = parse_logical_circuit(text, "canonical.lstim")
    assert signature(original.ast) == signature(reparsed.ast)
    assert original.to_operations() == reparsed.to_operations() == expected
    assert format_logical_circuit(reparsed) == format_logical_circuit(original.ast) == text
    assert text.endswith("\n") and not text.endswith("\n\n") and "\r" not in text
    assert [block.block_id for block in reparsed.blocks] == ["P2", "P0", "P1"]
    return text


@pytest.mark.parametrize("line,operation", [
    ("INIT_Z(3) D", LogicalInit("D", "Z", 3)),
    ("INIT_X(2) D", LogicalInit("D", "X", 2)),
    ("SE(4) D", SyndromeExtraction("D", 4)),
    ("H D", TransversalH("D")),
    ("CX B D", TransversalCNOT("B", "D")),
    ("X D", LogicalPauli("D", "X")),
    ("Y D mode=physical", LogicalPauli("D", "Y", mode="physical")),
    ("Z D mode=frame", LogicalPauli("D", "Z", mode="frame")),
    ("X D mode=frame", LogicalPauli("D", "X", mode="frame")),
    ("Y D mode=frame", LogicalPauli("D", "Y", mode="frame")),
    ("MX D", LogicalMeasure("D", "X")),
    ("MZ D", LogicalMeasure("D", "Z")),
    ("MX D mode=deterministic", LogicalMeasure("D", "X", mode="deterministic")),
    ("MZ D mode=random", LogicalMeasure("D", "Z", mode="random")),
    ("BELL_PREP A B", BellStatePrep("A", "B")),
    ("BELL_PREP(5) A B", BellStatePrep("A", "B", 5)),
    ("KNILL_EC D A B", KnillEC("D", "A", "B")),
    ("KNILL_EC(3) D A B prepare_resource=true", KnillEC("D", "A", "B", rounds=3)),
    ("KNILL_EC D A B prepare_resource=false", KnillEC("D", "A", "B", prepare_resource=False)),
])
@pytest.mark.parametrize("label", [None, "cycle_2"])
def test_every_opcode_defaults_options_labels_and_control_order(line, operation, label):
    if label:
        opcode, rest = line.split(" ", 1)
        position = opcode.find("(")
        position = len(opcode) if position < 0 else position
        line = opcode[:position] + f"[{label}]" + opcode[position:] + " " + rest
        if isinstance(operation, TransversalCNOT):
            operation = TransversalCNOT(*operation.targets, operation_id=label)
        elif isinstance(operation, BellStatePrep):
            operation = BellStatePrep(*operation.targets, operation.rounds, operation_id=label)
        elif isinstance(operation, KnillEC):
            operation = KnillEC(
                *operation.targets, rounds=operation.rounds,
                prepare_resource=operation.prepare_resource, operation_id=label,
            )
        else:
            operation = replace(operation, operation_id=label)
    assert round_trip(PREFIX + line, (*BINDINGS, operation)) == PREFIX + line + "\n"


def test_comments_crlf_leading_zeroes_nested_groups_and_binding_barriers():
    source = "# 注釈\r\n\r\n" + PREFIX.replace("(1)", "(01)").replace("index=2", "index=002")
    source += """  H[first]   D # label
REPEAT 02 {
 REPEAT 1 {
  PARALLEL {
   SE(01) D
   X A mode = frame
  }
 }
 CX B D
}
BIND later P0
Z later
"""
    source = source.replace("\r\n", "\n").replace("\n", "\r\n")
    layer = (SyndromeExtraction("D", 1), LogicalPauli("A", "X", mode="frame"))
    expected = (*BINDINGS, TransversalH("D", operation_id="first"),
                layer, TransversalCNOT("B", "D"), layer, TransversalCNOT("B", "D"),
                BindPatch("later", "P0"), LogicalPauli("later", "Z"))
    assert round_trip(source, expected) == PREFIX + """H[first] D
REPEAT 2 {
    REPEAT 1 {
        PARALLEL {
            SE(1) D
            X A mode=frame
        }
    }
    CX B D
}
BIND later P0
Z later
"""


def test_declarations_only_are_valid_but_empty_or_header_only_are_not():
    source = "# No executable lines\nFORMAT(1)\nCODE sc ROTATED_SURFACE(3)\nPATCH P sc index=7"
    program = parse_logical_circuit(source)
    assert format_logical_circuit(program) == source.split("\n", 1)[1] + "\n"
    assert not program.operations
    with pytest.raises(LSTIMSemanticError, match="at least one physical PATCH"):
        format_logical_circuit(parse_ast("# comment\nFORMAT(1)\n"))


@pytest.mark.parametrize("source", [
    PREFIX.replace("FORMAT(1)", "FORMAT(2)"),
    PREFIX + "H unknown", PREFIX + "CX D D", PREFIX + "SE(0) D",
    PREFIX + "X D mode=random", PREFIX + "PARALLEL {\nH D\n}",
    PREFIX + "REPEAT 2 {\nH[tag] D\n}",
])
def test_syntax_only_invalid_ast_is_not_formatted_as_verified(source):
    with pytest.raises(LSTIMSemanticError):
        format_logical_circuit(parse_ast(source))


@pytest.mark.parametrize("change", [
    {"opcode": "PHYSICAL_GATE"}, {"targets": ("D\nH A",)},
    {"label": "reserved\nX D"}, {"label": "H"}, {"targets": ["D"]},
    {"targets": "D"}, {"rounds": True}, {"opcode": None},
])
def test_hand_built_malformed_ast_cannot_inject_or_change_statements(change):
    ast = parse_ast(PREFIX + "H D")
    bad = replace(ast, statements=(*ast.statements[:-1], replace(ast.statements[-1], **change)))
    with pytest.raises(LSTIMSemanticError):
        format_logical_circuit(bad)


def test_malformed_declaration_and_mutable_ast_container_are_rejected():
    ast = parse_ast(PREFIX)
    for bad in [
        replace(ast, statements=list(ast.statements)),
        replace(ast, statements=(replace(ast.statements[0], alias="sc\nH D"), *ast.statements[1:])),
        replace(ast, header=replace(ast.header, version=True)),
        replace(ast, header=None),
    ]:
        with pytest.raises(LSTIMSemanticError):
            format_logical_circuit(bad)
    with pytest.raises(TypeError, match="LogicalProgram or FileNode"):
        format_logical_circuit("FORMAT(1)")


def test_formatting_does_not_compile_or_unroll_a_syntax_tree(monkeypatch):
    from logical_to_stim_converter.language import program

    def forbidden(*args, **kwargs):
        raise AssertionError("formatter attempted physical allocation or loop lowering")

    monkeypatch.setattr(program, "lower_ast", forbidden)
    ast = parse_ast(PREFIX + "REPEAT 90000 {\nH D\n}\n")
    assert format_logical_circuit(ast) == PREFIX + "REPEAT 90000 {\n    H D\n}\n"
