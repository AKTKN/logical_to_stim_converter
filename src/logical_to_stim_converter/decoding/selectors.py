"""Semantic detector membership independent of geometric coordinate guesses."""

from collections.abc import Callable
from dataclasses import dataclass, field

from ..core.compiler_context import DetectorInfo
from ..core.lifecycle import BlockUseId
from .errors import DecoderViewError


@dataclass(frozen=True)
class DetectorSelector:
    """AND filters, with union membership within each blocks/stages tuple.

    Blocks select all occupancies of a physical site. use_ids selects explicit
    BlockUseIds independently: anchor (default), touching (any source), or strict
    (all sources). These filters intersect with physical-block and stage filters.
    Stages: touching (default), anchor, or strict. None is an ordinary stage ID.
    basis describes the physical check at the semantic anchor, including H.
    Arbitrary unions and custom predicates operate on public DetectorInfo values.
    """

    block_ids: tuple[str, ...] | None = None
    block_membership: str = "anchor"
    stage_ids: tuple[str | None, ...] | None = None
    stage_membership: str = "touching"
    basis: str | None = None
    predicate: Callable[[DetectorInfo], bool] | None = field(default=None, repr=False)
    description: str = "semantic selection"
    use_ids: tuple[BlockUseId, ...] | None = None
    use_membership: str = "anchor"

    def __post_init__(self):
        if self.basis not in (None, "X", "Z"):
            raise DecoderViewError("Check basis must be X or Z")
        for kind in ("block", "stage", "use"):
            if getattr(self, kind + "_membership") not in ("anchor", "touching", "strict"):
                raise DecoderViewError("Membership must be anchor, touching, or strict")
            value = getattr(self, kind + "_ids")
            if value is not None:
                object.__setattr__(self, kind + "_ids", tuple(value))
        if self.use_ids is not None and any(not isinstance(u, BlockUseId) for u in self.use_ids):
            raise DecoderViewError("use_ids must contain immutable BlockUseId values")

    def __call__(self, detector):
        """Evaluate semantic membership against historical canonical detector metadata."""
        for requested, membership, anchor, support in (
            (
                self.block_ids,
                self.block_membership,
                detector.block_id,
                detector.supporting_block_ids,
            ),
            (self.stage_ids, self.stage_membership, detector.stage_id, detector.source_stage_ids),
            (self.use_ids, self.use_membership, detector.anchor_use_id, detector.source_use_ids),
        ):
            if requested is None:
                continue
            region = set(requested)
            matches = (
                anchor in region
                if membership == "anchor"
                else set(support) <= region
                if membership == "strict"
                else bool(set(support) & region)
            )
            if not matches:
                return False
        return (self.basis is None or detector.basis == self.basis) and (
            self.predicate is None or bool(self.predicate(detector))
        )

    def __or__(self, other):
        """Union two semantic predicates without imposing a new region boundary."""
        if not isinstance(other, DetectorSelector):
            return NotImplemented
        return DetectorSelector(
            predicate=lambda d: self(d) or other(d), description=f"({self!r}) OR ({other!r})"
        )
