"""Public imports, source-file diagnostics and unchanged ordinary compiled artifacts."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

import logical_to_stim_converter as public
from logical_to_stim_converter import (
    BindPatch,
    CompiledCircuit,
    LogicalProgram,
    LSTIMCompileError,
    LSTIMError,
    LSTIMFileError,
    LSTIMSemanticError,
    LstimSyntaxError,
    NoiseModel,
    format_logical_circuit,
    language,
    parse_logical_circuit,
    parse_logical_file,
)

MEMORY = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z[init](3) D
REPEAT 2 {
    SE(1) D
}
MZ[readout] D
"""


@pytest.mark.parametrize("name", [
    "LogicalProgram", "parse_logical_circuit", "parse_logical_file", "format_logical_circuit",
    "LSTIMError", "LstimSyntaxError", "LSTIMSemanticError", "LSTIMCompileError", "LSTIMFileError",
])
def test_root_and_language_export_the_same_public_objects(name):
    assert getattr(public, name) is getattr(language, name)
    assert name in public.__all__ and name in language.__all__
    assert not hasattr(public, "Lark")


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("as_string", [False, True])
def test_utf8_files_keep_names_and_original_codepoint_offsets(tmp_path, newline, as_string):
    path = tmp_path / "記憶 circuit.lstim"
    source = ("# 日本語 comment\n" + MEMORY).replace("\n", newline)
    path.write_bytes(source.encode("utf-8"))
    program = parse_logical_file(str(path) if as_string else path)
    assert isinstance(program, LogicalProgram)
    assert program.source == source and program.source_name == str(path)
    assert format_logical_circuit(program) == MEMORY
    span = program.label_spans["init"]
    assert span.source_name == str(path) and (span.start_line, span.start_column) == (6, 1)
    assert source[span.start_offset:span.end_offset] == "INIT_Z[init](3) D"


@pytest.mark.parametrize("source,error_type,line,word", [
    (MEMORY.replace("FORMAT(1)", "FORMAT(2)"), LSTIMSemanticError, 1, "version"),
    (MEMORY + "@\n", LstimSyntaxError, 10, "character"),
    (MEMORY.replace("mode=frame", "mode=invalid") + "X D mode=invalid\n",
     LSTIMSemanticError, 10, "physical|frame"),
    (MEMORY.replace("MZ[readout] D", "MZ[readout] unknown"), LSTIMSemanticError, 9, "BIND"),
])
def test_file_syntax_and_semantics_are_distinct_located_errors(
    tmp_path, source, error_type, line, word,
):
    path = tmp_path / "bad.lstim"
    path.write_bytes(source.encode("utf-8"))
    with pytest.raises(error_type) as caught:
        parse_logical_file(path)
    error = caught.value
    assert isinstance(error, LSTIMError)
    assert error.source_name == str(path) and error.line == line
    assert f"{path}:{line}:" in str(error) and word in str(error) and "^" in str(error)


@pytest.mark.parametrize("invalid", [b"\xff", b"\xe3\x81", b"\xc0\xaf"])
def test_invalid_encoding_reports_byte_and_character_location_and_cause(tmp_path, invalid):
    path = tmp_path / "encoding.lstim"
    prefix = "# 日本語\r\nFORMAT(1)\r\n# "
    path.write_bytes(prefix.encode("utf-8") + invalid)
    with pytest.raises(LSTIMFileError, match="Invalid UTF-8") as caught:
        parse_logical_file(path)
    error = caught.value
    assert error.original_error is error.__cause__
    assert isinstance(error.__cause__, UnicodeDecodeError)
    assert error.__cause__.start == len(prefix.encode("utf-8"))
    assert (error.line, error.column) == (3, 3)
    assert error.span.start_offset == len(prefix)
    assert f"{path}:3:3:" in str(error)


