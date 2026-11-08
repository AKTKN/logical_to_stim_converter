"""LSTIM syntax, static validation and lowering through existing Python operations.

PATCH declares fixed physical sites; BIND only reserves one for a logical state.
An epoch begins with an actual initialization reset. A stage is a compiler QEC
region, independent of a source label. REPEAT preserves a nested static sequence;
logical PARALLEL groups operations, while the physical compiler owns TICK timing.
Parsing alone establishes none of these state/lifecycle properties.
"""

from .lexer import lex_source
from .parser import parse_ast
from .program import LogicalProgram, parse_logical_circuit

__all__ = ["LogicalProgram", "lex_source", "parse_ast", "parse_logical_circuit"]
