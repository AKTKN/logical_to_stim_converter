"""Independent stream parsing, signed GF(2), causal moments and noise multisets."""

from collections import Counter, defaultdict
from dataclasses import dataclass

import stim

from .reference_same_schedule import geometry
from .reference_stim import reflect

ANNOTATIONS = {"QUBIT_COORDS", "SHIFT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE"}
NOISE = {"X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"}
MEASUREMENTS = {"M", "MX", "MR"}


class Mismatch(AssertionError):
    """A physical, semantic, signed-flow or fault-location mismatch."""


def require(condition, diagnostic):
    if not condition:
        raise Mismatch(diagnostic)


def parity(values):
    result = 0
    for v in values:
        result ^= 1 << v
    return result


def row_space(rows):
    """Unique reduced binary row space; integer bits are columns (including sign)."""
    pivots = {}
    for value in rows:
        while value:
            pivot = (value & -value).bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    for pivot in sorted(pivots, reverse=True):
        for previous in list(pivots):
            if previous < pivot and (pivots[previous] >> pivot) & 1:
                pivots[previous] ^= pivots[pivot]
    return tuple(pivots[p] for p in sorted(pivots))


def atoms(circuit):
    """Expand repeats/grouped targets without reordering any overlapping operations."""
    result = []
    for instruction in circuit.flattened():
        if instruction.name in ANNOTATIONS or instruction.name == "TICK":
            result.append(instruction)
            continue
        size = 2 if instruction.name in ("CX", "DEPOLARIZE2") else 1
        targets = instruction.targets_copy()
        require(len(targets) % size == 0, f"Malformed atomic gate {instruction}")
        for k in range(0, len(targets), size):
            result.append(
                stim.CircuitInstruction(
                    instruction.name, targets[k : k + size], instruction.gate_args_copy()
                )
            )
    return result


@dataclass
class Parsed:
    circuit: stim.Circuit
    sites: dict
    keys: tuple
    key_to_record: dict
    detectors: tuple[int, ...]
    observables: dict[int, int]

    @property
    def canonical_keys(self):
        return tuple(sorted(self.keys))

    def describe(self, row):
        keys = self.canonical_keys
        return {
            "keys": [k for i, k in enumerate(keys) if (row >> i) & 1],
            "sign": (row >> len(keys)) & 1,
        }


def parse(circuit, distance, basis, *, standard=False):
    g = geometry(distance)
    sites = {}
    for i, coords in circuit.get_final_qubit_coordinates().items():
        require(
            len(coords) >= 2 and all(int(c) == c for c in coords[:2]),
            f"Invalid occupied coordinate qubit={i}: {coords}",
        )
        coordinate = tuple(int(c) for c in coords[:2])
        sites[i] = reflect(coordinate) if standard else coordinate
    require(
        len(sites) == len(set(sites.values())) and set(sites.values()) == set(g.sites),
        f"Occupied site bijection differs: expected={g.sites}, actual={sites}",
    )
    by_coordinate = {c.coordinate: c for c in g.checks}
    rounds = Counter()
    keys, detectors, observables = [], [], defaultdict(int)
    for instruction in circuit.flattened():
        name = instruction.name
        if name in MEASUREMENTS:
            for target in instruction.targets_copy():
                coordinate = sites[target.value]
                if coordinate in by_coordinate:
                    check = by_coordinate[coordinate]
                    expected_gate = "MR" if standard else ("MX" if check.basis == "X" else "M")
                    require(
                        name == expected_gate,
                        f"Check basis mismatch check={check} actual={instruction}",
                    )
                    rounds[coordinate] += 1
                    key = ("check", check.basis, coordinate, rounds[coordinate])
                else:
                    require(
                        name == ("MX" if basis == "X" else "M"),
                        f"Readout basis mismatch basis={basis}, site={coordinate}: {instruction}",
                    )
                    key = ("readout", basis, coordinate)
                keys.append(key)
        if name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            absolute = [len(keys) + t.value for t in instruction.targets_copy()]
            require(
                all(0 <= i < len(keys) for i in absolute),
                f"Invalid annotation record at measurement={len(keys)}: {instruction}",
            )
            row = parity(absolute)
            if name == "DETECTOR":
                detectors.append(row)
            else:
                observables[int(instruction.gate_args_copy()[0])] ^= row
    expected = {("check", c.basis, c.coordinate, t) for c in g.checks for t in (1, 2, 3)}
    expected.update(("readout", basis, q) for q in g.data)
    require(
        len(keys) == len(set(keys)) and set(keys) == expected,
        f"Semantic measurement bijection differs missing={expected - set(keys)}, "
        f"extra={set(keys) - expected}",
    )
    order = {key: i for i, key in enumerate(sorted(keys))}

    def remap(row):
        return parity(order[key] for i, key in enumerate(keys) if (row >> i) & 1)

    return Parsed(
        circuit,
        sites,
        tuple(keys),
        {key: i for i, key in enumerate(keys)},
        tuple(map(remap, detectors)),
        {i: remap(row) for i, row in observables.items()},
    )


def expected_annotations(distance, basis):
    g = geometry(distance)
    keys = sorted(
        [("check", c.basis, c.coordinate, t) for c in g.checks for t in (1, 2, 3)]
        + [("readout", basis, q) for q in g.data]
    )
    columns = {key: i for i, key in enumerate(keys)}
    rows = {}
    for c in g.checks:
        for t in (1, 2, 3, 4):
            if t in (1, 4) and c.basis != basis:
                continue
            terms = [("check", c.basis, c.coordinate, min(t, 3))]
            if t in (2, 3):
                terms.append(("check", c.basis, c.coordinate, t - 1))
            if t == 4:
                terms.extend(("readout", basis, q) for q in c.support)
            rows[(c.basis, c.coordinate, t)] = parity(columns[k] for k in terms)
    logical = parity(columns[("readout", basis, q)] for q in g.logical(basis))
    return rows, logical


