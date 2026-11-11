"""Immutable Bell-resource cuts resolved from verified physical/use provenance."""

from dataclasses import dataclass, replace

import stim

from ..core.lifecycle import BlockUseId
from ..core.logical_block import GlobalSiteId


@dataclass(frozen=True)
class ResourcePreparationBoundary:
    """One reset-to-final-SE use; the stochastic channel follows its existing TICK.

    ideal_boundary_instruction is an exclusive ideal prefix, including final-layer
    idle accounting at injection time. channel_instruction indexes the canonical
    noisy circuit, or is None for enabled zero-probability preparation. Data sites
    retain physical keys, never inferred from current logical owners or geometry.
    """

    bell_preparation_id: str
    preparation_module_id: str
    block_use_id: BlockUseId
    resource_entangling_module_id: str
    first_layer: int
    final_se_layer: int
    ideal_boundary_instruction: int
    data_sites: tuple[GlobalSiteId, ...]
    channel_instruction: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "data_sites", tuple(tuple(s) for s in self.data_sites))

    @property
    def channel_tag(self):
        """Distinct stochastic provenance, never a primitive gate's module tag."""
        return f"resource_post_se:{self.preparation_module_id}"


def resolve_resource_preparation_boundaries(compiled, blocks=None):
    """Resolve each explicit BellStatePrep's two initializations in one indexed pass.

    Reject malformed structural/use/physical relationships instead of guessing a
    time cut. This resolver never recognizes a bare pair of initializations.
    """
    physical, measurements, ticks = {}, {}, {}
    module_ids = {f.module_id for f in compiled.fragments}
    layer = 0
    for i, inst in enumerate(compiled.ideal_circuit):
        if isinstance(inst, stim.CircuitRepeatBlock):
            raise ValueError("Resource boundaries require an expanded physical schedule")
        if inst.name == "TICK":
            ticks[layer] = i + 1
            layer += 1
        elif inst.tag in module_ids:
            physical.setdefault(inst.tag, []).append((i, layer, inst.name))
            if stim.gate_data(inst.name).produces_measurements:
                measurements.setdefault(inst.tag, []).append((i, layer))
    boundaries, seen_modules, seen_uses = [], set(), set()
    composites = {c.composite_id: c for c in compiled.composites}
    if len(composites) != len(compiled.composites):
        raise ValueError("Duplicate composite identity in resource preparation")
    for composite in compiled.composites:
        if composite.operation_type != "BellStatePrep":
            continue
        children = [f for f in compiled.fragments if composite.composite_id in f.composite_ids]
        if (tuple(f.operation_type for f in children)
                != ("LogicalInit", "LogicalInit", "TransversalCNOT")
                or tuple(f.operation_id for f in children) != composite.child_operation_ids
                or any(f.composite_ids[-1] != composite.composite_id for f in children)):
            raise ValueError("Ambiguous BellStatePrep primitive membership")
        a, b, entangle = children
        if (len(a.block_use_ids) != 1 or len(b.block_use_ids) != 1
                or entangle.block_use_ids != (*a.block_use_ids, *b.block_use_ids)
                or len(set(entangle.block_use_ids)) != 2):
            raise ValueError("Bell preparation requires two distinct verified preparation use IDs")
        for f, basis in ((a, "X"), (b, "Z")):
            use = f.block_use_ids[0]
            matches = [p for p in compiled.preparations if p.module_id == f.module_id]
            if (len(matches) != 1 or matches[0].block_use_id != use
                    or matches[0].basis != basis or use.block_id != f.block_id):
                raise ValueError("Bell preparation metadata disagrees with its primitive/use")
            prep = matches[0]
            data_ids = blocks[use.block_id].layout.data_ids if blocks is not None else prep.data_ids
            if prep.data_ids != data_ids:
                raise ValueError("Bell preparation data sites disagree with the physical layout")
            if f.module_id in seen_modules or use in seen_uses:
                raise ValueError("Duplicate resource preparation module/use epoch")
            seen_modules.add(f.module_id)
            seen_uses.add(use)
            ops = physical.get(f.module_id, ())
            ms = measurements.get(f.module_id, ())
            cx = physical.get(entangle.module_id, ())
            if (not ops or not ms or not cx or ops[0][2] not in ("R", "RX")
                    or ops[-1][0] != ms[-1][0] or ms[-1][1] not in ticks):
                raise ValueError("Resource preparation has no unique final SE/TICK boundary")
            stop = ticks[ms[-1][1]]
            if stop > cx[0][0]:
                raise ValueError("Resource post-SE boundary must precede resource CNOT")
            records = [m for m in compiled.measurements if m.module_id == f.module_id]
            if (not records or any(m.key.block_use_id != use or m.key.kind != "syndrome"
                                   for m in records)
                    or max(m.time_layer for m in records) != ms[-1][1]):
                raise ValueError("Resource SE records disagree with the preparation use/boundary")
            sites = tuple((use.block_id, q) for q in data_ids)
            if any(s not in compiled.physical_qubit_map for s in sites):
                raise ValueError("Resource data injection sites are missing from the physical map")
            indices = [compiled.physical_qubit_map[s] for s in sites]
            if len(set(indices)) != len(indices):
                raise ValueError("Duplicate resource data injection sites")
            boundaries.append(ResourcePreparationBoundary(
                composite.composite_id, f.module_id, use, entangle.module_id,
                ops[0][1], ms[-1][1], stop, sites,
            ))
    return tuple(boundaries)


