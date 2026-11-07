"""Compile linear physical frame propagation once, outside any shot loop."""

import numpy as np

from ..decoding.frames import FrameBoundary, OfflineFramePlan
from ..decoding.records import GF2Map
from ..decoding.views import source_fingerprint


def make_frame_plan(compiled):
    if compiled._compiler is None:
        raise ValueError("A physical assembly history is required for frame propagation")
    records = compiled.measurement_index_by_key
    nq, nm = compiled.ideal_circuit.num_qubits, len(records)
    blocks = {b.block_id: b for b in compiled._compiler.blocks}
    positions = {
        b.position(q): compiled.physical_qubit_map[b.block_id, q]
        for b in blocks.values()
        for q in b.layout.qubit_ids
    }
    # Locate the last physical step of each ordinary SE module.
    last = {}
    for i, (kind, value) in enumerate(compiled._evaluation_steps):
        if kind == "physical":
            for inst in value.circuit:
                if inst.tag:
                    last[inst.tag] = i
    specs = []
    for prep in compiled.preparations:
        specs.append((prep.module_id, "physical", prep.block_id, prep.orientation, prep.data_ids))
    for f in compiled.fragments:
        if f.operation_type == "SyndromeExtraction":
            specs.append(
                (
                    f.module_id,
                    "physical",
                    f.block_id,
                    f.orientations_after[0],
                    blocks[f.block_id].layout.data_ids,
                )
            )
    for r in compiled.readouts:
        specs.append(
            (
                r.module_id,
                "readout",
                r.block_id,
                r.orientation,
                tuple(k.local_id for k in r.records),
            )
        )
    offsets, width = {}, nm
    for key, kind, _, _, data in specs:
        offsets[key] = (width, width + len(data) * (2 if kind == "physical" else 1))
        width = offsets[key][1]
    x = np.zeros((width + 1, nq), dtype=bool)
    z = x.copy()
    interpreted = np.zeros((width + 1, nm), dtype=bool)
    interpreted[:nm] = np.eye(nm, dtype=bool)
    readout_by_key = {r.module_id: r for r in compiled.readouts}
    # Readout hypotheses are raw record deltas, propagated through later Bell feedback.
    for key, kind, _, _, _ in specs:
        if kind == "readout":
            a, b = offsets[key]
            interpreted[np.arange(a, b), [records[k] for k in readout_by_key[key].records]] = True
    bells = {b.composite_id: b for b in compiled.bell_measurements}
    spec_by_key = {s[0]: s for s in specs}
    cursor = 0

    def toggle(pauli, condition):
        for position, axis in pauli.items():
            target = positions[position]
            if axis in "XY":
                x[:, target] ^= condition
            if axis in "ZY":
                z[:, target] ^= condition

    def inject(key):
        _, _, bid, _, data = spec_by_key[key]
        a, b = offsets[key]
        indices = [compiled.physical_qubit_map[bid, q] for q in data]
        n = len(data)
        x[np.arange(a, a + n), indices] ^= True
        z[np.arange(a + n, b), indices] ^= True

    for i, (kind, value) in enumerate(compiled._evaluation_steps):
        if kind == "physical":
            local = {j: positions[q] for q, j in value.q2i.items()}
            for inst in value.circuit:
                if inst.name == "TICK":
                    continue
                ts = [local[t.value] for t in inst.targets_copy()]
                if inst.name == "H":
                    old = x[:, ts].copy()
                    x[:, ts] = z[:, ts]
                    z[:, ts] = old
                elif inst.name == "CX":
                    c, t = ts[::2], ts[1::2]
                    x[:, t] ^= x[:, c]
                    z[:, c] ^= z[:, t]
                elif inst.name in ("R", "RX", "RY"):
                    x[:, ts] = z[:, ts] = False
                elif inst.name in ("M", "MX", "MY"):
                    flips = z[:, ts] if inst.name == "MX" else x[:, ts]
                    if inst.name == "MY":
                        flips = x[:, ts] ^ z[:, ts]
                    interpreted[:, cursor : cursor + len(ts)] ^= flips
                    cursor += len(ts)
                    x[:, ts] = z[:, ts] = False
                elif inst.name not in ("X", "Y", "Z"):
                    raise ValueError(f"Unsupported frame instruction {inst.name}")
            for key, k, _, _, _ in specs:
                if (
                    k == "physical"
                    and last.get(key) == i
                    and any(
                        f.module_id == key and f.operation_type == "SyndromeExtraction"
                        for f in compiled.fragments
                    )
                ):
                    inject(key)
        elif kind == "preparation":
            inject(value)
        elif kind == "virtual":
            bit = np.zeros(width + 1, dtype=bool)
            bit[-1] = True
            toggle(value, bit)
        elif kind == "teleport":
            bell = bells[value["composite_id"]]
            mx = bell.x_readout.logical_parity.evaluate(interpreted, records)
            mz = bell.z_readout.logical_parity.evaluate(interpreted, records)
            block = blocks[bell.output_block_id]
            for axis, bits in (("X", mz), ("Z", mx)):
                toggle(
                    compiled._compiler.backend.logical_pauli(
                        block, bell.logical_id, axis, bell.output_orientation
                    ),
                    bits,
                )
        else:
            raise ValueError("Unsupported frame boundary")
    if cursor != nm:
        raise ValueError("Physical frame replay lost measurement ordering")
    boundaries = []
    for key, kind, bid, orientation, data in specs:
        a, b = offsets[key]
        ids = (
            tuple(f"{axis}:{q}" for axis in "XZ" for q in data)
            if kind == "physical"
            else tuple(f"record:{q}" for q in data)
        )
        boundaries.append(
            FrameBoundary(
                key,
                kind,
                bid,
                orientation,
                data,
                ids,
                GF2Map.from_matrix(interpreted[a:b]),
                GF2Map.from_matrix(x[a:b]),
                GF2Map.from_matrix(z[a:b]),
            )
        )
    return OfflineFramePlan(
        source_fingerprint(compiled),
        GF2Map.from_matrix(interpreted[:nm]),
        tuple(interpreted[-1]),
        GF2Map.from_matrix(x[:nm]),
        GF2Map.from_matrix(z[:nm]),
        tuple(x[-1]),
        tuple(z[-1]),
        tuple(boundaries),
    )