def pauli_bits(flow):
    bits = 0
    for p in (flow.input_copy(), flow.output_copy()):
        for i in range(len(p)):
            bits = (bits << 2) | {0: 0, 1: 1, 2: 3, 3: 2}[p[i]]
    return bits


def measurement_constraints(parsed):
    """Eliminate all input/output Paulis, multiplying actual signed Stim flows.

    Flow multiplication tracks anticommuting Pauli phases. Every resulting
    measurement-only signed relation is additionally verified by Stim.
    """
    # Pad every Pauli to the same width: Flow omits trailing identity qubits.
    width = parsed.circuit.num_qubits
    pivots, result = {}, []
    canonical = {k: i for i, k in enumerate(parsed.canonical_keys)}
    for original in parsed.circuit.flow_generators():
        pin, pout = original.input_copy(), original.output_copy()
        pin += stim.PauliString(width - len(pin))
        pout += stim.PauliString(width - len(pout))
        flow = stim.Flow(input=pin, output=pout, measurements=original.measurements_copy())
        bits = pauli_bits(flow)
        while bits:
            pivot = bits.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (bits, flow)
                break
            other_bits, other_flow = pivots[pivot]
            bits ^= other_bits
            flow = flow * other_flow
        if bits:
            continue
        require(parsed.circuit.has_flow(flow), f"Signed eliminated flow rejected: {flow}")
        records = flow.measurements_copy()
        row = parity(canonical[parsed.keys[i]] for i in records)
        sign = flow.input_copy().sign != flow.output_copy().sign
        result.append(row | (int(sign) << len(parsed.keys)))
    return row_space(result)


@dataclass(frozen=True, order=True)
class Event:
    name: str
    targets: tuple
    args: tuple
    inverted: tuple


def event_moments(parsed):
    moments = [[]]
    for inst in atoms(parsed.circuit):
        if inst.name == "TICK":
            moments.append([])
        elif inst.name not in ANNOTATIONS:
            targets = inst.targets_copy()
            require(all(t.value in parsed.sites for t in targets), f"Unmapped target: {inst}")
            args = tuple(inst.gate_args_copy())
            if inst.name in MEASUREMENTS and args == (0.0,):
                args = ()
            moments[-1].append(
                Event(
                    inst.name,
                    tuple(parsed.sites[t.value] for t in targets),
                    args,
                    tuple(t.is_inverted_result_target for t in targets),
                )
            )
    return moments


def causal_moments(parsed):
    """Trace normal form: commute only disjoint atomic events inside each TICK."""
    result = []
    for events in event_moments(parsed):
        depths, levels = {}, defaultdict(list)
        for e in events:
            depth = max((depths.get(q, -1) for q in e.targets), default=-1) + 1
            levels[depth].append(e)
            for q in e.targets:
                depths[q] = depth
        result.append(tuple(tuple(sorted(levels[k])) for k in sorted(levels)))
    return tuple(result)


@dataclass(frozen=True)
class NoiseLocation:
    moment: int
    parent: tuple
    side: str
    channel: str
    targets: tuple
    probability: float
    order: tuple


def noise_locations(parsed):
    locations = Counter()
    for moment, events in enumerate(event_moments(parsed)):
        used = {q for e in events if e.name not in NOISE for q in e.targets}
        previous, occurrences, positions = {}, Counter(), Counter()
        for e in events:
            order = tuple(positions[q] for q in e.targets)
            if e.name in NOISE:
                if e.name == "DEPOLARIZE1" and not used.intersection(e.targets):
                    parent, side = ("idle",), "interval_end"
                else:
                    parent = tuple(previous.get(q, ("no_prior_gate",)) for q in e.targets)
                    side = "after" if all(q in previous for q in e.targets) else "before"
                locations[
                    NoiseLocation(moment, parent, side, e.name, e.targets, e.args[0], order)
                ] += 1
            else:
                occurrence = occurrences[(e.name, e.targets)]
                occurrences[(e.name, e.targets)] += 1
                parent = (e.name, e.targets, occurrence)
                if e.name in MEASUREMENTS and e.args and e.args[0]:
                    locations[
                        NoiseLocation(
                            moment,
                            (parent,),
                            "result",
                            "measurement_flip",
                            e.targets,
                            e.args[0],
                            order,
                        )
                    ] += 1
                for q in e.targets:
                    previous[q] = parent
            for q in e.targets:
                positions[q] += 1
    return locations


def canonical_dem(parsed, distance, basis):
    """Native DEM from the complete physical model with canonical semantic IDs."""
    rows, logical = expected_annotations(distance, basis)
    circuit = stim.Circuit()
    for inst in parsed.circuit.flattened():
        if inst.name not in ANNOTATIONS:
            circuit.append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    total = len(parsed.keys)
    for name, row in [("DETECTOR", r) for _, r in sorted(rows.items())] + [
        ("OBSERVABLE_INCLUDE", logical)
    ]:
        targets = [
            stim.target_rec(parsed.key_to_record[k] - total)
            for j, k in enumerate(parsed.canonical_keys)
            if (row >> j) & 1
        ]
        circuit.append(name, targets, [] if name == "DETECTOR" else [0])
    return circuit.detector_error_model()
