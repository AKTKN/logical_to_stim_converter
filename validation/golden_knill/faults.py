"""Independent categorical Pauli probes, raw parities and surviving data actions."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import product

import numpy as np
import stim

from .normalize import event_moments, parse, patch_site, require


@dataclass(frozen=True)
class Probe:
    moment: int
    parent: tuple | None
    axes: tuple
    side: str
    category: str


def make_probes(reference, distance, basis, *, open_output=False):
    """All reset/results and Bell-CX alternatives; selected SE and D waiting sites."""
    parsed = parse(reference.circuit, distance, basis, open_output=open_output)
    moments = event_moments(parsed)
    probes = []
    for t, events in enumerate(moments):
        selected_se = False
        for e in events:
            parent = (e.name, e.targets)
            if e.name in ("R", "RX"):
                axis = "X" if e.name == "R" else "Z"
                probes.append(Probe(t, parent, ((e.targets[0], axis),), "after", "reset"))
            elif e.name in ("M", "MX"):
                axis = "X" if e.name == "M" else "Z"
                probes.append(Probe(t, parent, ((e.targets[0], axis),), "before", "result"))
            elif e.name == "CX":
                patches = {patch_site(q, distance)[0] for q in e.targets}
                bell = len(patches) == 2
                if not bell and selected_se:
                    continue
                selected_se = True
                for axes in product("IXYZ", repeat=2):
                    if axes != ("I", "I"):
                        probes.append(
                            Probe(
                                t,
                                parent,
                                tuple(zip(e.targets, axes, strict=True)),
                                "after",
                                "Bell_CX" if bell else "SE_CX",
                            )
                        )
    waiting = [
        t
        for t, m in enumerate(reference.moments)
        if "D" in m.active_patches and "D" not in m.operations
    ]
    for t in sorted({waiting[0], waiting[len(waiting) // 2], waiting[-1]}):
        for local in reference.geometry.sites:
            coordinate = reference.sites[reference.indices["D", local]]
            for axis in "XYZ":
                probes.append(Probe(t, None, ((coordinate, axis),), "end", "D_waiting_idle"))
    # These channels are after the final SE TICK and before resource entangling CX.
    for patch in ("A", "B"):
        for local in reference.geometry.data:
            coordinate = reference.sites[reference.indices[patch, local]]
            for axis in "XYZ":
                probes.append(
                    Probe(
                        reference.resource_boundary_moment + 1,
                        None,
                        ((coordinate, axis),),
                        "start",
                        "resource_boundary",
                    )
                )
    # Active ancillas receive final-layer idle noise even when the patch data
    # are destructively read out. These locations remain in the noise inventory;
    # their channels are individually proved causally inert at the terminal cut.
    terminal_patches = ("D", "A") if open_output else ("B",)
    for patch in terminal_patches:
        for check in reference.geometry.checks:
            coordinate = reference.sites[reference.indices[patch, check.coordinate]]
            for axis in "XYZ":
                probes.append(
                    Probe(
                        len(reference.moments) - 1,
                        None,
                        ((coordinate, axis),),
                        "end",
                        "terminal_idle",
                    )
                )
    return tuple(probes)


def _responses(circuit, distance, basis, probes, *, open_output=False, mathematical=False):
    """No sampling: propagate deterministic errors with Stim or binary symplectic algebra.

    Stabilizer randomization is explicitly disabled only for differential Pauli
    propagation. Ideal signed instrument proofs are performed separately in B2.
    """
    parsed = parse(circuit, distance, basis, open_output=open_output)
    count = len(probes)
    where = defaultdict(list)
    for i, p in enumerate(probes):
        where[p.moment, p.parent, p.side].append((i, p.axes))
    lookup = {coord: i for i, coord in parsed.sites.items()}
    x = np.zeros((circuit.num_qubits, count), dtype=np.bool_)
    z = np.zeros_like(x)
    sim = (
        None
        if mathematical
        else stim.FlipSimulator(
            batch_size=count,
            num_qubits=circuit.num_qubits,
            disable_stabilizer_randomization=True,
        )
    )
    records = []

    def inject(t, parent, side):
        for i, axes in where[t, parent, side]:
            for coordinate, axis in axes:
                if axis == "I":
                    continue
                q = lookup[coordinate]
                if mathematical:
                    if axis in "XY":
                        x[q, i] ^= True
                    if axis in "YZ":
                        z[q, i] ^= True
                else:
                    mask = np.zeros((circuit.num_qubits, count), dtype=np.bool_)
                    mask[q, i] = True
                    sim.broadcast_pauli_errors(pauli=axis, mask=mask)

    for t, events in enumerate(event_moments(parsed)):
        inject(t, None, "start")
        for e in events:
            require(
                e.name in ("R", "RX", "CX", "M", "MX"),
                f"C1 fault propagation unsupported ideal event {e}",
            )
            parent = (e.name, e.targets)
            inject(t, parent, "before")
            qs = [lookup[c] for c in e.targets]
            if mathematical:
                if e.name == "R":
                    x[qs[0]] = False
                elif e.name == "RX":
                    z[qs[0]] = False
                elif e.name == "CX":
                    x[qs[1]] ^= x[qs[0]]
                    z[qs[0]] ^= z[qs[1]]
                else:
                    records.append((x if e.name == "M" else z)[qs[0]].copy())
            else:
                sim.do(stim.CircuitInstruction(e.name, qs))
            inject(t, parent, "after")
        inject(t, None, "end")
    raw = np.array(records) if mathematical else sim.get_measurement_flips()
    raw = raw[[parsed.key_to_record[k] for k in parsed.canonical_keys]]
    survivor = []
    states = sim.peek_pauli_flips() if open_output and not mathematical else None
    if open_output:
        for coordinate in sorted(parsed.sites.values()):
            patch, local = patch_site(coordinate, distance)
            if patch == "B" and local in reference_geometry(distance).data:
                q = lookup[coordinate]
                if mathematical:
                    survivor.extend((x[q].copy(), z[q].copy()))
                else:
                    survivor.extend(
                        (
                            np.array([p[q] in (1, 2) for p in states]),
                            np.array([p[q] in (2, 3) for p in states]),
                        )
                    )
    return raw, np.array(survivor, dtype=np.bool_)


def reference_geometry(distance):
    from validation.golden_memory.reference_same_schedule import geometry

    return geometry(distance)


def check_fault_probes(actual, reference, distance, basis, *, open_output=False):
    probes = make_probes(reference, distance, basis, open_output=open_output)
    expected_raw, expected_survivor = _responses(
        reference.circuit, distance, basis, probes, open_output=open_output, mathematical=True
    )
    for label, circuit in (("DUT", actual), ("independent Stim", reference.circuit)):
        raw, survivor = _responses(circuit, distance, basis, probes, open_output=open_output)
        differences = np.argwhere(raw != expected_raw)
        require(
            not differences.size,
            f"C1 deterministic raw fault response {label}: "
            f"{[(int(r), probes[int(p)]) for r, p in differences[:1]]}",
        )
        differences = np.argwhere(survivor != expected_survivor)
        require(
            not differences.size,
            f"C1 survivor physical action {label}: "
            f"{[(int(r), probes[int(p)]) for r, p in differences[:1]]}",
        )
    parsed = parse(reference.circuit, distance, basis, open_output=open_output)
    rows = [*parsed.detectors, *parsed.observables.values()]
    signatures = []
    for row in rows:
        selected = [i for i in range(len(parsed.keys)) if (row >> i) & 1]
        signatures.append(np.logical_xor.reduce(expected_raw[selected], axis=0))
    signatures = np.array(signatures)
    terminal = [i for i, p in enumerate(probes) if p.category == "terminal_idle"]
    require(
        not np.any(expected_raw[:, terminal])
        and (not expected_survivor.size or not np.any(expected_survivor[:, terminal]))
        and not np.any(signatures[:, terminal]),
        "C1 terminal idle mechanism unexpectedly affects raw/annotated/survivor state",
    )
    zero_signature = ~np.any(signatures, axis=0)
    return {
        "total": len(probes),
        "by_category": dict(Counter(p.category for p in probes)),
        "all_Bell_CX_15_Paulis": True,
        "signed_raw_record_response": True,
        "independent_symplectic_vs_Stim": True,
        "survivor_physical_actions": open_output,
        "zero_annotated_signature": int(np.count_nonzero(zero_signature)),
        "zero_annotated_by_category": dict(
            Counter(p.category for i, p in enumerate(probes) if zero_signature[i])
        ),
        "zero_raw_signature": int(np.count_nonzero(~np.any(expected_raw, axis=0))),
        "terminal_idle_probes": len(terminal),
        "terminal_idle_all_inert": True,
    }
