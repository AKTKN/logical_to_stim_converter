"""Translate statically validated syntax into existing operations and fixed patches."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, TypeAlias

from .ast_nodes import (
    BindNode,
    CodeNode,
    OperationNode,
    ParallelNode,
    PatchNode,
    RepeatNode,
    SourceSpan,
    StatementNode,
)
from .errors import LSTIMSemanticError
from .semantics import ValidatedAst

if TYPE_CHECKING:
    from ..core.logical_block import LogicalBlock
    from ..operations.base import OperationModule
    from ..operations.binding import BindPatch

ProgramEntry: TypeAlias = "OperationModule | BindPatch | tuple[OperationModule, ...]"
SourceEntry: TypeAlias = SourceSpan | tuple[SourceSpan, ...]


@dataclass(frozen=True, slots=True)
class LoweredProgram:
    """Immutable existing-Python program with aligned source entries and labels."""

    blocks: tuple[LogicalBlock, ...]
    operations: tuple[ProgramEntry, ...]
    operation_spans: tuple[SourceEntry, ...]
    label_spans: Mapping[str, SourceSpan]


def lower_ast(validated: ValidatedAst) -> LoweredProgram:
    """Construct fixed patches and statically unroll a previously bounded AST.

    Every occurrence gets a fresh existing operation object. Parallel groups stay
    separate tuples; BIND remains a directive and never becomes an initial map.
    Physical imports are deferred so syntax-only clients remain independent.
    """
    from ..core.code_spec import CodeSpec
    from ..core.logical_block import LogicalBlock
    from ..operations.bell_preparation import BellStatePrep
    from ..operations.binding import BindPatch
    from ..operations.initialization import LogicalInit
    from ..operations.knill_ec import KnillEC
    from ..operations.measurement import LogicalMeasure
    from ..operations.pauli import LogicalPauli
    from ..operations.syndrome_extraction import SyndromeExtraction
    from ..operations.transversal import TransversalCNOT, TransversalH

    codes = {}
    blocks = []
    labels = {}
    for node in validated.ast.statements:
        try:
            if isinstance(node, CodeNode):
                codes[node.alias] = CodeSpec.rotated_surface(node.distance)
            elif isinstance(node, PatchNode):
                blocks.append(LogicalBlock.placed(
                    node.physical_id, codes[node.code_alias], patch_index=node.index,
                ))
        except ValueError as error:
            raise LSTIMSemanticError(str(error), node.span, validated.source) from error

    def operation(node: OperationNode) -> OperationModule:
        """Use the existing constructors with exact source flags, order and defaults."""
        options = {option.name: option.value for option in node.options}
        kwargs = {"operation_id": node.label}
        if node.label is not None:
            labels[node.label] = node.span
        try:
            if node.opcode in {"INIT_Z", "INIT_X"}:
                return LogicalInit(node.targets[0], node.opcode[-1], node.rounds, **kwargs)
            if node.opcode == "SE":
                return SyndromeExtraction(node.targets[0], node.rounds, **kwargs)
            if node.opcode == "H":
                return TransversalH(node.targets[0], **kwargs)
            if node.opcode == "CX":
                return TransversalCNOT(*node.targets, **kwargs)
            if node.opcode in {"X", "Y", "Z"}:
                return LogicalPauli(
                    node.targets[0], node.opcode, mode=options.get("mode", "physical"), **kwargs,
                )
            if node.opcode in {"MX", "MZ"}:
                return LogicalMeasure(
                    node.targets[0], node.opcode[-1],
                    mode=options.get("mode", "deterministic"), **kwargs,
                )
            if node.opcode == "BELL_PREP":
                return BellStatePrep(*node.targets, node.rounds, **kwargs)
            if node.opcode == "KNILL_EC":
                return KnillEC(
                    *node.targets, rounds=node.rounds,
                    prepare_resource=options.get("prepare_resource", True), **kwargs,
                )
        except ValueError as error:
            raise LSTIMSemanticError(str(error), node.span, validated.source) from error
        raise LSTIMSemanticError(f"Unsupported opcode {node.opcode!r}", node.span, validated.source)

    def entries(nodes: tuple[StatementNode, ...]) -> Iterator[tuple[ProgramEntry, SourceEntry]]:
        """Yield the already bounded occurrences, retaining each sequential barrier."""
        for node in nodes:
            if isinstance(node, (CodeNode, PatchNode)):
                continue
            if isinstance(node, BindNode):
                yield BindPatch(node.logical_id, node.physical_id), node.span
            elif isinstance(node, OperationNode):
                yield operation(node), node.span
            elif isinstance(node, ParallelNode):
                yield (
                    tuple(operation(op) for op in node.operations),
                    tuple(op.span for op in node.operations),
                )
            elif isinstance(node, RepeatNode):
                for _ in range(node.count):
                    yield from entries(node.body)

    operations = []
    spans = []
    for entry, span in entries(validated.ast.statements):
        operations.append(entry)
        spans.append(span)
    return LoweredProgram(tuple(blocks), tuple(operations), tuple(spans), MappingProxyType(labels))
