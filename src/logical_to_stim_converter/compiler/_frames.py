"""Evaluate externally resolved physical frames through the actual ideal circuit.

No correction selection or quantum feedback occurs here. Binary physical vectors
propagate linearly through the compiled Clifford pairings. Measurement flips and
teleportation byproducts are evaluated once, using corrected classical records.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from ..core.compiler_context import BlockStatus, PauliFrame
from ..core.protocol import PhysicalPauliFrame


def readonly(a):
    a = np.asarray(a, dtype=np.bool_)
    return np.frombuffer(a.tobytes(), dtype=np.bool_).reshape(a.shape)


@dataclass(frozen=True)
class EvaluatedBellMeasurement:
    corrected_x: np.ndarray
    corrected_z: np.ndarray
    byproduct_x: np.ndarray
    byproduct_z: np.ndarray
    output_frames: tuple[PhysicalPauliFrame, ...]


@dataclass(frozen=True)
class FrameEvaluation:
    corrected_measurements: np.ndarray
    logical_outputs: np.ndarray
    readout_values: Mapping[str, np.ndarray]
    bell_measurements: Mapping[str, EvaluatedBellMeasurement]
    final_frames: Mapping[str, tuple[PhysicalPauliFrame, ...]]


def correction_vectors(compiled, measurements, corrections, *, validation):
    """Validate external hypotheses; optionally prove strict noiseless sectors."""
    if validation not in ("noiseless", "hypothesis"):
        raise ValueError("Frame validation must be noiseless or hypothesis")
    raw = np.asarray(measurements, dtype=np.bool_)
    if raw.ndim != 2 or raw.shape[1] != compiled.ideal_circuit.num_measurements:
        raise ValueError("Expected a shot-by-raw-measurement matrix")
    preps = {p.module_id: p for p in compiled.preparations}
    if set(corrections) != set(preps):
        raise ValueError("Supply a resolved physical correction for every preparation module")
    records = {m.key: m.index for m in compiled.measurements}

    def vectors(prep, values):
        if isinstance(values, PhysicalPauliFrame):
            values = (values,) * len(raw)
        if len(values) != len(raw):
            raise ValueError("Supply one physical correction per shot")
        xs, zs = [], []
        expected = prep.unresolved_frame
        for frame in values:
            if (not isinstance(frame, PhysicalPauliFrame) or not frame.resolved
                    or (frame.block_id, frame.orientation, frame.preparation_module_id,
                        frame.stage_id, frame.source_syndromes)
                    != (expected.block_id, expected.orientation, expected.preparation_module_id,
                        expected.stage_id, expected.source_syndromes)):
                raise ValueError("Correction identity, orientation, or source boundary disagrees")
            if not (set(frame.x_support) | set(frame.z_support)) <= set(prep.data_ids):
                raise ValueError("Correction targets an unknown physical data qubit")
            expected_logical = PauliFrame(
                x_constant=bool(len(set(frame.x_support) & set(prep.logical_z)) % 2),
                z_constant=bool(len(set(frame.z_support) & set(prep.logical_x)) % 2))
            if frame.logical_contribution != expected_logical:
                raise ValueError("Correction logical contribution disagrees with physical support")
            xs.append([q in frame.x_support for q in prep.data_ids])
            zs.append([q in frame.z_support for q in prep.data_ids])
        xs = np.asarray(xs, dtype=np.uint8).reshape(len(raw), len(prep.data_ids))
        zs = np.asarray(zs, dtype=np.uint8).reshape(len(raw), len(prep.data_ids))
        if validation == "noiseless":
            for axis, vector in (("X", zs), ("Z", xs)):
                checks = [c for c in prep.checks if c.basis == axis]
                syndrome = raw[:, [records[c.measurements[-1]] for c in checks]]
                if not np.array_equal(vector @ prep.check_matrix(axis).T % 2, syndrome):
                    raise ValueError(
                        "Physical correction does not satisfy preparation check equations")
            support = prep.logical_x if prep.basis == "X" else prep.logical_z
            vector = zs if prep.basis == "X" else xs
            if np.any(np.sum(vector[:, [prep.data_ids.index(q) for q in support]], axis=1) % 2):
                raise ValueError("Preparation correction changes the intended logical eigenvalue")
        return xs.astype(bool), zs.astype(bool)

    return {key: vectors(preps[key], value) for key, value in corrections.items()}


def evaluate_frames(compiled, measurements, corrections, *, validation="noiseless"):
    resolved = correction_vectors(compiled, measurements, corrections, validation=validation)
    raw = np.asarray(measurements, dtype=np.bool_)
    preps = {p.module_id: p for p in compiled.preparations}
    records = compiled.measurement_index_by_key
    blocks = {b.block_id: b for b in compiled._compiler.blocks}
    backend = compiled._compiler.backend
    positions = {b.position(q): compiled.physical_qubit_map[(b.block_id, q)]
                 for b in blocks.values() for q in b.layout.qubit_ids}
    x = np.zeros((len(raw), compiled.ideal_circuit.num_qubits), dtype=np.bool_)
    z = x.copy()
    interpreted = raw.copy()
    cursor = 0
    evaluated_bells = {}

    def toggle(pauli, condition=True):
        for position, axis in pauli.items():
            index = positions[position]
            if axis in "XY":
                x[:, index] ^= condition
            if axis in "ZY":
                z[:, index] ^= condition

    def output_frames(block_id, logical, orientation, source, dependencies, stage=None):
        block = blocks[block_id]
        ix = [compiled.physical_qubit_map[(block_id, q)] for q in block.layout.data_ids]
        lx = backend.logical_pauli(block, logical, "X", orientation)
        lz = backend.logical_pauli(block, logical, "Z", orientation)
        fx = np.sum(x[:, [positions[q] for q in lz]], axis=1) % 2
        fz = np.sum(z[:, [positions[q] for q in lx]], axis=1) % 2
        return tuple(PhysicalPauliFrame(
            block_id, orientation, source, stage,
            tuple(k for p in dependencies for k in preps[p].unresolved_frame.source_syndromes),
            tuple(q for q, bit in zip(block.layout.data_ids, x[s, ix], strict=True) if bit),
            tuple(q for q, bit in zip(block.layout.data_ids, z[s, ix], strict=True) if bit),
            PauliFrame(x_constant=int(fx[s]), z_constant=int(fz[s]))) for s in range(len(raw)))

    bells = {b.composite_id: b for b in compiled.bell_measurements}
    for kind, value in compiled._evaluation_steps:
        if kind == "physical":
            local = {i: positions[q] for q, i in value.q2i.items()}
            for inst in value.circuit:
                if inst.name == "TICK":
                    continue
                targets = [local[t.value] for t in inst.targets_copy()]
                if inst.name == "H":
                    old = x[:, targets].copy()
                    x[:, targets] = z[:, targets]
                    z[:, targets] = old
                elif inst.name == "CX":
                    c, t = targets[::2], targets[1::2]
                    x[:, t] ^= x[:, c]
                    z[:, c] ^= z[:, t]
                elif inst.name in ("R", "RX", "RY"):
                    x[:, targets] = z[:, targets] = False
                elif inst.name in ("M", "MX", "MY"):
                    flips = (z[:, targets] if inst.name == "MX" else
                             x[:, targets] if inst.name == "M" else
                             x[:, targets] ^ z[:, targets])
                    interpreted[:, cursor:cursor + len(targets)] ^= flips
                    cursor += len(targets)
                    x[:, targets] = z[:, targets] = False
                elif inst.name not in ("X", "Y", "Z"):
                    raise ValueError(f"Unsupported physical frame instruction {inst.name}")
        elif kind == "preparation":
            prep = preps[value]
            indices = [compiled.physical_qubit_map[(prep.block_id, q)] for q in prep.data_ids]
            xs, zs = resolved[value]
            x[:, indices] ^= xs
            z[:, indices] ^= zs
        elif kind == "virtual":
            toggle(value)
        elif kind == "teleport":
            bell = bells[value["composite_id"]]
            mx = bell.x_readout.logical_parity.evaluate(interpreted, records)
            mz = bell.z_readout.logical_parity.evaluate(interpreted, records)
            block = blocks[bell.output_block_id]
            toggle(backend.logical_pauli(block, bell.logical_id, "X", bell.output_orientation), mz)
            toggle(backend.logical_pauli(block, bell.logical_id, "Z", bell.output_orientation), mx)
            frames = output_frames(bell.output_block_id, bell.logical_id,
                                   bell.output_orientation, bell.composite_id,
                                   bell.preparation_dependencies,
                                   bell.physical_output_frame.stage_id)
            evaluated_bells[bell.composite_id] = EvaluatedBellMeasurement(
                readonly(mx), readonly(mz), readonly(mz), readonly(mx), frames)
        else:
            raise ValueError("Unknown physical frame evaluation boundary")
    if cursor != raw.shape[1]:
        raise ValueError("Physical frame replay disagrees with compiled measurement order")
    readouts = {r.module_id: readonly(r.logical_parity.evaluate(interpreted, records))
                for r in compiled.readouts}
    outputs = np.zeros((len(raw), len(compiled.observables)), dtype=np.bool_)
    for o in compiled.observables:
        outputs[:, o.index] = np.bitwise_xor.reduce(
            interpreted[:, o.readout_measurement_indices], axis=1)
    final = {q: output_frames(b, q, compiled.orientations[q], "open_output",
                              compiled.preparation_dependencies[q])
             for q, b in compiled.logical_to_block.items()
             if compiled.block_status[b] == BlockStatus.ACTIVE}
    return FrameEvaluation(readonly(interpreted), readonly(outputs),
                           MappingProxyType(readouts), MappingProxyType(evaluated_bells),
                           MappingProxyType(final))
