"""Single Knill teleportation; correction selection stays outside the circuit."""

from dataclasses import dataclass

from ..core.code_spec import positive_int
from .bell_preparation import BellStatePrep
from .composite import CompositeOperation, CompositeStep
from .measurement import LogicalMeasure
from .transversal import TransversalCNOT


@dataclass(frozen=True, init=False)
class KnillEC(CompositeOperation):
    prepare_resource: bool
    rounds: int | None

    def __init__(self, data, first_resource, output_resource, *, prepare_resource=True,
                 rounds=None, noise=None, operation_id=None):
        object.__setattr__(self, "targets", (data, first_resource, output_resource))
        object.__setattr__(self, "prepare_resource", prepare_resource)
        object.__setattr__(self, "rounds", rounds)
        object.__setattr__(self, "noise", noise)
        object.__setattr__(self, "operation_id", operation_id)
        self.__post_init__()
        if type(prepare_resource) is not bool:
            raise ValueError("prepare_resource must be a boolean")
        if rounds is not None:
            positive_int(rounds, "rounds")

    def expand(self, context):
        d, a, b = self.targets
        if len({context.block_for(q).code.d for q in self.targets}) != 1:
            raise ValueError("Knill EC requires compatible equal-distance blocks")
        prep = (CompositeStep((BellStatePrep(a, b, self.rounds, noise=self.noise),),
                              "resource"),) if self.prepare_resource else ()
        return prep + (
            CompositeStep((TransversalCNOT(d, a, noise=self.noise),), "teleportation"),
            CompositeStep((LogicalMeasure(d, "X", mode="random", noise=self.noise),
                           LogicalMeasure(a, "Z", mode="random", noise=self.noise)),
                          "teleportation"),
        )
