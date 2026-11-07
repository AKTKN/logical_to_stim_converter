"""Expand composites without erasing primitive identity, stages, or parallelism."""

from dataclasses import dataclass
from itertools import zip_longest

from ..operations.base import OperationModule
from ..operations.composite import CompositeOperation


@dataclass(frozen=True)
class PlannedOperation:
    operation: OperationModule
    identity: str
    stage: str | None
    parents: tuple[str, ...]


@dataclass(frozen=True)
class Boundary:
    operation: CompositeOperation
    identity: str


@dataclass(frozen=True)
class PlanStep:
    operations: tuple[PlannedOperation, ...] = ()
    before: tuple[Boundary, ...] = ()
    after: tuple[Boundary, ...] = ()


def plan_program(program, context):
    seen = set()
    counters = {"op": 0, "composite": 0}

    def identity(op, parents):
        kind = "composite" if isinstance(op, CompositeOperation) else "op"
        name = op.operation_id or f"{kind}{counters[kind]:04d}"
        counters[kind] += 1
        name = f"{parents[-1]}/{name}" if parents else name
        if name in seen:
            raise ValueError("Operation IDs must be unique within a compilation")
        seen.add(name)
        return name

    def expand(op, stage=None, parents=()):
        if not isinstance(op, OperationModule):
            raise ValueError("Each logical layer requires operation objects")
        name = identity(op, parents)
        if not isinstance(op, CompositeOperation):
            return [PlanStep((PlannedOperation(op, name, stage, parents),))]
        result = []
        for child in op.expand(context):
            child_stage = f"{name}/{child.stage}"
            streams = []
            for q in child.operations:
                local_stage = child_stage
                if child.stage == "resource_prep":
                    local_stage += ":" + q.targets[0]
                streams.append(expand(q, local_stage, (*parents, name)))
            result.extend(merge(streams))
        boundary = Boundary(op, name)
        first = result[0]
        result[0] = PlanStep(first.operations, (boundary, *first.before), first.after)
        last = result[-1]
        result[-1] = PlanStep(last.operations, last.before, (*last.after, boundary))
        return result

    def merge(streams):
        return [PlanStep(tuple(op for s in steps if s for op in s.operations),
                         tuple(b for s in steps if s for b in s.before),
                         tuple(b for s in steps if s for b in s.after))
                for steps in zip_longest(*streams)]

    result = []
    for entry in program:
        group = [entry] if isinstance(entry, OperationModule) else list(entry)
        if not group or any(not isinstance(op, OperationModule) for op in group):
            raise ValueError("Each logical layer requires operation objects")
        targets = [q for op in group for q in op.targets]
        if len(set(targets)) != len(targets):
            raise ValueError("A parallel layer operates on the same physical block twice")
        result.extend(merge([expand(op) for op in group]))
    return result
