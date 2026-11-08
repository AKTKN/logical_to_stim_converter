"""Source-aware syntax/semantic diagnostics and preserved compiler failures."""

from .ast_nodes import SourceSpan


class LSTIMError(ValueError):
    """A source diagnostic; a missing span means only the file is known."""

    def __init__(
        self, message: str, span: SourceSpan | None, source: str,
        *, source_name: str = "<string>",
    ) -> None:
        self.message = message
        self.span = span
        self.source_name = span.source_name if span is not None else source_name
        if span is None:
            self.line = self.column = self.excerpt = self.caret = None
            super().__init__(f"{self.source_name}: {message}")
            return
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


class LstimSyntaxError(LSTIMError):
    """A lexical, grammatical or parser-budget error in user source."""


class LstimLexError(LstimSyntaxError):
    """A character or token that is not accepted at this source position."""


class LstimParseError(LstimSyntaxError):
    """A valid token in an invalid grammatical position, or unexpected EOF."""


class LstimLimitError(LstimSyntaxError):
    """A source exceeds a documented syntactic resource limit."""


class LSTIMSemanticError(LSTIMError):
    """An invalid declaration, name, signature, option or static expansion."""


class LSTIMFileError(LSTIMError):
    """An unreadable or non-UTF-8 source file, retaining the original exception."""

    def __init__(
        self, message: str, original_error: OSError | UnicodeDecodeError,
        source_name: str, *, span: SourceSpan | None = None, source: str = "",
    ) -> None:
        self.original_error = original_error
        super().__init__(message, span, source, source_name=source_name)


class LSTIMCompileError(LSTIMError):
    """An existing compiler validation failure, without guessed source locations."""

    def __init__(self, original_error: Exception, source_name: str) -> None:
        self.original_error = original_error
        super().__init__(
            f"Physical compilation failed: {original_error}", None, "", source_name=source_name,
        )
