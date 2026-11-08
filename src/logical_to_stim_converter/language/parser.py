"""Syntax-only text entrypoint; semantic validation and lowering are separate."""

from lark import Tree

from ._syntax import _token_stream
from .ast_nodes import FileNode
from .transformer import AstTransformer


def parse_ast(source: str, source_name: str = "<string>") -> FileNode:
    """Parse one bounded LSTIM document without initializing or allocating qubits.

    A successful parse guarantees syntax only. Version support, declarations,
    signatures, option legality and resource/quantum lifecycle belong to later
    semantic validation and the existing physical compiler.
    """
    for item in _token_stream(source, source_name):
        if isinstance(item, Tree):
            return AstTransformer(source, source_name).transform(item)
    raise AssertionError("contextual parser did not produce a tree")
