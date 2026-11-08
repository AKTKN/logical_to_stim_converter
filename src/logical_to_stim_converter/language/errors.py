"""Located LSTIM syntax diagnostics without exposing Lark exception dumps."""

from .ast_nodes import SourceSpan


class LstimSyntaxError(ValueError):
    """A lexical, grammatical or parser-budget error in user source."""

    def __init__(self, message: str, span: SourceSpan, source: str) -> None:
        self.message = message
        self.span = span
        self.source_name = span.source_name
        self.line = span.start_line
        self.column = span.start_column
        line_start = source.rfind("\n", 0, span.start_offset) + 1
        # Slice before expanding tabs, including when rejecting an oversized line.
        preview_start = max(line_start, span.start_offset - 60)
        preview_end = min(len(source), span.start_offset + 100)
        line = source[preview_start:preview_end].split("\n", 1)[0].rstrip("\r")
        caret_column = len(source[preview_start:span.start_offset].expandtabs(4))
        self.excerpt = line.expandtabs(4)
        self.caret = " " * caret_column + "^"
        super().__init__(
            f"{self.source_name}:{self.line}:{self.column}: {message}\n"
            f"{self.excerpt}\n{self.caret}"
        )


class LstimLexError(LstimSyntaxError):
    """A character or token that is not accepted at this source position."""


class LstimParseError(LstimSyntaxError):
    """A valid token in an invalid grammatical position, or unexpected EOF."""


class LstimLimitError(LstimSyntaxError):
    """A source exceeds a documented syntactic resource limit."""
