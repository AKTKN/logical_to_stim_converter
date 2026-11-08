"""LSTIM syntax, static validation and lowering through existing Python operations.

PATCH declares fixed physical sites; BIND only reserves one for a logical state.
An epoch begins with an actual initialization reset. A stage is a compiler QEC
region, independent of a source label. REPEAT preserves a nested static sequence;
logical PARALLEL groups operations, while the physical compiler owns TICK timing.
Parsing alone establishes none of these state/lifecycle properties.
"""

from .errors import (
    LSTIMCompileError,
    LSTIMError,
    LSTIMFileError,
    LSTIMSemanticError,
    LstimSyntaxError,
)
from .formatter import format_logical_circuit
from .lexer import lex_source
from .parser import parse_ast
from .program import LogicalProgram, parse_logical_circuit, parse_logical_file

__all__ = [
    "LogicalProgram", "parse_logical_circuit", "parse_logical_file", "format_logical_circuit",
    "LSTIMError", "LstimSyntaxError", "LSTIMSemanticError", "LSTIMCompileError", "LSTIMFileError",
    "lex_source", "parse_ast",
]
