"""Canonical logical source, preserving order, explicit defaults and block structure."""

from dataclasses import fields

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
    StatementNode,
)
from .errors import LSTIMSemanticError, LstimSyntaxError
from .parser import parse_ast
from .program import LogicalProgram
from .semantics import MAX_EXPANDED_OPERATIONS, validate_ast

_NODES = (FileNode, HeaderNode, CodeNode, PatchNode, BindNode, OperationNode,
          OptionNode, ParallelNode, RepeatNode)


def _semantic_signature(value: object) -> tuple:
    """Retain every typed field and ordered member except diagnostic SourceSpans."""
    if type(value) in _NODES:
        return (type(value), tuple(
            (field.name, _semantic_signature(getattr(value, field.name)))
            for field in fields(value) if field.name != "span"
        ))
    if type(value) is tuple:
        return (tuple, tuple(_semantic_signature(item) for item in value))
    if value is None or type(value) in (str, int, bool):
        return (type(value), value)
    raise TypeError("AST fields must contain immutable typed syntax values")


def _lines(node: StatementNode, depth: int = 0) -> list[str]:
    indent = "    " * depth
    if isinstance(node, CodeNode):
        text = f"CODE {node.alias} {node.family}({node.distance})"
    elif isinstance(node, PatchNode):
        text = f"PATCH {node.physical_id} {node.code_alias} index={node.index}"
    elif isinstance(node, BindNode):
        text = f"BIND {node.logical_id} {node.physical_id}"
    elif isinstance(node, OperationNode):
        text = node.opcode
        if node.label is not None:
            text += f"[{node.label}]"
        if node.rounds is not None:
            text += f"({node.rounds})"
        text += " " + " ".join(node.targets)
        for option in node.options:
            value = str(option.value).lower() if type(option.value) is bool else str(option.value)
            text += f" {option.name}={value}"
    elif isinstance(node, (ParallelNode, RepeatNode)):
        if isinstance(node, ParallelNode):
            text, children = "PARALLEL", node.operations
        else:
            text, children = f"REPEAT {node.count}", node.body
        lines = [indent + text + " {"]
        for child in children:
            lines.extend(_lines(child, depth + 1))
        return [*lines, indent + "}"]
    else:
        raise TypeError("Unsupported AST statement")
    return [indent + text]


def format_logical_circuit(program: LogicalProgram | FileNode) -> str:
    """Return valid v1 source with four-space indentation, LF and a final newline.

    Comments and blank lines are discarded. No defaults are inserted and repeats
    remain nested. Raw ASTs undergo static validation and a grammar round trip;
    this checks source semantics, not physical lifecycle or stabilizer flows.
    """
    if not isinstance(program, (LogicalProgram, FileNode)):
        raise TypeError("format_logical_circuit expects LogicalProgram or FileNode")
    ast = program.ast if isinstance(program, LogicalProgram) else program
    source = program.source if isinstance(program, LogicalProgram) else ""
    span = ast.span if isinstance(ast.span, SourceSpan) else None
    try:
        # A program has already passed its caller-selected expansion budget.
        budget = max(MAX_EXPANDED_OPERATIONS, program.expanded_operation_count) if isinstance(
            program, LogicalProgram,
        ) else MAX_EXPANDED_OPERATIONS
        validate_ast(ast, source, max_operations=budget)
        signature = _semantic_signature(ast)
        lines = [f"FORMAT({ast.format_version})"]
        for statement in ast.statements:
            lines.extend(_lines(statement))
        formatted = "\n".join(lines) + "\n"
        reparsed = parse_ast(formatted, ast.span.source_name)
        if signature != _semantic_signature(reparsed):
            raise ValueError("AST fields change meaning when rendered as source")
        return formatted
    except LSTIMSemanticError:
        raise
    except (LstimSyntaxError, AttributeError, TypeError, ValueError, RecursionError) as error:
        raise LSTIMSemanticError(
            f"Malformed AST cannot be formatted as LSTIM v1: {str(error)[:160]}", span, source,
        ) from error
