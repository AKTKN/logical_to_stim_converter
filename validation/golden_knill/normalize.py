"""Independent coordinate/record, signed-flow and causal noise normalization.

The golden-memory algebra has no construction dependency on the converter.
Its trace normal form commutes only disjoint operations within one TICK.
"""

from collections import Counter, defaultdict

import stim

from validation.golden_memory.normalize import (
    ANNOTATIONS,
    MEASUREMENTS,
    NOISE,
    Mismatch,
    Parsed,
    atoms,
    causal_moments,
    event_moments,
    measurement_constraints,
    noise_locations,
    parity,
    require,
    row_space,
)
from validation.golden_memory.reference_same_schedule import geometry

__all__ = [
    "ANNOTATIONS",
    "MEASUREMENTS",
    "NOISE",
    "Mismatch",
    "atoms",
    "causal_moments",
    "event_moments",
    "measurement_constraints",
    "noise_locations",
    "parity",
    "require",
    "row_space",
    "parse",
    "basis_map",
    "canonical_circuit",
    "canonical_dem",
    "patch_site",
]


def patch_site(coordinate, distance):
    """Map absolute coordinates using the independently specified patch placement."""
    stride = 2 * distance + 2
    for i, patch in enumerate(("D", "A", "B")):
        local = (coordinate[0] - i * stride, coordinate[1])
        if local in geometry(distance).sites:
            return patch, local
    raise Mismatch(f"Physical site outside three-patch specification: {coordinate}")


def parse(circuit, distance, basis, *, open_output=False):
    g = geometry(distance)
    sites = {}
    for index, coords in circuit.get_final_qubit_coordinates().items():
        require(
            len(coords) >= 2 and all(int(c) == c for c in coords[:2]),
            f"Invalid occupied coordinate q={index}, coords={coords}",
        )
        sites[index] = tuple(map(int, coords[:2]))
    expected_sites = {(q[0] + i * (2 * distance + 2), q[1]) for i in range(3) for q in g.sites}
    require(
        len(sites) == len(set(sites.values())) and set(sites.values()) == expected_sites,
        f"B1 occupied physical sites mismatch missing={expected_sites - set(sites.values())}, "
        f"extra={set(sites.values()) - expected_sites}",
    )
    checks = {c.coordinate: c for c in g.checks}
    rounds, observables = Counter(), defaultdict(int)
    keys, detectors = [], []
    for inst in circuit.flattened():
        name = {"MZ": "M", "RZ": "R"}.get(inst.name, inst.name)
        if name in MEASUREMENTS:
            for target in inst.targets_copy():
                coordinate = sites[target.value]
                patch, local = patch_site(coordinate, distance)
                if local in checks:
                    check = checks[local]
                    require(
                        name == ("MX" if check.basis == "X" else "M"),
                        f"B1 check readout basis patch={patch},check={check},actual={inst}",
                    )
                    rounds[patch, local] += 1
                    keys.append(("check", patch, check.basis, coordinate, rounds[patch, local]))
                else:
                    read_basis = {"D": "X", "A": "Z", "B": basis}[patch]
                    require(
                        name == ("MX" if read_basis == "X" else "M"),
                        f"B1 Bell/final readout basis patch={patch},site={coordinate},"
                        f"expected={read_basis},actual={inst}",
                    )
                    keys.append(("readout", patch, read_basis, coordinate))
        if name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            records = [len(keys) + t.value for t in inst.targets_copy()]
            require(
                all(0 <= r < len(keys) for r in records),
                f"B2 invalid annotation record count={len(keys)}: {inst}",
            )
            row = parity(records)
            if name == "DETECTOR":
                detectors.append(row)
            else:
                observables[int(inst.gate_args_copy()[0])] ^= row
    expected_keys = set()
    for i, patch in enumerate(("D", "A", "B")):

        def absolute(q):
            return (q[0] + i * (2 * distance + 2), q[1])

        for check in g.checks:
            for t in range(1, 2 if patch == "D" else distance + 1):
                expected_keys.add(("check", patch, check.basis, absolute(check.coordinate), t))
        if patch != "B" or not open_output:
            read_basis = {"D": "X", "A": "Z", "B": basis}[patch]
            expected_keys.update(("readout", patch, read_basis, absolute(q)) for q in g.data)
    require(
        len(keys) == len(set(keys)) and set(keys) == expected_keys,
        f"B1 semantic record bijection mismatch missing={expected_keys - set(keys)}, "
        f"extra={set(keys) - expected_keys}",
    )
    columns = {key: i for i, key in enumerate(sorted(keys))}

    def remap(row):
        return parity(columns[k] for i, k in enumerate(keys) if (row >> i) & 1)

    return Parsed(
        circuit,
        sites,
        tuple(keys),
        {k: i for i, k in enumerate(keys)},
        tuple(map(remap, detectors)),
        {i: remap(r) for i, r in observables.items()},
    )


def basis_map(actual, reference):
    """Return exact binary row coefficients and require an invertible detector map."""
    require(
        len(actual) == len(reference),
        f"B2 detector basis dimensions differ DUT={len(actual)},reference={len(reference)}",
    )
    pivots = {}
    for i, row in enumerate(reference):
        value, coefficient = row, 1 << i
        while value:
            pivot = value.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (value, coefficient)
                break
            r, c = pivots[pivot]
            value ^= r
            coefficient ^= c
        require(value != 0, f"B2 independent reference detector rows dependent row={i}")
    coefficients = []
    for i, row in enumerate(actual):
        value, coefficient = row, 0
        while value:
            pivot = value.bit_length() - 1
            require(
                pivot in pivots,
                f"B2 detector parity outside independent row space row={i},residual={value:#x}",
            )
            r, c = pivots[pivot]
            value ^= r
            coefficient ^= c
        coefficients.append(coefficient)
    require(
        len(row_space(coefficients)) == len(reference),
        "B2 detector row transformation is not invertible",
    )
    return tuple(coefficients)


def canonical_circuit(parsed, reference):
    """Keep every physical instruction; append only independently authored rows."""
    circuit = stim.Circuit()
    for inst in parsed.circuit.flattened():
        if inst.name not in ANNOTATIONS:
            circuit.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    total = len(parsed.keys)
    for row in reference.detectors:
        circuit.append(
            "DETECTOR",
            [
                stim.target_rec(parsed.key_to_record[k] - total)
                for j, k in enumerate(parsed.canonical_keys)
                if (row >> j) & 1
            ],
        )
    for obs_id, row in sorted(reference.observables.items()):
        circuit.append(
            "OBSERVABLE_INCLUDE",
            [
                stim.target_rec(parsed.key_to_record[k] - total)
                for j, k in enumerate(parsed.canonical_keys)
                if (row >> j) & 1
            ],
            obs_id,
        )
    return circuit


def canonical_dem(parsed, reference):
    """Native exact Stim DEM, with no decomposition, probability rounding or cap."""
    return canonical_circuit(parsed, reference).detector_error_model()
