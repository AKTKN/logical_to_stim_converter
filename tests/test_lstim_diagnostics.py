"""Source-aware invalid input and bounded syntactic resource handling."""

import os
import subprocess
import sys

import pytest

from logical_to_stim_converter.language import lex_source, parse_ast
from logical_to_stim_converter.language._syntax import (
    MAX_BLOCK_DEPTH,
    MAX_INTEGER_DIGITS,
    MAX_SOURCE_CHARS,
    MAX_TOKENS,
)
from logical_to_stim_converter.language.errors import (
    LstimLexError,
    LstimLimitError,
    LstimParseError,
    LstimSyntaxError,
)


@pytest.mark.parametrize("entrypoint", [parse_ast, lex_source])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_bad_character_has_file_line_column_and_caret(entrypoint, newline):
    source = newline.join(["# 日本語 allowed", "FORMAT(1)", "  H D @"])
    with pytest.raises(LstimLexError) as caught:
        entrypoint(source, "circuit.lstim")
    error = caught.value
    assert (error.source_name, error.line, error.column) == ("circuit.lstim", 3, 7)
    assert (error.span.end_line, error.span.end_column) == (3, 8)
    assert source[error.span.start_offset:error.span.end_offset] == "@"
    assert str(error) == (
        "circuit.lstim:3:7: unexpected character '@'\n  H D @\n      ^"
    )
    assert error.__cause__ is None
    assert error.__suppress_context__


@pytest.mark.parametrize("source,position", [
    ("", (1, 1)), ("# comment", (1, 10)), ("FORMAT(1)\nSE(", (2, 4)),
    ("FORMAT(1)\nREPEAT 2 {\nH D\n", (4, 1)),
    ("FORMAT(1)\r\nREPEAT 2 {\r\nH D\r\n", (4, 1)),
])
def test_eof_location_is_actual_end_of_original_source(source, position):
    with pytest.raises(LstimParseError, match="unexpected end of source") as caught:
        parse_ast(source, "eof.lstim")
    error = caught.value
    assert (error.line, error.column) == position
    assert error.span.start_offset == error.span.end_offset == len(source)
    assert str(error).endswith("^")


def test_bad_token_and_reserved_identifier_have_located_parse_errors():
    with pytest.raises(LstimParseError, match=r"bad.lstim:2:5: unexpected token '\]'"):
        parse_ast("FORMAT(1)\nH D ]", "bad.lstim")
    with pytest.raises(LstimParseError, match="reserved word 'H'") as caught:
        parse_ast("FORMAT(1)\nCODE H ROTATED_SURFACE(3)")
    assert (caught.value.line, caught.value.column) == (2, 6)


def test_caret_expands_tabs_and_clips_long_lines():
    source = "FORMAT(1)\n\tH D @"
    with pytest.raises(LstimSyntaxError) as caught:
        parse_ast(source)
    assert caught.value.column == 6
    assert caught.value.excerpt == "    H D @"
    assert caught.value.caret == "        ^"
    with pytest.raises(LstimSyntaxError) as caught:
        parse_ast("FORMAT(1)\nH " + "A" * 20_000 + " @")
    assert len(str(caught.value)) < 300
    assert caught.value.excerpt.endswith(" @")
    assert caught.value.caret.endswith("^")


def nested_source(depth):
    return "FORMAT(1)\n" + "REPEAT 2 {\n" * depth + "H D\n" + "}\n" * depth


@pytest.mark.parametrize("entrypoint", [parse_ast, lex_source])
def test_nesting_limit_is_located_before_recursive_failure(entrypoint):
    source = nested_source(MAX_BLOCK_DEPTH + 1)
    with pytest.raises(LstimLimitError, match="block nesting") as caught:
        entrypoint(source, "nested.lstim")
    assert caught.value.line == MAX_BLOCK_DEPTH + 2
    assert caught.value.column == 10
    assert caught.value.excerpt == "REPEAT 2 {"


def test_maximum_depth_and_large_counts_parse_without_unrolling():
    tree = parse_ast(nested_source(MAX_BLOCK_DEPTH))
    current, = tree.statements
    for _ in range(MAX_BLOCK_DEPTH):
        assert current.count == 2
        current, = current.body
    assert current.opcode == "H"
    big = "9" * MAX_INTEGER_DIGITS
    repeat, = parse_ast(f"FORMAT(1)\nREPEAT {big} {{\nH D\n}}").statements
    assert repeat.count == int(big)
    assert len(repeat.body) == 1


@pytest.mark.parametrize("entrypoint", [parse_ast, lex_source])
def test_integer_limit_avoids_python_int_digit_failure(entrypoint):
    source = "FORMAT(" + "9" * (MAX_INTEGER_DIGITS + 1) + ")"
    with pytest.raises(LstimLimitError, match="decimal digits") as caught:
        entrypoint(source, "digits.lstim")
    assert (caught.value.line, caught.value.column) == (1, 8)


@pytest.mark.parametrize("entrypoint", [parse_ast, lex_source])
def test_character_limit_includes_comments_and_has_bounded_diagnostic(entrypoint):
    with pytest.raises(LstimLimitError, match="characters") as caught:
        entrypoint("#" + "日" * (MAX_SOURCE_CHARS + 1), "large.lstim")
    assert caught.value.span.start_offset == MAX_SOURCE_CHARS
    assert len(str(caught.value)) < 300


def test_exact_character_limit_is_accepted():
    source = "FORMAT(1) #" + "a" * (MAX_SOURCE_CHARS - len("FORMAT(1) #"))
    assert parse_ast(source).format_version == 1


@pytest.mark.parametrize("entrypoint", [parse_ast, lex_source])
def test_token_budget_includes_blank_lines(entrypoint):
    with pytest.raises(LstimLimitError, match="tokens") as caught:
        entrypoint("FORMAT(1)\n" + "\n" * MAX_TOKENS, "tokens.lstim")
    assert caught.value.line > 1
    assert caught.value.span.source_name == "tokens.lstim"


def test_exact_token_budget_and_wide_targets_do_not_use_recursive_transforms():
    # Five header tokens (including newline), one opcode and NAME tokens.
    tree = parse_ast("FORMAT(1)\nH " + " ".join(["D"] * (MAX_TOKENS - 6)))
    assert len(tree.statements[0].targets) == MAX_TOKENS - 6


def test_exception_can_be_displayed_without_lark_traceback():
    source = "FORMAT(1)\nSE( D"
    try:
        parse_ast(source, "display.lstim")
    except LstimSyntaxError as error:
        diagnostic = str(error)
    assert diagnostic.startswith("display.lstim:2:")
    assert "SE( D\n" in diagnostic
    assert "^" in diagnostic
    assert "Traceback" not in diagnostic
    assert "Unexpected" not in diagnostic


def test_ast_values_are_reproducible_across_hash_seeds():
    script = (
        "from logical_to_stim_converter.language import parse_ast; "
        "print(repr(parse_ast('FORMAT(1)\\nX[label] D mode=frame extra=true')))"
    )
    results = []
    for seed in ("7", "123"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        result = subprocess.run(
            [sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True,
        )
        results.append(result.stdout)
    assert results[0] == results[1]
