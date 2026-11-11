"""Syntax structure, immutable values and exact original-source locations."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from logical_to_stim_converter.language import parse_ast
from logical_to_stim_converter.language.ast_nodes import (
    BindNode,
    CodeNode,
    FileNode,
    HeaderNode,
    OperationNode,
    OptionNode,
    ParallelNode,
    PatchNode,
    RepeatNode,
    SourceSpan,
)
from logical_to_stim_converter.language.errors import LstimSyntaxError

MEMORY = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z(3) D
REPEAT 2 {
    SE(1) D
}
MZ D
"""

THREE_PATCH = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
PATCH P1 sc index=1
PATCH P2 sc index=2
BIND D P0
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


def test_memory_declarations_header_and_unexpanded_loop():
    tree = parse_ast(MEMORY, "memory.lstim")
    assert isinstance(tree, FileNode)
    assert isinstance(tree.header, HeaderNode)
    assert tree.format_version == tree.header.version == 1
    code, patch, bind, init, repeat, measure = tree.statements
    assert isinstance(code, CodeNode)
    assert (code.alias, code.family, code.distance) == ("sc", "ROTATED_SURFACE", 3)
    assert isinstance(patch, PatchNode)
    assert (patch.physical_id, patch.code_alias, patch.index) == ("P0", "sc", 0)
    assert isinstance(bind, BindNode)
    assert (bind.logical_id, bind.physical_id) == ("D", "P0")
    assert (init.opcode, init.targets, init.rounds) == ("INIT_Z", ("D",), 3)
    assert isinstance(repeat, RepeatNode)
    assert repeat.count == 2
    assert len(repeat.body) == 1
    assert (repeat.body[0].opcode, repeat.body[0].rounds) == ("SE", 1)
    assert measure.opcode == "MZ"


def test_three_patch_fixture_retains_later_bindings_and_labels():
    tree = parse_ast(THREE_PATCH)
    assert len(tree.statements) == 19
    assert [s.logical_id for s in tree.statements if isinstance(s, BindNode)] == [
        "D", "A0", "B0", "A1", "B1", "A2", "B2",
    ]
    knills = [s for s in tree.statements if isinstance(s, OperationNode) and s.opcode == "KNILL_EC"]
    assert [(s.label, s.rounds, s.targets) for s in knills] == [
        ("cycle0", 3, ("D", "A0", "B0")),
        ("cycle1", 3, ("D", "A1", "B1")),
        ("cycle2", 3, ("D", "A2", "B2")),
    ]


def test_shared_contract_contains_exact_required_programs():
    contract = (Path(__file__).resolve().parents[1] / "docs/lstim_v1.md").read_text()
    assert f"```text\n{MEMORY}```" in contract
    assert f"```text\n{THREE_PATCH}```" in contract


@pytest.mark.parametrize("opcode,rounds,targets", [
    ("INIT_Z", 3, ("D",)), ("INIT_X", 2, ("D",)), ("SE", 4, ("D", "A")),
    ("H", None, ("D",)), ("CX", None, ("D", "A")), ("X", None, ("D",)),
    ("Y", None, ("D",)), ("Z", None, ("D",)), ("MX", None, ("D",)),
    ("MZ", None, ("D",)), ("BELL_PREP", 3, ("A", "B")),
    ("BELL_PREP", None, ("A", "B")), ("KNILL_EC", 5, ("D", "A", "B")),
    ("KNILL_EC", None, ("D", "A", "B")),
])
@pytest.mark.parametrize("label", [None, "source_label"])
def test_every_operation_and_optional_label(opcode, rounds, targets, label):
    text = opcode + (f"[{label}]" if label else "")
    text += f"({rounds})" if rounds is not None else ""
    node, = parse_ast("FORMAT(1)\n" + text + " " + " ".join(targets)).statements
    assert (node.opcode, node.rounds, node.targets, node.label, node.options) == (
        opcode, rounds, targets, label, (),
    )


@pytest.mark.parametrize("command,options", [
    ("X D mode=physical", [("mode", "physical")]),
    ("Y D mode=frame", [("mode", "frame")]),
    ("MX D mode=deterministic", [("mode", "deterministic")]),
    ("MZ D mode=random", [("mode", "random")]),
    ("KNILL_EC D A B prepare_resource=false", [("prepare_resource", False)]),
    ("KNILL_EC(3) D A B prepare_resource=true", [("prepare_resource", True)]),
    ("H D unknown=17 another = 0 mode=frame", [("unknown", 17), ("another", 0), ("mode", "frame")]),
])
def test_options_have_typed_values_and_order_without_semantic_validation(command, options):
    node, = parse_ast("FORMAT(1)\n" + command).statements
    assert all(isinstance(o, OptionNode) for o in node.options)
    assert [(o.name, o.value) for o in node.options] == options
    assert [type(o.value) for o in node.options] == [type(v) for _, v in options]


