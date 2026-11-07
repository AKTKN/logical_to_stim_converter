"""Exact Pauli fault actions for a declared conditional Bell-readout interval.

This is not a deterministic Stim DEM. Incoming sectors/frames are conditioned
on prior decoder hypotheses. Exclusive alternatives within a depolarizing channel
retain their group identity; cross-patch/readout/survivor correlations are kept.
"""

from dataclasses import dataclass
from itertools import product

import numpy as np
import stim

from .errors import UnsupportedProjectionError
from .records import GF2Map
from .stages import module_end
from .views import source_fingerprint


@dataclass(frozen=True)
class PauliFault:
    instruction_index: int
    channel: str
    exclusive_group: tuple[int, int]
    probability: float
    paulis: tuple[tuple[int, str], ...]
    measurement_record: int | None = None


@dataclass(frozen=True)
class ConditionalReadoutModel:
    source_fingerprint: str
    composite_id: str
    start_instruction: int
    end_instruction: int
    boundary_convention: str
    faults: tuple[PauliFault, ...]
    readout_record_ids: tuple[int, ...]
    output_data_ids: tuple[str, ...]
    raw_flip_map: GF2Map
    output_x_map: GF2Map
    output_z_map: GF2Map
    x_syndrome_map: GF2Map
    z_syndrome_map: GF2Map
    logical_flip_map: GF2Map


def make_conditional_readout_model(compiled, bell):
    """Preserve every Pauli atom from resource CNOT through destructive readout.

    Faults before this interval are represented only through the supplied incoming
    sector/frame hypothesis, whose accuracy is not asserted. Model construction
    never samples or consults a hidden physical error record.
    """
    resource = next(
        f
        for f in compiled.fragments
        if f.operation_type == "TransversalCNOT"
        and bell.composite_id in f.composite_ids
        and f.stage
        and f.stage.endswith("resource_entangling")
    )
    circuit = compiled.circuit
    start = next(i for i, inst in enumerate(circuit) if inst.tag == resource.module_id)
    end = module_end(circuit, bell.z_readout.module_id)
    keys = compiled.measurement_index_by_key
    readouts = (bell.x_readout, bell.z_readout)
    record_ids = tuple(keys[k] for r in readouts for k in r.records)
    prep = next(p for p in compiled.preparations if p.block_id == bell.output_block_id)
    output_ids = prep.data_ids
    output_indices = [compiled.physical_qubit_map[bell.output_block_id, q] for q in output_ids]
    faults, at_instruction = [], {}
    cursor = sum(inst.num_measurements for inst in circuit[:start])
    for i in range(start, end):
        inst = circuit[i]
        ts = [t.value for t in inst.targets_copy()]
        args = inst.gate_args_copy()
        new = []
        if inst.name in ("X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"):
            width = 2 if inst.name == "DEPOLARIZE2" else 1
            variants = (tuple(v) for v in product("IXYZ", repeat=width) if any(a != "I" for a in v))
            variants = tuple(variants) if inst.name.startswith("DEPOLARIZE") else ((inst.name[0],),)
            for offset in range(0, len(ts), width):
                for axes in variants:
                    new.append(
                        PauliFault(
                            i,
                            inst.name,
                            (i, offset),
                            args[0] / len(variants),
                            tuple(
                                (q, a)
                                for q, a in zip(ts[offset : offset + width], axes, strict=True)
                                if a != "I"
                            ),
                        )
                    )
        elif inst.name in ("M", "MX", "MY"):
            if args and args[0]:
                new = [
                    PauliFault(i, inst.name, (i, j), args[0], (), cursor + j)
                    for j in range(len(ts))
                ]
        elif stim.gate_data(inst.name).is_noisy_gate:
            raise UnsupportedProjectionError(f"Conditional model does not support {inst.name}")
        at_instruction[i] = tuple(range(len(faults), len(faults) + len(new)))
        faults.extend(new)
        cursor += inst.num_measurements
    x = np.zeros((len(faults), circuit.num_qubits), dtype=bool)
    z = x.copy()
    flips = np.zeros((len(faults), len(compiled.measurements)), dtype=bool)
    cursor = sum(inst.num_measurements for inst in circuit[:start])
    for i in range(start, end):
        inst = circuit[i]
        ts = [t.value for t in inst.targets_copy()]
        if inst.name == "CX":
            c, t = ts[::2], ts[1::2]
            x[:, t] ^= x[:, c]
            z[:, c] ^= z[:, t]
        elif inst.name == "H":
            old = x[:, ts].copy()
            x[:, ts] = z[:, ts]
            z[:, ts] = old
        elif inst.name in ("R", "RX", "RY"):
            x[:, ts] = z[:, ts] = False
        elif inst.name in ("M", "MX", "MY"):
            fs = z[:, ts] if inst.name == "MX" else x[:, ts]
            if inst.name == "MY":
                fs = x[:, ts] ^ z[:, ts]
            flips[:, cursor : cursor + len(ts)] ^= fs
            x[:, ts] = z[:, ts] = False
        elif not (
            stim.gate_data(inst.name).is_noisy_gate
            or inst.name
            in (
                "TICK",
                "DETECTOR",
                "OBSERVABLE_INCLUDE",
                "SHIFT_COORDS",
                "QUBIT_COORDS",
                "X",
                "Y",
                "Z",
            )
        ):
            raise UnsupportedProjectionError(f"Unsupported conditional Clifford {inst.name}")
        for row in at_instruction[i]:
            f = faults[row]
            for q, axis in f.paulis:
                if axis in "XY":
                    x[row, q] ^= True
                if axis in "ZY":
                    z[row, q] ^= True
            if f.measurement_record is not None:
                flips[row, f.measurement_record] ^= True
        cursor += inst.num_measurements
    selected = flips[:, record_ids]
    syndromes, logical = [], []
    offset = 0
    for r in readouts:
        a = selected[:, offset : offset + len(r.records)].astype(np.uint8)
        syndromes.append(a @ r.check_matrix(r.basis).T % 2)
        supports = [j for j, k in enumerate(r.records) if k in r.logical_parity.terms]
        logical.append(np.sum(a[:, supports], axis=1) % 2)
        offset += len(r.records)
    return ConditionalReadoutModel(
        source_fingerprint(compiled),
        bell.composite_id,
        start,
        end,
        "Condition on predicted sectors/frames immediately before resource CNOT; "
        "earlier residual errors are not inferred by this conditional model. "
        "Depolarizing atoms in one exclusive_group are mutually exclusive.",
        tuple(faults),
        record_ids,
        output_ids,
        GF2Map.from_matrix(selected),
        GF2Map.from_matrix(x[:, output_indices]),
        GF2Map.from_matrix(z[:, output_indices]),
        *(GF2Map.from_matrix(a) for a in syndromes),
        GF2Map.from_matrix(np.array(logical, dtype=np.uint8).T),
    )