def test_missing_directory_and_inaccessible_paths_preserve_os_causes(tmp_path, monkeypatch):
    for path, cause in [(tmp_path / "missing.lstim", FileNotFoundError), (tmp_path, OSError)]:
        with pytest.raises(LSTIMFileError, match="Cannot read UTF-8") as caught:
            parse_logical_file(path)
        assert isinstance(caught.value.__cause__, cause)
        assert caught.value.original_error is caught.value.__cause__
        assert caught.value.source_name == str(path) and caught.value.line is None

    def denied(self):
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "read_bytes", denied)
    with pytest.raises(LSTIMFileError, match="Permission denied") as caught:
        parse_logical_file(tmp_path / "denied.lstim")
    assert isinstance(caught.value.__cause__, PermissionError)


def test_file_operation_budget_and_inspection_never_compile_or_sample(tmp_path, monkeypatch):
    path = tmp_path / "memory.lstim"
    path.write_text(MEMORY, encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("parse/inspect/format attempted physical compilation")

    monkeypatch.setattr(public.CircuitCompiler, "compile", forbidden)
    program = parse_logical_file(path, max_operations=5)
    assert program.expanded_operation_count == 5 and format_logical_circuit(program) == MEMORY
    assert program.to_operations()[0] == BindPatch("D", "P0")
    with pytest.raises(LSTIMSemanticError, match="Expansion exceeds 4"):
        parse_logical_file(path, max_operations=4)


def test_repeated_compilation_preserves_inputs_and_returns_standard_independent_artifacts():
    program = parse_logical_circuit(MEMORY)
    ast, blocks, operations = program.ast, program.blocks, program.to_operations()
    site_map = dict(blocks[0].site_map)
    matrix = blocks[0].code.H_X.copy()
    first = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.001))
    second = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.003))
    assert isinstance(first, CompiledCircuit) and isinstance(second, CompiledCircuit)
    assert first is not second and first.circuit != second.circuit
    assert first.ideal_circuit == second.ideal_circuit == program.compile().ideal_circuit
    assert (program.ast, program.blocks, program.to_operations()) == (ast, blocks, operations)
    assert dict(blocks[0].site_map) == site_map
    np.testing.assert_array_equal(blocks[0].code.H_X, matrix)
    assert format_logical_circuit(program) == MEMORY
    first.validate_metadata()
    second.validate_metadata()
    first.circuit.detector_error_model()
    view = first.make_decoder_view()
    assert view is not None and first.make_frame_plan() is not None
    events, observables = first.ideal_circuit.compile_detector_sampler(seed=123).sample(
        4, separate_observables=True,
    )
    assert not events.any() and not observables.any()
    first.circuit.append("X_ERROR", [0], 0.5)
    assert first.circuit != second.circuit
    repeated = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.003))
    assert repeated.circuit == second.circuit


def test_readonly_views_and_label_lookup_keep_source_order():
    program = parse_logical_circuit(MEMORY)
    assert tuple(program.label_spans) == ("init", "readout")
    assert [block.block_id for block in program.blocks] == ["P0"]
    assert program.operations is program.to_operations()
    assert [operation.operation_id for operation in program.operations[1:]] == [
        "init", None, None, "readout",
    ]
    for field in ["ast", "blocks", "operations", "label_spans"]:
        with pytest.raises(FrozenInstanceError):
            setattr(program, field, None)
    with pytest.raises(TypeError):
        program.label_spans["new"] = program.ast.span


def test_compile_errors_keep_physical_cause_and_known_source_without_guessing_line():
    program = parse_logical_circuit(
        MEMORY.replace("INIT_Z[init](3) D\n", ""), "uninitialized.lstim",
    )
    with pytest.raises(LSTIMCompileError) as caught:
        program.compile()
    error = caught.value
    assert error.__cause__ is error.original_error and isinstance(error.original_error, ValueError)
    assert error.source_name == "uninitialized.lstim" and error.line is None
    assert "Physical compilation failed" in str(error)
