"""Shared grammar loading, bounded contextual tokenization and error conversion."""

import re
from collections.abc import Iterator
from functools import lru_cache
from importlib.resources import files

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedCharacters, UnexpectedInput, UnexpectedToken

from .ast_nodes import SourceSpan
from .errors import LstimLexError, LstimLimitError, LstimParseError, LstimSyntaxError

MAX_SOURCE_CHARS = 1_000_000
MAX_TOKENS = 100_000
MAX_BLOCK_DEPTH = 64
MAX_INTEGER_DIGITS = 128


@lru_cache(maxsize=1)
def _get_parser() -> Lark:
    """Load the installed grammar once; each parse owns its interactive state."""
    reserved: re.Pattern[str]

    def check_name(token: Token) -> Token:
        if reserved.fullmatch(str(token)):
            raise UnexpectedToken(token, expected={"NAME"})
        return token

    grammar = files(__package__).joinpath("grammar.lark").read_text(encoding="utf-8")
    parser = Lark(
        grammar, parser="lalr", lexer="contextual", propagate_positions=True,
        maybe_placeholders=False, lexer_callbacks={"NAME": check_name, "OPTION_KEY": check_name},
    )
    # Derive reserved words from grammar terminals instead of a second keyword list.
    reserved = re.compile("|".join(
        f"(?:{terminal.pattern.to_regexp()})"
        for terminal in parser.terminals
        if terminal.name not in {"NAME", "OPTION_KEY"}
    ))
    return parser


def _located_error(error: UnexpectedInput, source: str, source_name: str) -> LstimSyntaxError:
    if isinstance(error, UnexpectedToken) and error.token.type == "$END":
        start = end = len(source)
        message = "unexpected end of source; expected a statement or closing delimiter"
        error_type = LstimParseError
    elif isinstance(error, UnexpectedToken):
        start = error.token.start_pos
        end = error.token.end_pos
        value = str(error.token)
        if error.token.type in {"NAME", "OPTION_KEY"} and error.expected == {"NAME"}:
            message = f"reserved word {value!r} cannot be used as an identifier"
        else:
            message = f"unexpected token {value[:32]!r}"
        error_type = LstimParseError
    else:
        start = error.pos_in_stream
        end = min(len(source), start + 1)
        message = f"unexpected character {source[start:end]!r}"
        error_type = LstimLexError
    return error_type(message, SourceSpan.from_offsets(source, source_name, start, end), source)


def _token_stream(source: str, source_name: str) -> Iterator[Token | Tree]:
    """Yield checked tokens and then the completed tree using one contextual lexer."""
    if len(source) > MAX_SOURCE_CHARS:
        span = SourceSpan.from_offsets(source, source_name, MAX_SOURCE_CHARS, MAX_SOURCE_CHARS)
        raise LstimLimitError(f"source exceeds {MAX_SOURCE_CHARS} characters", span, source)
    interactive = _get_parser().parse_interactive(source)
    depth = 0
    try:
        for count, token in enumerate(interactive.iter_parse(), start=1):
            message = None
            if count > MAX_TOKENS:
                message = f"source exceeds {MAX_TOKENS} tokens"
            elif token.type == "INT" and len(token) > MAX_INTEGER_DIGITS:
                message = f"integer exceeds {MAX_INTEGER_DIGITS} decimal digits"
            elif token.type == "LBRACE":
                depth += 1
                if depth > MAX_BLOCK_DEPTH:
                    message = f"block nesting exceeds {MAX_BLOCK_DEPTH} levels"
            elif token.type == "RBRACE":
                depth -= 1
            if message is not None:
                span = SourceSpan.from_offsets(source, source_name, token.start_pos, token.end_pos)
                raise LstimLimitError(message, span, source)
            yield token
        yield interactive.feed_eof()
    except (UnexpectedCharacters, UnexpectedToken) as error:
        raise _located_error(error, source, source_name) from None
