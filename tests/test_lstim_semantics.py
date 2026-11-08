"""Static source validation and pre-allocation expansion limits, without physics."""

from dataclasses import replace

import pytest

from logical_to_stim_converter.language import parse_ast
from logical_to_stim_converter.language.ast_nodes import ParallelNode, RepeatNode
from logical_to_stim_converter.language.errors import LSTIMError, LSTIMSemanticError
from logical_to_stim_converter.language.semantics import MAX_EXPANDED_OPERATIONS, validate_ast

DECLARATIONS = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
PATCH P1 sc index=1
PATCH P2 sc index=2
"""
BOUND = DECLARATIONS + "BIND D P0\nBIND A P1\nBIND B P2\n"


def validate(source, **kwargs):
    return validate_ast(parse_ast(source, "semantic.lstim"), source, **kwargs)


@pytest.mark.parametrize("text,reason", [
    ("FORMAT(0)", "FORMAT version"), ("FORMAT(2)", "FORMAT version"),
    ("FORMAT(1)", "at least one physical PATCH"),
    ("FORMAT(1)\nCODE sc ROTATED_SURFACE(3)", "at least one physical PATCH"),
    ("FORMAT(1)\nCODE sc ROTATED_SURFACE(3)\nCODE sc ROTATED_SURFACE(5)", "Duplicate code"),
    (DECLARATIONS + "PATCH P0 sc index=3", "Duplicate physical patch"),
    (DECLARATIONS + "PATCH P3 sc index=0", "Duplicate patch placement"),
    ("FORMAT(1)\nPATCH P0 missing index=0", "Unknown preceding code"),
    ("FORMAT(1)\nPATCH P0 sc index=0\nCODE sc ROTATED_SURFACE(3)", "Unknown preceding code"),
    (BOUND + "CODE later ROTATED_SURFACE(3)", "declarations must precede"),
    (BOUND + "PATCH P3 sc index=3", "declarations must precede"),
    (DECLARATIONS + "BIND D missing", "Unknown physical patch"),
    (DECLARATIONS + "H D", "Unknown logical handle"),
    (DECLARATIONS + "INIT_Z(1) P0", "Unknown logical handle"),
    (BOUND + "CX D missing", "Unknown logical handle"),
    (BOUND + "SE(1) future\nBIND future P0", "Unknown logical handle"),
])
def test_versions_declarations_names_and_order(text, reason):
    with pytest.raises(LSTIMSemanticError, match=reason) as caught:
        validate(text)
    error = caught.value
    assert error.source_name == "semantic.lstim"
    assert error.line >= 1 and error.column >= 1
    assert error.excerpt and "^" in error.caret


@pytest.mark.parametrize("distance", [0, 1, 2, 4, 6])
def test_invalid_distances(distance):
    with pytest.raises(LSTIMSemanticError, match="odd integer >= 3"):
        validate(f"FORMAT(1)\nCODE sc ROTATED_SURFACE({distance})")


@pytest.mark.parametrize("opcode,arity,rounds", [
    ("INIT_Z", 1, "(1)"), ("INIT_X", 1, "(1)"), ("SE", 1, "(1)"),
    ("H", 1, ""), ("CX", 2, ""), ("X", 1, ""), ("Y", 1, ""), ("Z", 1, ""),
    ("MX", 1, ""), ("MZ", 1, ""), ("BELL_PREP", 2, ""), ("KNILL_EC", 3, ""),
])
def test_exact_opcode_arity(opcode, arity, rounds):
    targets = ("D", "A", "B", "extra")[:arity + 1]
    with pytest.raises(LSTIMSemanticError, match=f"exactly {arity} target"):
        validate(BOUND + f"{opcode}{rounds} " + " ".join(targets))
    if arity > 1:
        with pytest.raises(LSTIMSemanticError, match=f"exactly {arity} target"):
            validate(BOUND + f"{opcode}{rounds} D")


@pytest.mark.parametrize("opcode", ["INIT_Z", "INIT_X", "SE"])
def test_required_rounds(opcode):
    with pytest.raises(LSTIMSemanticError, match="requires explicit"):
        validate(BOUND + f"{opcode} D")


@pytest.mark.parametrize("command", [
    "INIT_Z(0) D", "INIT_X(0) D", "SE(0) D", "BELL_PREP(0) A B", "KNILL_EC(0) D A B",
    "H(1) D", "CX(1) D A", "X(1) D", "Y(1) D", "Z(1) D", "MX(1) D", "MZ(1) D",
    "CX D D", "BELL_PREP A A", "KNILL_EC D A A",
])
def test_rounds_and_repeated_operands(command):
    with pytest.raises(LSTIMSemanticError):
        validate(BOUND + command)


@pytest.mark.parametrize("command,reason", [
    ("H D mode=frame", "does not accept option"),
    ("X D unknown=frame", "does not accept option"),
    ("X D mode=frame mode=physical", "Duplicate option"),
    ("MX D mode=random mode=random", "Duplicate option"),
    ("X D mode=random", "mode must be physical"),
    ("X D mode=true", "mode must be physical"),
    ("X D mode=1", "mode must be physical"),
    ("MZ D mode=frame", "mode must be deterministic"),
    ("MZ D mode=0", "mode must be deterministic"),
    ("KNILL_EC D A B prepare_resource=1", "must be true or false"),
    ("KNILL_EC D A B prepare_resource=False", "must be true or false"),
    ("KNILL_EC D A B prepare_resource=maybe", "must be true or false"),
    ("KNILL_EC(3) D A B prepare_resource=false", "unused rounds"),
    ("BELL_PREP A B prepare_resource=true", "does not accept option"),
    ("SE(1) D rounds=3", "does not accept option"),
    ("INIT_Z(1) D epoch=1", "does not accept option 'epoch'"),
    ("KNILL_EC D A B epoch=0", "does not accept option 'epoch'"),
])
def test_option_legality_types_duplicates_and_no_epoch_override(command, reason):
    with pytest.raises(LSTIMSemanticError, match=reason):
        validate(BOUND + command)


@pytest.mark.parametrize("command", [
    "KNILL_EC D A B", "KNILL_EC(3) D A B prepare_resource=true",
    "KNILL_EC D A B prepare_resource=false", "BELL_PREP A B", "BELL_PREP(5) A B",
    "X D mode=physical", "Y D mode=frame", "Z D", "MX D mode=random", "MZ D",
])
def test_valid_options_and_optional_composite_rounds(command):
    assert validate(BOUND + command).expanded_operation_count == 4


def test_option_errors_point_at_the_actual_option_on_crlf_source():
    source = (BOUND + "X D mode=frame mode=physical").replace("\n", "\r\n")
    with pytest.raises(LSTIMSemanticError) as caught:
        validate(source)
    error = caught.value
    assert (error.line, error.column) == (9, 16)
    assert error.span.end_column == 29
    assert source[error.span.start_offset:error.span.end_offset] == "mode=physical"
    assert "semantic.lstim:9:16" in str(error)
    assert str(error).endswith("               ^")


def test_labels_are_unique_across_sequential_and_parallel_operations():
    source = BOUND + "H[tag] D\nPARALLEL {\n X[tag] D\n H A\n}"
    with pytest.raises(LSTIMSemanticError, match="Duplicate source label 'tag'"):
        validate(source)


@pytest.mark.parametrize("command", [
    "INIT_Z(1) D", "INIT_X(1) D", "MZ D", "MX D", "BELL_PREP A B", "KNILL_EC D A B",
    "H[label] D", "SE[label](1) D",
])
def test_repeat_resource_changes_and_labels_are_rejected_even_in_nested_groups(command):
    source = BOUND + f"REPEAT 1 {{\n REPEAT 2 {{\n {command}\n }}\n}}"
    with pytest.raises(LSTIMSemanticError, match="forbidden inside REPEAT"):
        validate(source)
    if command.split()[0].split("(")[0].split("[")[0] not in {"BELL_PREP", "KNILL_EC"}:
        source = BOUND + f"REPEAT 2 {{\nPARALLEL {{\n{command}\nH A\n}}\n}}"
        with pytest.raises(LSTIMSemanticError, match="forbidden inside REPEAT"):
            validate(source)


@pytest.mark.parametrize("body", ["PARALLEL {\n}", "PARALLEL {\nH D\n}", "REPEAT 2 {\n}"])
def test_nonempty_repeat_and_minimum_parallel_size(body):
    with pytest.raises(LSTIMSemanticError):
        validate(BOUND + body)


def test_repeat_cost_counts_occurrences_members_and_bindings_without_materialization():
    source = BOUND + "REPEAT 2 {\nSE(1) D\nREPEAT 3 {\nPARALLEL {\nH D\nX A\n}\n}\n}"
    result = validate(source, max_operations=17)
    assert result.expanded_operation_count == 3 + 2 * (1 + 3 * 2) == 17
    with pytest.raises(LSTIMSemanticError, match="exceeds 16"):
        validate(source, max_operations=16)


@pytest.mark.parametrize("count", [0, MAX_EXPANDED_OPERATIONS + 1, 10**127])
def test_bad_repeat_counts_fail_without_expansion(count):
    with pytest.raises(LSTIMSemanticError):
        validate(BOUND + f"REPEAT {count} {{\nH D\n}}")


def test_nested_repeat_multiplication_and_whole_program_sum_are_bounded():
    with pytest.raises(LSTIMSemanticError, match="Expansion exceeds"):
        validate(BOUND + "REPEAT 99999 {\nREPEAT 99999 {\nH D\n}\n}")
    with pytest.raises(LSTIMSemanticError, match="Expansion exceeds"):
        validate(BOUND + "REPEAT 2 {\nH D\n}\nREPEAT 2 {\nX D\n}", max_operations=6)
    assert validate(BOUND + "REPEAT 99997 {\nH D\n}").expanded_operation_count == 100_000


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_configured_limits(limit):
    with pytest.raises(ValueError, match="max_operations"):
        validate(BOUND, max_operations=limit)


@pytest.mark.parametrize("command", [
    "DETECTOR rec[-1]", "TICK", "R D", "OBSERVABLE_INCLUDE(0) rec[-1]", "DEPOLARIZE1(1) D",
    "BIND D P0 epoch=1", "PATCH P3 sc index=3 epoch=1", "SE(-1) D", "REPEAT -1 {\nH D\n}",
    "FORMAT(1)", "REPEAT 2 {\nBIND Q P0\n}",
])
def test_invalid_syntax_is_rejected_before_semantics(command):
    with pytest.raises(LSTIMError) as caught:
        validate(BOUND + command)
    assert caught.value.source_name == "semantic.lstim"
    assert caught.value.span is not None


def test_semantics_does_not_allocate_physical_objects_or_duplicate_lifecycle(monkeypatch):
    from logical_to_stim_converter import CodeSpec, LogicalBlock

    def forbidden(*args, **kwargs):
        raise AssertionError("static validation allocated physical objects")

    monkeypatch.setattr(CodeSpec, "rotated_surface", forbidden)
    monkeypatch.setattr(LogicalBlock, "placed", forbidden)
    # These names are known, but the physical state machine must reject them later.
    source = BOUND + "H D\nMZ D\nH D\nBIND D P0\nBIND other P0"
    assert validate(source).expanded_operation_count == 8


@pytest.mark.parametrize("change", [
    {"opcode": "TICK"}, {"rounds": True}, {"rounds": -1}, {"rounds": 1.5},
])
def test_manual_ast_cannot_bypass_signature_validation(change):
    source = BOUND + "SE(1) D"
    ast = parse_ast(source)
    bad = replace(ast.statements[-1], **change)
    with pytest.raises(LSTIMSemanticError):
        validate_ast(replace(ast, statements=(*ast.statements[:-1], bad)), source)


def test_manual_ast_cannot_hide_binding_declaration_composite_or_excess_nesting():
    source = BOUND + "H D"
    ast = parse_ast(source)
    operation = ast.statements[-1]
    for forbidden in (ast.statements[0], ast.statements[-2]):
        repeat = RepeatNode(1, (forbidden,), operation.span)
        with pytest.raises(LSTIMSemanticError):
            validate_ast(replace(ast, statements=(*ast.statements[:-1], repeat)), source)
    composite = replace(operation, opcode="BELL_PREP", targets=("D", "A"))
    parallel = ParallelNode((operation, composite), operation.span)
    with pytest.raises(LSTIMSemanticError, match="primitive operations only"):
        validate_ast(replace(ast, statements=(*ast.statements[:-1], parallel)), source)
    nested = operation
    for _ in range(65):
        nested = RepeatNode(1, (nested,), operation.span)
    with pytest.raises(LSTIMSemanticError, match="Block nesting"):
        validate_ast(replace(ast, statements=(*ast.statements[:-1], nested)), source)