def test_exact_spans_include_delimiters_but_exclude_indentation_and_comments():
    source = (
        "# 注釈\r\nFORMAT(1)\r\nREPEAT 2 { # loop\r\n  PARALLEL {\r\n"
        "    H[tag] D\r\n    X A mode = frame # end\r\n  }\r\n}"
    )
    tree = parse_ast(source, "windows.lstim")
    repeat, = tree.statements
    parallel, = repeat.body
    assert isinstance(parallel, ParallelNode)
    h, x = parallel.operations
    assert tree.span == SourceSpan("windows.lstim", 1, 1, 8, 2, 0, len(source))
    assert tree.header.span == SourceSpan("windows.lstim", 2, 1, 2, 10, 0, 0)
    assert repeat.span == SourceSpan("windows.lstim", 3, 1, 8, 2, 0, 0)
    assert parallel.span == SourceSpan("windows.lstim", 4, 3, 7, 4, 0, 0)
    assert h.span == SourceSpan("windows.lstim", 5, 5, 5, 13, 0, 0)
    assert x.span == SourceSpan("windows.lstim", 6, 5, 6, 21, 0, 0)
    assert x.options[0].span == SourceSpan("windows.lstim", 6, 9, 6, 21, 0, 0)
    for node, text in [
        (tree.header, "FORMAT(1)"), (h, "H[tag] D"), (x, "X A mode = frame"),
        (x.options[0], "mode = frame"), (repeat, source[source.index("REPEAT"):]),
    ]:
        assert source[node.span.start_offset:node.span.end_offset] == text


def test_nested_repeats_and_parallel_preserve_order():
    source = """FORMAT(1)
REPEAT 2 {
    X D
    REPEAT 3 {
        PARALLEL {
            H A
            SE(1) D
        }
    }
    Z D
}
"""
    outer, = parse_ast(source).statements
    x, inner, z = outer.body
    assert (outer.count, inner.count, x.opcode, z.opcode) == (2, 3, "X", "Z")
    parallel, = inner.body
    assert [o.opcode for o in parallel.operations] == ["H", "SE"]
    assert len(outer.body) == 3


def test_ast_is_recursively_immutable_and_line_ending_independent():
    tree = parse_ast(THREE_PATCH)
    assert tree == parse_ast(THREE_PATCH.replace("\n", "\r\n"))
    assert hash(tree) == hash(parse_ast(THREE_PATCH))
    stack = [tree]
    while stack:
        item = stack.pop()
        if is_dataclass(item):
            first = fields(item)[0]
            with pytest.raises(FrozenInstanceError):
                setattr(item, first.name, None)
            stack.extend(getattr(item, f.name) for f in fields(item))
        elif isinstance(item, tuple):
            stack.extend(item)
        else:
            assert item is None or type(item) in {str, int, bool}


@pytest.mark.parametrize("source", [
    "", "# comment", "H D", "CODE sc ROTATED_SURFACE(3)\nFORMAT(1)",
    "FORMAT(1)\nFORMAT(1)", "FORMAT(1) H D", "FORMAT(1)\nH D X A",
    "FORMAT(1)\nH D; X A", "FORMAT(1)\nH D\nunknown D",
    "FORMAT(1)\nSE(3)\nD", "FORMAT(1)\nH", "FORMAT(1)\nSE(3,4) D",
    "FORMAT(1)\nKNILL_EC(3)[label] D A B", "FORMAT(1)\nX D[tag]",
    "FORMAT(1)\nH[a][b] D", "FORMAT(1)\nH D mode=frame other",
    "FORMAT(1)\nH D mode=", "FORMAT(1)\nH mode=frame D",
    "FORMAT(1)\nREPEAT 2 { SE(1) D }", "FORMAT(1)\nREPEAT 2 {\nH D}",
    "FORMAT(1)\nREPEAT 2 {\nH D\n", "FORMAT(1)\nPARALLEL {\nH D\n]",
    "FORMAT(1)\nPARALLEL {\nBIND D P0\n}",
    "FORMAT(1)\nPARALLEL {\nREPEAT 2 {\nH D\n}\n}",
    "FORMAT(1)\nPARALLEL {\nPARALLEL {\nH D\n}\n}",
    "FORMAT(1)\nREPEAT 2 {\nCODE sc ROTATED_SURFACE(3)\n}",
    "FORMAT(1)\nPATCH P0 sc", "FORMAT(1)\nPATCH P0 sc index=-1",
    "FORMAT(1)\nPATCH P0 sc index=0 extra=1", "FORMAT(1)\nBIND D P0 extra",
    "FORMAT(1)\nCODE sc ROTATED_SURFACE(3,3)",
    "FORMAT(1)\nH D mode=frame mode=frame D",
])
def test_malformed_structure_is_rejected(source):
    with pytest.raises(LstimSyntaxError):
        parse_ast(source, "bad.lstim")


@pytest.mark.parametrize("statement", [
    "DETECTOR rec[-1]", "TICK", "DEPOLARIZE1(0.1) D", "R D", "RX D",
    "OBSERVABLE_INCLUDE(0) rec[-1]", "MPP X0*X1", "eval D", "H D+1",
    "H D mode=__import__('os')", "H D mode=${value}", 'H D mode="frame"',
])
def test_physical_stim_and_expression_injection_are_rejected(statement):
    with pytest.raises(LstimSyntaxError):
        parse_ast("FORMAT(1)\n" + statement)


def test_syntax_does_not_validate_or_execute_quantum_semantics():
    tree = parse_ast("""FORMAT(99)
H missing another
CODE sc ROTATED_SURFACE(0)
PATCH P0 missing_code index=0
INIT_Z(0) never_bound
REPEAT 0 {
    MZ[duplicate] never_bound strange=true strange=7
}
PARALLEL {
}
""")
    assert tree.format_version == 99
    assert tree.statements[0].targets == ("missing", "another")
    assert tree.statements[4].count == 0
    assert tree.statements[-1].operations == ()
