"""Static v1 validation without physical allocation or quantum lifecycle tracking."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import NoReturn

from ._syntax import MAX_BLOCK_DEPTH
from .ast_nodes import (
    BindNode,
    CodeNode,
    FileNode,
    OperationNode,
    ParallelNode,
    PatchNode,
    RepeatNode,
    SourceSpan,
    StatementNode,
)
from .errors import LSTIMSemanticError

MAX_EXPANDED_OPERATIONS = 100_000
_SIGNATURES = MappingProxyType({
    "INIT_Z": (1, "required"), "INIT_X": (1, "required"), "SE": (1, "required"),
    "H": (1, "forbidden"), "CX": (2, "forbidden"),
    "X": (1, "forbidden"), "Y": (1, "forbidden"), "Z": (1, "forbidden"),
    "MX": (1, "forbidden"), "MZ": (1, "forbidden"),
    "BELL_PREP": (2, "optional"), "KNILL_EC": (3, "optional"),
})
_REPEAT_OPCODES = frozenset({"SE", "H", "CX", "X", "Y", "Z"})
_COMPOSITES = frozenset({"BELL_PREP", "KNILL_EC"})


@dataclass(frozen=True, slots=True)
class ValidatedAst:
    """Static validation result, retaining source and a precomputed expansion cost.

    This does not assert that any patch is available or that a logical state is
    initialized. Only the existing physical compiler can establish those facts.
    """

    ast: FileNode
    source: str
    expanded_operation_count: int


class _Validator:
    def __init__(self, source: str, max_operations: int) -> None:
        self.source = source
        self.max_operations = max_operations
        self.codes: set[str] = set()
        self.patches: set[str] = set()
        self.indices: set[int] = set()
        self.handles: set[str] = set()
        self.labels: set[str] = set()

    def fail(self, message: str, span: SourceSpan) -> NoReturn:
        raise LSTIMSemanticError(message, span, self.source)

    def declaration(self, node: CodeNode | PatchNode) -> None:
        if isinstance(node, CodeNode):
            if node.alias in self.codes:
                self.fail(f"Duplicate code alias {node.alias!r}", node.span)
            if node.family != "ROTATED_SURFACE":
                self.fail(f"Unsupported code family {node.family!r}", node.span)
            if type(node.distance) is not int or node.distance < 3 or node.distance % 2 != 1:
                self.fail("ROTATED_SURFACE distance must be an odd integer >= 3", node.span)
            self.codes.add(node.alias)
        else:
            if node.physical_id in self.patches:
                self.fail(f"Duplicate physical patch {node.physical_id!r}", node.span)
            if node.code_alias not in self.codes:
                self.fail(f"Unknown preceding code alias {node.code_alias!r}", node.span)
            if type(node.index) is not int or node.index < 0:
                self.fail("Patch index must be a nonnegative integer", node.span)
            if node.index in self.indices:
                self.fail(f"Duplicate patch placement index {node.index}", node.span)
            self.patches.add(node.physical_id)
            self.indices.add(node.index)

    def operation(self, node: OperationNode, *, in_repeat: bool) -> None:
        signature = _SIGNATURES.get(node.opcode)
        if signature is None:
            self.fail(f"Unsupported logical opcode {node.opcode!r}", node.span)
        arity, rounds = signature
        if len(node.targets) != arity:
            self.fail(f"{node.opcode} requires exactly {arity} target(s)", node.span)
        if len(set(node.targets)) != len(node.targets):
            self.fail(f"{node.opcode} requires distinct targets", node.span)
        if rounds == "required" and node.rounds is None:
            self.fail(f"{node.opcode} requires explicit (rounds)", node.span)
        if rounds == "forbidden" and node.rounds is not None:
            self.fail(f"{node.opcode} does not accept (rounds)", node.span)
        if node.rounds is not None and (type(node.rounds) is not int or node.rounds < 1):
            self.fail(f"{node.opcode} rounds must be a positive integer", node.span)
        if in_repeat and node.opcode not in _REPEAT_OPCODES:
            self.fail(f"{node.opcode} is forbidden inside REPEAT", node.span)
        if node.label is not None:
            if in_repeat:
                self.fail("Operation labels are forbidden inside REPEAT", node.span)
            if node.label in self.labels:
                self.fail(f"Duplicate source label {node.label!r}", node.span)
            self.labels.add(node.label)
        for target in node.targets:
            if target not in self.handles:
                self.fail(f"Unknown logical handle {target!r}; use a preceding BIND", node.span)
        options = {}
        for option in node.options:
            if option.name in options:
                self.fail(f"Duplicate option {option.name!r} on {node.opcode}", option.span)
            options[option.name] = option.value
            if option.name == "mode" and node.opcode in {"X", "Y", "Z", "MX", "MZ"}:
                modes = (
                    ("physical", "frame") if node.opcode in {"X", "Y", "Z"}
                    else ("deterministic", "random")
                )
                if type(option.value) is not str or option.value not in modes:
                    self.fail(f"{node.opcode} mode must be {'|'.join(modes)}", option.span)
            elif option.name == "prepare_resource" and node.opcode == "KNILL_EC":
                if type(option.value) is not bool:
                    self.fail("prepare_resource must be true or false", option.span)
            else:
                self.fail(f"{node.opcode} does not accept option {option.name!r}", option.span)
        if options.get("prepare_resource") is False and node.rounds is not None:
            self.fail("KNILL_EC prepare_resource=false cannot specify unused rounds", node.span)

    def statement(self, node: StatementNode, *, in_repeat: bool = False, depth: int = 0) -> int:
        if isinstance(node, OperationNode):
            self.operation(node, in_repeat=in_repeat)
            return 1
        if isinstance(node, BindNode):
            if in_repeat:
                self.fail("BIND is forbidden inside REPEAT", node.span)
            if node.physical_id not in self.patches:
                self.fail(f"Unknown physical patch {node.physical_id!r}", node.span)
            # This is name introduction only, not a map of active quantum states.
            self.handles.add(node.logical_id)
            return 1
        if isinstance(node, (CodeNode, PatchNode)):
            self.fail("Declarations are forbidden inside executable groups", node.span)
        if depth >= MAX_BLOCK_DEPTH:
            self.fail(f"Block nesting exceeds {MAX_BLOCK_DEPTH} levels", node.span)
        if isinstance(node, ParallelNode):
            if len(node.operations) < 2:
                self.fail("PARALLEL requires at least two primitive operations", node.span)
            for operation in node.operations:
                if not isinstance(operation, OperationNode) or operation.opcode in _COMPOSITES:
                    self.fail("PARALLEL contains primitive operations only", operation.span)
                self.operation(operation, in_repeat=in_repeat)
            cost = len(node.operations)
        elif isinstance(node, RepeatNode):
            if type(node.count) is not int or node.count < 1:
                self.fail("REPEAT count must be a positive integer", node.span)
            if not node.body:
                self.fail("REPEAT requires a nonempty body", node.span)
            body_cost = 0
            for child in node.body:
                body_cost += self.statement(child, in_repeat=True, depth=depth + 1)
                if body_cost > self.max_operations:
                    self.fail(f"Expansion exceeds {self.max_operations} operations", child.span)
            if body_cost > self.max_operations // node.count:
                self.fail(f"Expansion exceeds {self.max_operations} operations", node.span)
            cost = body_cost * node.count
        else:
            self.fail("Unsupported statement", node.span)
        if cost > self.max_operations:
            self.fail(f"Expansion exceeds {self.max_operations} operations", node.span)
        return cost


def validate_ast(
    ast: FileNode, source: str, *, max_operations: int = MAX_EXPANDED_OPERATIONS,
) -> ValidatedAst:
    """Validate static declarations/signatures and bound work before any unrolling.

    BIND introduces a name; availability, stale aliases, resets, entanglement,
    physical collisions and actual epochs remain the existing compiler's job.
    The budget counts concrete operations and BindPatch directives, including
    every member of a parallel group and every repeated occurrence.
    """
    if type(max_operations) is not int or max_operations < 1:
        raise ValueError("max_operations must be a positive integer")
    validator = _Validator(source, max_operations)
    if type(ast.format_version) is not int or ast.format_version != 1:
        validator.fail(
            f"Unsupported FORMAT version {ast.format_version!r}; expected 1", ast.header.span,
        )
    executable = False
    cost = 0
    for statement in ast.statements:
        if isinstance(statement, (CodeNode, PatchNode)):
            if executable:
                validator.fail(
                    "CODE/PATCH declarations must precede BIND and operations", statement.span,
                )
            validator.declaration(statement)
        else:
            executable = True
            cost += validator.statement(statement)
            if cost > max_operations:
                validator.fail(f"Expansion exceeds {max_operations} operations", statement.span)
    if not validator.patches:
        validator.fail("Declare at least one physical PATCH", ast.header.span)
    return ValidatedAst(ast, source, cost)
