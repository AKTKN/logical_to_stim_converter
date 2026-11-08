"""Grammar-backed contextual tokens, boundaries and installed grammar resources."""

import os
import subprocess
import sys
import zipfile
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from logical_to_stim_converter.language import lex_source
from logical_to_stim_converter.language.errors import LstimSyntaxError
from tests.helpers.package_build import copy_package_source


def test_tokens_labels_options_and_positions():
    source = "# 日本語 comment\nFORMAT(1)\n\tKNILL_EC[cycle0](03) D A B prepare_resource = false"
    tokens = lex_source(source, "memory.lstim")
    assert [(token.type, token.value) for token in tokens[6:]] == [
        ("COMPOSITE_OPCODE", "KNILL_EC"), ("LSQB", "["), ("NAME", "cycle0"),
        ("RSQB", "]"), ("LPAR", "("), ("INT", "03"), ("RPAR", ")"),
        ("NAME", "D"), ("NAME", "A"), ("NAME", "B"),
        ("OPTION_KEY", "prepare_resource"), ("EQUAL", "="), ("_FALSE", "false"),
    ]
    opcode = tokens[6]
    assert opcode.span.source_name == "memory.lstim"
    assert (opcode.span.start_line, opcode.span.start_column) == (3, 2)
    assert (opcode.span.end_line, opcode.span.end_column) == (3, 10)
    assert source[opcode.span.start_offset:opcode.span.end_offset] == "KNILL_EC"
    with pytest.raises(FrozenInstanceError):
        opcode.value = "H"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("ending", ["", "\n", " # final comment"])
def test_whitespace_comments_blank_lines_and_eof(newline, ending):
    source = " # comment\n\n FORMAT ( 1 )\n\n  H _Data1\n".replace("\n", newline)
    tokens = lex_source(source + "  X _Data1 mode=frame" + ending)
    assert [token.value for token in tokens if token.type == "NAME"] == [
        "_Data1", "_Data1", "frame",
    ]
    assert tokens[-1].span.start_line >= 6


@pytest.mark.parametrize("name", [
    "FORMAT", "CODE", "PATCH", "ROTATED_SURFACE", "BIND", "REPEAT", "PARALLEL",
    "INIT_Z", "INIT_X", "SE", "H", "CX", "X", "Y", "Z", "MX", "MZ",
    "BELL_PREP", "KNILL_EC", "index", "true", "false",
])
def test_reserved_words_are_never_contextually_reinterpreted_as_names(name):
    with pytest.raises(LstimSyntaxError, match="reserved word"):
        lex_source(f"FORMAT(1)\nH {name}")


@pytest.mark.parametrize("name", ["H2", "FORMAT_extra", "index0", "falsehood", "_", "D"])
def test_keyword_prefixes_and_case_sensitive_names(name):
    assert lex_source(f"FORMAT(1)\nH {name}")[-1].value == name


@pytest.mark.parametrize("source", [
    "FORMAT(1)\nH D@", "FORMAT(1)\nH データ", "FORMAT(1)\nH D\u00a0",
    "FORMAT(1e)", "FORMAT(1.5)", "FORMAT(0x1)", "FORMAT(+1)",
    "FORMAT(1)\nSE(2abc) D", "FORMAT(1)\nH[tag D", "FORMAT(1)\nSE(3 D",
    "FORMAT(1)\n}", "FORMAT(1)\nHD", "FORMAT(1)\nCODEsc ROTATED_SURFACE(3)",
    "FORMAT(1)\nH D mode=frame extra", "FORMAT(1)\nH D mode=\"frame\"",
])
def test_invalid_characters_numbers_and_structure(source):
    with pytest.raises(LstimSyntaxError):
        lex_source(source, "bad.lstim")


def test_grammar_has_no_lalr_conflicts(monkeypatch):
    from lark import Lark
    from lark.utils import logger

    from logical_to_stim_converter.language._syntax import _get_parser

    def fail_on_warning(*args, **kwargs):
        pytest.fail(str(args))

    # debug exposes conflicts as warnings without requiring optional interegular.
    monkeypatch.setattr(logger, "warning", fail_on_warning)
    Lark(_get_parser().source_grammar, parser="lalr", lexer="contextual", debug=True)


def test_isolated_wheel_contains_and_loads_grammar(tmp_path):
    """Build and import an isolated wheel with source access and physical imports blocked."""
    root = Path(__file__).resolve().parents[1]
    source_tree = copy_package_source(tmp_path / "source")
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(dist)],
        cwd=source_tree, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel, = dist.glob("*.whl")
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        grammar_path = "logical_to_stim_converter/language/grammar.lark"
        assert grammar_path in archive.namelist()
        archive.extractall(installed)
    script = r'''
import importlib.abc
import importlib.util
import pathlib
import sys
import types

wheel_root = pathlib.Path(sys.argv[1])
repo_root = pathlib.Path(sys.argv[2])
sys.path[:] = [p for p in sys.path if p and pathlib.Path(p) not in {repo_root, repo_root / "src"}]
sys.path.insert(0, str(wheel_root))
# Load the syntax package directly to prove its independence of the eager root API.
package = types.ModuleType("logical_to_stim_converter")
package.__path__ = [str(wheel_root / "logical_to_stim_converter")]
sys.modules[package.__name__] = package

class BlockPhysical(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"stim", "stimflow", "pymatching"}:
            raise AssertionError("syntax imported physical dependency " + fullname)
        if fullname.startswith("logical_to_stim_converter.") and not fullname.startswith(
            "logical_to_stim_converter.language"
        ):
            raise AssertionError("syntax imported physical package " + fullname)

blocker = BlockPhysical()
sys.meta_path.insert(0, blocker)
from logical_to_stim_converter.language import lex_source
import logical_to_stim_converter.language as language
assert pathlib.Path(language.__file__).is_relative_to(wheel_root)
assert lex_source("FORMAT(1)\nH D")[-1].value == "D"
from logical_to_stim_converter.language import parse_ast
assert parse_ast("FORMAT(1)\nH D").statements[0].opcode == "H"
sys.meta_path.remove(blocker)
del sys.modules[package.__name__]
import logical_to_stim_converter as real_package
assert pathlib.Path(real_package.__file__).is_relative_to(wheel_root)
print("isolated wheel grammar loaded")
'''
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(installed), str(root)],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "isolated wheel grammar loaded" in result.stdout
