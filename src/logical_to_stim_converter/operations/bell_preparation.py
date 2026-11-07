"""Encoded Bell resource from concurrent X/Z preparations and a shared CNOT."""

from dataclasses import dataclass

from ..core.code_spec import positive_int
from .composite import CompositeOperation, CompositeStep
from .initialization import LogicalInit
from .transversal import TransversalCNOT


@dataclass(frozen=True, init=False)
class BellStatePrep(CompositeOperation):
    rounds: int | None

    def __init__(self, first, second, rounds=None, *, noise=None, operation_id=None):
        object.__setattr__(self, "targets", (first, second))
        object.__setattr__(self, "rounds", rounds)
        object.__setattr__(self, "noise", noise)
        object.__setattr__(self, "operation_id", operation_id)
        self.__post_init__()
        if rounds is not None:
            positive_int(rounds, "rounds")

    def expand(self, context):
        a, b = self.targets
        blocks = [context.block_for(q) for q in self.targets]
        if blocks[0].code.d != blocks[1].code.d:
            raise ValueError("Bell resources require compatible equal-distance blocks")
        rounds = self.rounds if self.rounds is not None else blocks[0].code.d
        return (
            CompositeStep((LogicalInit(a, "X", rounds, noise=self.noise),
                           LogicalInit(b, "Z", rounds, noise=self.noise)), "resource_prep"),
            CompositeStep((TransversalCNOT(a, b, noise=self.noise),), "resource_entangling"),
        )
