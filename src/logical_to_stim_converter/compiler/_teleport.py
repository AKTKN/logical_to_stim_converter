"""Composite semantic boundaries; physical gadgets remain primitive operations."""

from dataclasses import replace

import stim

from ..core.compiler_context import BlockStatus, MeasurementKey, ParityExpression, PauliFrame
from ..core.protocol import (
    BellMeasurementResult,
    CompositeInfo,
    PhysicalPauliFrame,
    RelocationRecord,
)
from ..operations.bell_preparation import BellStatePrep
from ..operations.knill_ec import KnillEC


class ProtocolAssembly:
    def __init__(self, backend):
        self.backend = backend
        self.starts = {}
        self.composites = []
        self.relocations = []
        self.bells = []

    def begin(self, boundary, context):
        op = boundary.operation
        blocks = tuple(context.block_for(q).block_id for q in op.targets)
        if isinstance(op, BellStatePrep):
            if any(context.status[b] != BlockStatus.UNINITIALIZED for b in blocks):
                raise ValueError("BellStatePrep requires two uninitialized resources")
        elif isinstance(op, KnillEC):
            if context.status[blocks[0]] != BlockStatus.ACTIVE:
                raise ValueError("KnillEC requires active input data")
            expected = BlockStatus.UNINITIALIZED if op.prepare_resource else BlockStatus.ACTIVE
            if any(context.status[b] != expected for b in blocks[1:]):
                raise ValueError(f"KnillEC resources must be {expected.value}")
            if not op.prepare_resource:
                for axis in "XZ":
                    p = stim.PauliString(len(context.observable_ids))
                    for q in op.targets[1:]:
                        p[context.observable_ids[q]] = axis
                    if context.logical_state.peek_observable_expectation(p) != 1:
                        raise ValueError("Existing resource must have intended Bell XX=ZZ=+1")
        self.starts[boundary.identity] = (blocks, context.frames[op.targets[0]])

    def end(self, boundary, context, tracker, fragments):
        op, identity = boundary.operation, boundary.identity
        children = tuple(dict.fromkeys(f.operation_id for f in fragments
                                      if identity in f.composite_ids))
        self.composites.append(CompositeInfo(
            identity, op.operation_type,
            (() if isinstance(op, BellStatePrep) else
             op.targets[:1] if op.prepare_resource else op.targets),
            op.targets[:1] if isinstance(op, KnillEC) else op.targets, children))
        if not isinstance(op, KnillEC):
            return None
        (db, ab, bb), incoming = self.starts[identity]
        d, a, b = op.targets
        readouts = [next(f for f in reversed(fragments)
                         if f.operation_type == "LogicalMeasure" and f.logical_id == q)
                    for q in (d, a)]
        parities = []
        for q, bid, axis, f in zip((d, a), (db, ab), "XZ", readouts, strict=True):
            block = context.blocks[bid]
            at = {block.position(local): local for local in block.layout.data_ids}
            p = self.backend.logical_pauli(block, q, axis, f.orientations_before[0])
            parities.append(ParityExpression(tuple(
                MeasurementKey(bid, at[pos], "readout") for pos in p)))
        mx, mz = parities
        fd, fa, fb = (context.frames[q] for q in (d, a, b))
        output_frame = replace(fd.with_parities(fa.x ^ fb.x ^ mz, fd.z ^ fb.z ^ mx),
                               preparation_syndromes=tuple(dict.fromkeys(
                                   fd.preparation_syndromes + fa.preparation_syndromes
                                   + fb.preparation_syndromes)))
        orientation = context.orientations[b]
        draft = dict(composite_id=identity, logical_id=d, data_block_id=db,
                     first_resource_block_id=ab, output_block_id=bb,
                     x_readout=readouts[0].module_id, z_readout=readouts[1].module_id,
                     incoming_frame=incoming,
                     raw_byproduct=PauliFrame().with_parities(mz, mx),
                     output_orientation=orientation, logical_output_frame=output_frame,
                     preparation_dependencies=tuple(f.module_id for f in fragments
                                                    if f.operation_type == "LogicalInit"))
        self.bells.append(draft)
        self.relocations.append(RelocationRecord(identity, d, db, bb, (a, b)))
        # The semantic channel on the persistent input is identity. Undo only
        # the internal ideal Bell-measurement CX in the intended-state oracle;
        # unrelated concurrent computation and reference entanglement survive.
        context.logical_state.cx(context.observable_ids[d], context.observable_ids[a])
        for q in (a, b):
            del context.logical_to_block[q]
        context.logical_to_block[d] = bb
        context.frames[d] = output_frame
        context.orientations[d] = orientation
        # The physical-state tracker followed the actual measurement branches.
        # Rename its surviving B slot to the persistent D identity.
        tracker.logical_state.swap(context.observable_ids[d], context.observable_ids[b])
        tracker.active.remove(b)
        tracker.active.add(d)
        tracker.orientations[d] = orientation
        return draft

    def finalize(self, preparations, readouts):
        by_module = {r.module_id: r for r in readouts}
        return tuple(BellMeasurementResult(
            **{**draft, "x_readout": by_module[draft["x_readout"]],
               "z_readout": by_module[draft["z_readout"]]},
            physical_output_frame=PhysicalPauliFrame(
                draft["output_block_id"], draft["output_orientation"], draft["composite_id"],
                draft["composite_id"] + "/teleportation",
                tuple(k for p in preparations
                      if p.module_id in draft["preparation_dependencies"]
                      for k in p.unresolved_frame.source_syndromes))) for draft in self.bells)
