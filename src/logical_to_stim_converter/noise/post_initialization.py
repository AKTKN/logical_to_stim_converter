"""Explicit, use-bound post-initialization channels, independent of Bell policy."""

from dataclasses import dataclass, replace

from ..core.lifecycle import BlockUseId
from ..core.logical_block import GlobalSiteId


@dataclass(frozen=True)
class PostInitializationBoundary:
    """An exclusive ideal prefix and exact selected-circuit stochastic location."""

    operation_id: str
    preparation_module_id: str
    block_use_id: BlockUseId
    final_se_layer: int
    ideal_boundary_instruction: int
    data_sites: tuple[GlobalSiteId, ...]
    probability: float
    channel_instruction: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "data_sites", tuple(tuple(s) for s in self.data_sites))

    @property
    def channel_tag(self):
        return f"initialization_post_se:{self.preparation_module_id}"


def resolve_post_initialization_boundaries(compiled, policies):
    """Resolve exact operation/use pairs after verified ideal physical assembly."""
    if not policies:
        return ()
    result = []
    ticks, layer = {}, 0
    for i, inst in enumerate(compiled.ideal_circuit):
        if inst.name == "TICK":
            ticks[layer] = i + 1
            layer += 1
    for policy in policies:
        matches = [
            f
            for f in compiled.fragments
            if f.operation_id == policy.operation_id
            and policy.block_use_id in f.block_use_ids
            and f.operation_type == "LogicalInit"
        ]
        if len(matches) != 1:
            raise ValueError("Post-initialization policy must match one LogicalInit operation/use")
        fragment = matches[0]
        prep = next(p for p in compiled.preparations if p.module_id == fragment.module_id)
        records = [m for m in compiled.measurements if m.module_id == fragment.module_id]
        final = max(m.time_layer for m in records)
        if final not in ticks:
            if final != len(compiled.time_layers) - 1:
                raise ValueError("Initialization has no final SE boundary")
            ticks[final] = len(compiled.ideal_circuit)
        result.append(
            PostInitializationBoundary(
                fragment.operation_id,
                fragment.module_id,
                policy.block_use_id,
                final,
                ticks[final],
                tuple((prep.block_id, q) for q in prep.data_ids),
                policy.probability,
            )
        )
    return tuple(result)


def validate_post_initialization_provenance(compiled):
    """Audit cuts, targets, exact probabilities, multiplicity and instruction positions."""
    from .model import PostInitializationNoise

    boundaries = compiled.post_initialization_boundaries
    if not boundaries:
        if any(i.tag.startswith("initialization_post_se:") for i in compiled.circuit):
            raise ValueError("Post-initialization channels have no boundary provenance")
        return
    expected = resolve_post_initialization_boundaries(
        compiled,
        tuple(
            PostInitializationNoise(b.operation_id, b.block_use_id, b.probability)
            for b in boundaries
        ),
    )
    if tuple(replace(b, channel_instruction=None) for b in boundaries) != expected:
        raise ValueError("Post-initialization boundary disagrees with operation/use provenance")
    actual = {
        i.tag: n
        for n, i in enumerate(compiled.circuit)
        if i.tag.startswith("initialization_post_se:")
    }
    if actual != {b.channel_tag: b.channel_instruction for b in boundaries if b.probability}:
        raise ValueError("Post-initialization channel provenance disagrees")
    layer, cut = 0, {}
    for n, inst in enumerate(compiled.circuit):
        if inst.name == "TICK":
            cut[layer] = n + 1
            layer += 1
    tags = {b.channel_tag for b in boundaries}
    tags.update(b.channel_tag for b in compiled.resource_preparation_boundaries)
    if boundaries and layer not in cut:
        cut[layer] = min(
            (
                b.channel_instruction
                for b in boundaries
                if b.final_se_layer == layer and b.channel_instruction is not None
            ),
            default=len(compiled.circuit),
        )
    for b in boundaries:
        if not b.probability:
            if b.channel_instruction is not None:
                raise ValueError("Zero post-initialization probability has a channel")
            continue
        i = b.channel_instruction
        inst = compiled.circuit[i]
        if (
            inst.name != "DEPOLARIZE1"
            or inst.gate_args_copy() != [b.probability]
            or tuple(t.value for t in inst.targets_copy())
            != tuple(compiled.physical_qubit_map[s] for s in b.data_sites)
            or i < cut[b.final_se_layer]
            or any(s.tag not in tags for s in compiled.circuit[cut[b.final_se_layer] : i])
        ):
            raise ValueError("Invalid post-initialization location, targets or probability")
    if sum(i.tag.startswith("initialization_post_se:") for i in compiled.circuit) != len(actual):
        raise ValueError("Duplicate post-initialization channels")
