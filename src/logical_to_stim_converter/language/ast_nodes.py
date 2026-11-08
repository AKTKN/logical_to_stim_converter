"""Immutable syntax data, independent of quantum and decoder implementations."""

from dataclasses import dataclass, field
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Half-open source range with 1-based positions and code-point offsets.

    Offsets address the original source, including CRLF. They do not participate
    in equality, so equivalent LF/CRLF syntax retains equal line/column spans.
    """

    source_name: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_offset: int = field(compare=False)
    end_offset: int = field(compare=False)

    @classmethod
    def from_offsets(
        cls, source: str, source_name: str, start: int, end: int,
    ) -> "SourceSpan":
        """Locate a range in the original source; used for file/error boundaries."""
        return cls(
            source_name=source_name,
            start_line=source.count("\n", 0, start) + 1,
            start_column=start - source.rfind("\n", 0, start),
            end_line=source.count("\n", 0, end) + 1,
            end_column=end - source.rfind("\n", 0, end),
            start_offset=start,
            end_offset=end,
        )


@dataclass(frozen=True, slots=True)
class HeaderNode:
    """The required first FORMAT header; version support is checked separately."""

    version: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class CodeNode:
    """A mathematical code declaration with no constructed code object."""

    alias: str
    family: str
    distance: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class PatchNode:
    """A fixed physical patch declaration with an explicit placement index."""

    physical_id: str
    code_alias: str
    index: int
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class BindNode:
    """An ordered logical-to-physical reservation directive."""

    logical_id: str
    physical_id: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class OptionNode:
    """A named scalar option, preserving its spelling, type and source order."""

    name: str
    value: str | int | bool
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class OperationNode:
    """An operation signature without arity, option or lifecycle validation."""

    opcode: str
    targets: tuple[str, ...]
    rounds: int | None
    options: tuple[OptionNode, ...]
    label: str | None
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ParallelNode:
    """An ordered group of primitive operations at one logical boundary."""

    operations: tuple[OperationNode, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class RepeatNode:
    """An unexpanded nested sequence; no count-sized allocation occurs here."""

    count: int
    body: tuple["BodyStatement", ...]
    span: SourceSpan


BodyStatement: TypeAlias = OperationNode | ParallelNode | RepeatNode
StatementNode: TypeAlias = CodeNode | PatchNode | BindNode | BodyStatement


@dataclass(frozen=True, slots=True)
class FileNode:
    """A complete syntax-only document, including its explicit version header."""

    header: HeaderNode
    statements: tuple[StatementNode, ...]
    span: SourceSpan

    @property
    def format_version(self) -> int:
        """Return the declared version without asserting that it is supported."""
        return self.header.version
