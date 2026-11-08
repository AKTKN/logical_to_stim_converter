"""Diagnostic tokenization using the same contextual grammar as AST parsing."""

from dataclasses import dataclass

from lark import Token

from ._syntax import _token_stream
from .ast_nodes import SourceSpan


@dataclass(frozen=True, slots=True)
class SourceToken:
    """A grammar token with its original spelling and half-open source location."""

    type: str
    value: str
    span: SourceSpan


def lex_source(source: str, source_name: str = "<string>") -> tuple[SourceToken, ...]:
    """Tokenize and check grammatical context without building a typed AST.

    Contextual tokens require parser state, so malformed statement structure also
    raises a located syntax error. Whitespace/comments are ignored; newlines stay.
    """
    tokens = []
    for item in _token_stream(source, source_name):
        if isinstance(item, Token):
            tokens.append(SourceToken(
                type=item.type,
                value=str(item),
                span=SourceSpan(
                    source_name, item.line, item.column, item.end_line, item.end_column,
                    item.start_pos, item.end_pos,
                ),
            ))
    return tuple(tokens)