def validate_resource_preparation_provenance(compiled):
    """Audit public immutable cuts and exact stochastic locations without private state.

    All channels at a shared cut are contiguous after the existing final-layer
    TICK. A preparation prefix therefore stops before every post-SE channel.
    """
    boundaries = compiled.resource_preparation_boundaries
    actual, tick_stops, first_gate = {}, {}, {}
    layer = 0
    for i, inst in enumerate(compiled.circuit):
        if inst.tag.startswith("resource_post_se:"):
            if inst.tag in actual:
                raise ValueError("Duplicate resource post-SE stochastic provenance")
            actual[inst.tag] = i
        if inst.name == "TICK":
            tick_stops[layer] = i + 1
            layer += 1
        elif inst.tag:
            first_gate.setdefault(inst.tag, i)
    if not boundaries:
        if actual:
            raise ValueError("Resource post-SE channels have no preparation boundary provenance")
        return
    expected = resolve_resource_preparation_boundaries(compiled)
    if tuple(replace(b, channel_instruction=None) for b in boundaries) != expected:
        raise ValueError("Resource preparation boundary disagrees with structural/use provenance")
    if actual != {b.channel_tag: b.channel_instruction for b in boundaries
                  if b.channel_instruction is not None}:
        raise ValueError("Resource post-SE channel instruction provenance disagrees")
    tags = {b.channel_tag for b in boundaries}
    tags.update(b.channel_tag for b in compiled.post_initialization_boundaries)
    presence = {}
    for b in boundaries:
        index = b.channel_instruction
        presence.setdefault(b.bell_preparation_id, []).append(index is not None)
        if index is None:
            continue
        inst = compiled.circuit[index]
        targets = tuple(compiled.physical_qubit_map[s] for s in b.data_sites)
        if (inst.name != "DEPOLARIZE1" or tuple(t.value for t in inst.targets_copy()) != targets
                or not inst.gate_args_copy() or inst.gate_args_copy()[0] == 0):
            raise ValueError("Resource post-SE channel must target each physical data site once")
        stop = tick_stops[b.final_se_layer]
        if (index < stop or index >= first_gate[b.resource_entangling_module_id]
                or any(i.tag not in tags for i in compiled.circuit[stop:index])):
            raise ValueError("Resource post-SE channel must immediately follow final SE/TICK, "
                             "before resource CNOT")
    if any(any(v) != all(v) for v in presence.values()):
        raise ValueError("Both resource post-SE channels must be present together")
