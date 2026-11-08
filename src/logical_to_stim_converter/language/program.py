"""Immutable validated logical programs and a thin bridge to the physical compiler.

A logical handle identifies a state through teleportation; a PATCH fixes its
possible physical sites. BIND reserves a patch without reset or time. Only the
existing compiler's LogicalInit starts a physical-use epoch. A parallel tuple is
a logical grouping, while physical TICKs delimit gate/noise intervals and stages
name semantic QEC regions. Source labels identify operations, not epochs/stages.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .ast_nodes import FileNode, SourceSpan
from .errors import LSTIMCompileError
from .lowering import ProgramEntry, SourceEntry, lower_ast
from .parser import parse_ast
from .semantics import MAX_EXPANDED_OPERATIONS, validate_ast

if TYPE_CHECKING:
    from ..compiler.circuit_compiler import CompiledCircuit
    from ..core.logical_block import LogicalBlock
    from ..noise.model import NoiseModel


@dataclass(frozen=True, slots=True, init=False)
class LogicalProgram:
    """A statically validated source and immutable existing-Python operation program.

    Inspect blocks/operations without compilation. Compilation owns fresh state
    each time and delegates all quantum lifecycle/flow/geometry checks. Aligned
    operation_spans contain one span per entry, or a tuple for a parallel layer;
    label_spans maps only explicit source labels, never generated module IDs.
    """

    source: str
    ast: FileNode
    blocks: tuple[LogicalBlock, ...]
    operations: tuple[ProgramEntry, ...]
    operation_spans: tuple[SourceEntry, ...]
    label_spans: Mapping[str, SourceSpan]
    expanded_operation_count: int

    def __init__(
        self, source: str, source_name: str = "<string>",
        *, max_operations: int = MAX_EXPANDED_OPERATIONS,
    ) -> None:
        ast = parse_ast(source, source_name)
        validated = validate_ast(ast, source, max_operations=max_operations)
        lowered = lower_ast(validated)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "ast", ast)
        for field in ("blocks", "operations", "operation_spans", "label_spans"):
            object.__setattr__(self, field, getattr(lowered, field))
        object.__setattr__(self, "expanded_operation_count", validated.expanded_operation_count)

    @property
    def source_name(self) -> str:
        """Return the source file name or caller-provided diagnostic label."""
        return self.ast.span.source_name

    def to_operations(self) -> tuple[ProgramEntry, ...]:
        """Return the immutable ordered operations/directives and parallel tuples."""
        return self.operations

    def compile(
        self, *, noise_model: NoiseModel | None = None, allow_open_outputs: bool = False,
    ) -> CompiledCircuit:
        """Delegate once with empty initial reservations; return the standard artifact.

        Compiler validation errors retain their original exception/cause. The
        compiler does not expose a source-statement error marker, so this bridge
        reports the known file without guessing a line from implicit module IDs.
        """
        from ..compiler.circuit_compiler import CircuitCompiler

        try:
            compiler = CircuitCompiler(self.blocks, logical_to_block={})
            return compiler.compile(
                self.to_operations(), noise_model=noise_model,
                allow_open_outputs=allow_open_outputs,
            )
        except (ValueError, TypeError, NotImplementedError) as error:
            raise LSTIMCompileError(error, self.source_name) from error


def parse_logical_circuit(
    source: str, source_name: str = "<string>", *, max_operations: int = MAX_EXPANDED_OPERATIONS,
) -> LogicalProgram:
    """Parse, statically validate and lower text without building physical circuits.

    This language-namespace entrypoint precedes M8-C's package-root/file API and
    formatter. The operation budget counts BIND directives and parallel members.
    """
    return LogicalProgram(source, source_name, max_operations=max_operations)
