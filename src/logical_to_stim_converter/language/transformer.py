"""Convert a positional Lark tree to immutable syntax data without physical imports."""

from dataclasses import dataclass
from typing import Any

from lark import Token, Transformer_NonRecursive, v_args
from lark.tree import Meta

from .ast_nodes import (
    BindNode,
    CodeNode,
    FileNode,
    HeaderNode,
    OperationNode,
    OptionNode,
    ParallelNode,
    PatchNode,
    RepeatNode,
    SourceSpan,
)


@dataclass(frozen=True)
class _Label:
    value: str


@dataclass(frozen=True)
class _Rounds:
    value: int


@v_args(meta=True)
class AstTransformer(Transformer_NonRecursive):
    """Build syntax nodes iteratively, including deeply nested bounded repeats."""

    def __init__(self, source: str, source_name: str) -> None:
        super().__init__()
        self.source = source
        self.source_name = source_name

    def _span(self, meta: Meta) -> SourceSpan:
        return SourceSpan(
            self.source_name, meta.line, meta.column, meta.end_line, meta.end_column,
            meta.start_pos, meta.end_pos,
        )

    def start(self, meta: Meta, children: list[Any]) -> FileNode:
        return FileNode(
            children[0], tuple(children[1:]),
            SourceSpan.from_offsets(self.source, self.source_name, 0, len(self.source)),
        )

    def header(self, meta: Meta, children: list[Token]) -> HeaderNode:
        return HeaderNode(int(children[0]), self._span(meta))

    def code_decl(self, meta: Meta, children: list[Token]) -> CodeNode:
        return CodeNode(str(children[0]), "ROTATED_SURFACE", int(children[1]), self._span(meta))

    def patch_decl(self, meta: Meta, children: list[Token]) -> PatchNode:
        return PatchNode(str(children[0]), str(children[1]), int(children[2]), self._span(meta))

    def bind(self, meta: Meta, children: list[Token]) -> BindNode:
        return BindNode(str(children[0]), str(children[1]), self._span(meta))

    def label(self, meta: Meta, children: list[Token]) -> _Label:
        return _Label(str(children[0]))

    def rounds(self, meta: Meta, children: list[Token]) -> _Rounds:
        return _Rounds(int(children[0]))

    def name_value(self, meta: Meta, children: list[Token]) -> str:
        return str(children[0])

    def int_value(self, meta: Meta, children: list[Token]) -> int:
        return int(children[0])

    def true_value(self, meta: Meta, children: list[Token]) -> bool:
        return True

    def false_value(self, meta: Meta, children: list[Token]) -> bool:
        return False

    def option(self, meta: Meta, children: list[Any]) -> OptionNode:
        return OptionNode(str(children[0]), children[1], self._span(meta))

    def operation(self, meta: Meta, children: list[Any]) -> OperationNode:
        targets = []
        options = []
        label = rounds = None
        for child in children[1:]:
            if isinstance(child, _Label):
                label = child.value
            elif isinstance(child, _Rounds):
                rounds = child.value
            elif isinstance(child, OptionNode):
                options.append(child)
            else:
                targets.append(str(child))
        return OperationNode(
            str(children[0]), tuple(targets), rounds, tuple(options), label, self._span(meta),
        )

    def parallel(self, meta: Meta, children: list[OperationNode]) -> ParallelNode:
        return ParallelNode(tuple(children), self._span(meta))

    def repeat(self, meta: Meta, children: list[Any]) -> RepeatNode:
        return RepeatNode(int(children[0]), tuple(children[1:]), self._span(meta))
