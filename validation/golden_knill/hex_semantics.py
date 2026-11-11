"""Independent GF(2), signed-instrument and conditional teleportation oracle.

No decoder output or production frame planner is consulted. A linear CSS
recovery fixes each syndrome while commuting with the chosen logical strings;
binary physical Paulis are then propagated through the actual transversal CXs.
The two-axis channel proof removes D's preparation entirely.
"""

from collections import Counter
from types import SimpleNamespace

import numpy as np
import stim

from validation.golden_memory.normalize import measurement_constraints, require, row_space
from validation.golden_memory.reference_same_schedule import geometry

ANNOTATIONS = {"DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS", "SHIFT_COORDS"}
MEASUREMENTS = {"M", "MX", "MR", "MRX"}


def parity(values):
    result = 0
    for value in values:
        result ^= 1 << int(value)
    return result


def _rows(matrix):
    return tuple(parity(np.flatnonzero(row)) for row in np.atleast_2d(matrix))


def solve_gf2(matrix, rhs):
    """Deterministic free-zero solution; reject inconsistent physical sectors."""
    a = np.asarray(matrix, dtype=np.uint8).copy() % 2
    b = np.asarray(rhs, dtype=np.uint8).copy() % 2
    a = np.column_stack((a, b))
    row, pivots = 0, []
    for column in range(a.shape[1] - 1):
        selected = np.flatnonzero(a[row:, column])
        if not len(selected):
            continue
        chosen = row + selected[0]
        a[[row, chosen]] = a[[chosen, row]]
        for other in range(len(a)):
            if other != row and a[other, column]:
                a[other] ^= a[row]
        pivots.append(column)
        row += 1
        if row == len(a):
            break
    require(
        not np.any(np.all(a[:, :-1] == 0, axis=1) & (a[:, -1] != 0)), "Inconsistent CSS syndrome"
    )
    result = np.zeros(a.shape[1] - 1, dtype=np.uint8)
    for index, column in enumerate(pivots):
        result[column] = a[index, -1]
    return result


def check_geometry(bundle):
    d, matrices = bundle.distance, bundle.matrices
    x, z, lx, lz = (matrices[k] for k in ("X", "Z", "LX", "LZ"))
    require(not np.any(x @ z.T % 2), "A0 Hex checks anticommute")
    require(
        len(row_space(_rows(x))) + len(row_space(_rows(z))) == d * d - 1, "A0 Hex stabilizer rank"
    )
    require(not np.any(lx @ z.T % 2) and not np.any(lz @ x.T % 2), "A0 logical/check commutation")
    require(np.array_equal(lx @ lz.T % 2, [[1]]), "A0 logical anticommutation")
    g = geometry(d)
    # Native Hex i = row*d+col; the independent physical grid uses that
    # same first-axis-major convention, reflected in its second coordinate.
    coordinates = [(2 * (i // d) + 1, 2 * (d - 1 - i % d) + 1) for i in range(d * d)]
    columns = {q: i for i, q in enumerate(g.data)}
    cosets = {}
    for basis, matrix, logical in (("X", x, lx), ("Z", z, lz)):
        mapped = [parity(columns[coordinates[i]] for i in np.flatnonzero(row)) for row in matrix]
        expected = [parity(columns[q] for q in c.support) for c in g.checks if c.basis == basis]
        require(row_space(mapped) == row_space(expected), f"A0 {basis} reflected row space differs")
        require(set(mapped) == set(expected), f"A0 {basis} reflected row sets differ")
        mapped_logical = parity(columns[coordinates[i]] for i in np.flatnonzero(logical[0]))
        wanted = parity(columns[q] for q in g.logical(basis))
        require(
            row_space([*expected, mapped_logical ^ wanted]) == row_space(expected),
            f"A0 {basis} logical coset differs",
        )
        check_arrays = np.asarray(
            [[(row >> j) & 1 for j in range(d * d)] for row in expected], dtype=np.uint8
        )
        difference = np.asarray(
            [((mapped_logical ^ wanted) >> j) & 1 for j in range(d * d)], dtype=np.uint8
        )
        coefficients = solve_gf2(check_arrays.T, difference)
        cosets[basis] = {
            "mapped_support": mapped_logical,
            "reference_support": wanted,
            "stabilizer_difference": mapped_logical ^ wanted,
            "signed_syndrome_rows": np.flatnonzero(coefficients).tolist(),
            "sign_rule": "native parity XOR these measured stabilizer bits = reference parity",
        }
    return {
        "passed": True,
        "reflection": "(row,col)->(row,d-1-col)",
        "rank_X": len(row_space(_rows(x))),
        "rank_Z": len(row_space(_rows(z))),
        "logical_cosets": cosets,
    }


def physical(circuit):
    result = stim.Circuit()
    for instruction in circuit.without_noise().flattened():
        if instruction.name not in ANNOTATIONS:
            result.append(instruction)
    return result


def pauli(support, values, basis, width):
    p = stim.PauliString(width)
    for index in np.flatnonzero(np.asarray(values)):
        p[support[index]] = basis
    return p


def _atoms(circuit):
    for instruction in physical(circuit):
        targets = instruction.targets_copy()
        if instruction.name == "TICK":
            yield instruction
            continue
        size = 2 if instruction.name in ("CX", "CZ", "CY", "SWAP") else 1
        for i in range(0, len(targets), size):
            yield stim.CircuitInstruction(
                instruction.name, targets[i : i + size], instruction.gate_args_copy()
            )


def check_round_instrument(segment, checks, logicals, data_support, label="round", record_map=None):
    segment = physical(segment)
    if record_map is None:
        record_map = {
            (b, j): offset + j
            for b, offset in (("X", 0), ("Z", len(checks["X"])))
            for j in range(len(checks[b]))
        }
    require(
        segment.num_measurements == len(checks["X"]) + len(checks["Z"]),
        f"{label} incomplete round records",
    )
    count = 0
    for basis in "XZ":
        for index, check in enumerate(checks[basis]):
            p = pauli(data_support, check, basis, segment.num_qubits)
            for flow in (
                stim.Flow(input=p, measurements=[record_map[basis, index]]),
                stim.Flow(output=p, measurements=[record_map[basis, index]]),
                stim.Flow(input=p, output=p),
            ):
                require(
                    segment.has_flow(flow),
                    f"{label} signed {basis} check {index} instrument failed: {flow}",
                )
                count += 1
        for logical in np.atleast_2d(logicals[basis]):
            p = pauli(data_support, logical, basis, segment.num_qubits)
            require(
                segment.has_flow(stim.Flow(input=p, output=p)),
                f"{label} {basis} logical preservation failed",
            )
            count += 1
    return count


def preparation_records(circuit, matrices, support):
    """Identify check meaning from measured ancilla's actual data neighbours."""
    support_index = {q: i for i, q in enumerate(support)}
    neighbourhood, bases, records = {}, {}, {}
    for inst in _atoms(circuit):
        ts = [t.value for t in inst.targets_copy()]
        if inst.name in ("CX", "CZ"):
            if ts[0] not in support_index and ts[1] in support_index:
                ancilla, data = ts
                basis = "X" if inst.name == "CX" else "Z"
            elif ts[0] in support_index and ts[1] not in support_index and inst.name == "CX":
                data, ancilla = ts
                basis = "Z"
            else:
                continue
            neighbourhood.setdefault(ancilla, set()).add(support_index[data])
            require(ancilla not in bases or bases[ancilla] == basis, "Check ancilla basis changed")
            bases[ancilla] = basis
    measured = 0
    for inst in _atoms(circuit):
        if inst.name not in MEASUREMENTS:
            continue
        q = inst.targets_copy()[0].value
        require(q not in support_index, "Data readout appeared inside preparation")
        basis = bases[q]
        candidates = [
            i
            for i, row in enumerate(matrices[basis])
            if set(np.flatnonzero(row)) == neighbourhood[q]
        ]
        require(len(candidates) == 1, f"Unknown {basis} check support {neighbourhood[q]}")
        records[basis, candidates[0]] = measured
        measured += 1
    if measured:
        require(
            len(records) == len(matrices["X"]) + len(matrices["Z"]), "Preparation missing check"
        )
    return records


def check_preparation(circuit, matrices, support, basis, rounds, label):
    m = len(matrices["X"]) + len(matrices["Z"])
    records = preparation_records(circuit, matrices, support)
    if not rounds:
        simulator = stim.TableauSimulator()
        simulator.do(circuit)
        for b in "XZ":
            for row in matrices[b]:
                output = pauli(support, row, b, circuit.num_qubits)
                initial = output.before(circuit)
                require(
                    initial.sign == 1 and all(initial[j] in (0, 3) for j in range(len(initial))),
                    f"{label} encoded check did not pull back to a positive initial Z product",
                )
                require(
                    circuit.has_flow(stim.Flow(input=initial, output=output)),
                    f"{label} exact unitary preparation flow failed",
                )
                require(
                    simulator.peek_observable_expectation(output) == 1,
                    f"{label} unitary encoded check",
                )
        return {"rounds": 0, "signed_flows": m, "constraint_rank": 0}
    segments, current, measured = [], stim.Circuit(), 0
    for inst in _atoms(circuit):
        if inst.name in ("R", "RX") and inst.targets_copy()[0].value in support:
            continue
        current.append(inst)
        if inst.name in MEASUREMENTS:
            measured += 1
            if measured == m:
                segments.append(current)
                current, measured = stim.Circuit(), 0
    require(len(segments) == rounds, f"{label} round count differs")
    record_map = {key: value % m for key, value in records.items()}
    count = sum(
        check_round_instrument(
            segment,
            {b: matrices[b] for b in "XZ"},
            {b: matrices["L" + b] for b in "XZ"},
            support,
            f"{label} round {j + 1}",
            record_map,
        )
        for j, segment in enumerate(segments)
    )
    parsed = SimpleNamespace(
        circuit=physical(circuit),
        keys=tuple(range(circuit.num_measurements)),
        canonical_keys=tuple(range(circuit.num_measurements)),
    )
    actual = measurement_constraints(parsed)
    expected = [1 << record_map[basis, j] for j in range(len(matrices[basis]))]
    expected += [
        (1 << (r * m + record_map[b, j])) ^ (1 << ((r - 1) * m + record_map[b, j]))
        for r in range(1, rounds)
        for b in "XZ"
        for j in range(len(matrices[b]))
    ]
    require(
        actual == row_space(expected), f"{label} full signed preparation constraint space differs"
    )
    return {
        "rounds": rounds,
        "signed_flows": count,
        "constraint_rank": len(actual),
        "free_syndromes": circuit.num_measurements - len(actual),
    }


def recovery_map(matrices, syndrome_basis):
    """Linear recovery columns commute with the corresponding logical string."""
    h = matrices[syndrome_basis]
    a = np.vstack((h, matrices["L" + syndrome_basis]))
    return [solve_gf2(a, np.r_[np.eye(len(h), dtype=np.uint8)[:, j], 0]) for j in range(len(h))]


def _xor(values):
    result = 0
    for value in values:
        result ^= int(value)
    return result


def _symbolic_frames(preparations, matrices, supports):
    frames, offset, all_records = {}, 0, {}
    for role in ("D", "A", "B"):
        circuit = preparations.get(role, stim.Circuit())
        records = preparation_records(circuit, matrices, supports[role])
        all_records[role] = {key: offset + value for key, value in records.items()}
        frame = {"X": [0] * len(supports[role]), "Z": [0] * len(supports[role])}
        for syndrome_basis, axis in (("X", "Z"), ("Z", "X")):
            for j, column in enumerate(recovery_map(matrices, syndrome_basis)):
                if (syndrome_basis, j) not in records:
                    continue
                variable = 1 << (offset + records[syndrome_basis, j])
                for q in np.flatnonzero(column):
                    frame[axis][q] ^= variable
        frames[role] = frame
        offset += circuit.num_measurements
    return frames, offset, all_records


def _propagate(frame, circuit, supports):
    lookup = {q: (role, j) for role, qs in supports.items() for j, q in enumerate(qs)}
    for inst in _atoms(circuit):
        if inst.name != "CX":
            continue
        c, t = [lookup[v.value] for v in inst.targets_copy()]
        frame[t[0]]["X"][t[1]] ^= frame[c[0]]["X"][c[1]]
        frame[c[0]]["Z"][c[1]] ^= frame[t[0]]["Z"][t[1]]


def _logical_frame(frame, matrices, role, basis):
    axis = "Z" if basis == "X" else "X"
    return _xor(frame[role][axis][j] for j in np.flatnonzero(matrices["L" + basis][0]))


def _readouts(circuit, supports, offset):
    lookup = {q: (role, j) for role, qs in supports.items() for j, q in enumerate(qs)}
    result = {}
    count = offset
    for inst in _atoms(circuit):
        if inst.name in MEASUREMENTS:
            role, j = lookup[inst.targets_copy()[0].value]
            basis = "X" if inst.name in ("MX", "MRX") else "Z"
            result[role, j] = (basis, count)
            count += 1
    return result


def _bell_bits(frame, circuit, matrices, supports, offset):
    record = _readouts(circuit, supports, offset)
    bits = {}
    for role, basis in (("D", "X"), ("A", "Z")):
        require(
            all(
                record.get((role, j), (None, None))[0] == basis for j in range(len(supports[role]))
            ),
            f"Bell {role} readout basis differs",
        )
        raw = parity(record[role, j][1] for j in np.flatnonzero(matrices["L" + basis][0]))
        bits[basis] = raw ^ _logical_frame(frame, matrices, role, basis)
    return bits


def derive_frame_plan(preparations, entangle, bell_measure, matrices, data_supports):
    """Public linear independent oracle for DUT metadata/replay cross-checks.

    Each integer is a parity mask on the original physical record. Physical
    frame entries are X then Z by role; Bell bits include gauge terms. The net
    survivor correction also includes the independently derived logical Pauli.
    """
    frames, offset, records = _symbolic_frames(preparations, matrices, data_supports)
    _propagate(frames, physical(entangle), data_supports)
    _propagate(frames, physical(bell_measure), data_supports)
    bits = _bell_bits(frames, bell_measure, matrices, data_supports, offset)
    correction = {axis: list(values) for axis, values in frames["B"].items()}
    for axis, logical_basis, bit_basis in (("X", "X", "Z"), ("Z", "Z", "X")):
        for j in np.flatnonzero(matrices["L" + logical_basis][0]):
            correction[axis][j] ^= bits[bit_basis]
    return {
        "frames": frames,
        "bell_bits": bits,
        "survivor_correction": correction,
        "preparation_records": records,
        "Bell_measurement_record_offset": offset,
    }


def _evaluate(mask, record):
    return _xor(record[j] for j in range(len(record)) if (mask >> j) & 1)


def _correct(simulator, frame, role, support, record):
    for axis in "XZ":
        targets = [
            support[j] for j, mask in enumerate(frame[role][axis]) if _evaluate(mask, record)
        ]
        if targets:
            getattr(simulator, axis.lower())(*targets)


def check_protocol_channel(
    preparations,
    entangle,
    bell_measure,
    readout,
    matrices,
    data_supports,
    input_basis,
    input_bit,
    trials=64,
    label="protocol",
    correction_array=None,
    logical_alternatives=None,
):
    """Exact two-axis channel flows plus separately labelled sampled gauge tests."""
    native_bell_instruction_count = len(bell_measure)
    preparations = {
        role: physical(preparations.get(role, stim.Circuit())) for role in ("D", "A", "B")
    }
    entangle, bell_measure, readout = map(physical, (entangle, bell_measure, readout))
    n = len(data_supports["D"])
    require(all(len(qs) == n for qs in data_supports.values()), f"{label} unequal patch widths")
    width = max(q for qs in data_supports.values() for q in qs) + 1
    # Channel proof: D preparation is absent; its Pauli is an actual input port.
    resources = {**preparations, "D": stim.Circuit()}
    frame, offset, _ = _symbolic_frames(resources, matrices, data_supports)
    _propagate(frame, entangle, data_supports)
    _propagate(frame, bell_measure, data_supports)
    bits = _bell_bits(frame, bell_measure, matrices, data_supports, offset)
    channel = preparations["A"] + preparations["B"] + entangle + bell_measure
    flow_masks = {}
    for basis in "XZ":
        correction = bits[basis] ^ _logical_frame(frame, matrices, "B", basis)
        flow = stim.Flow(
            input=pauli(data_supports["D"], matrices["L" + basis][0], basis, width),
            output=pauli(data_supports["B"], matrices["L" + basis][0], basis, width),
            measurements=[j for j in range(channel.num_measurements) if (correction >> j) & 1],
        )
        require(
            channel.has_flow(flow),
            f"{label} signed two-axis identity channel failed {basis}: {flow}",
        )
        flow_masks[basis] = correction
    if correction_array is not None:
        expected = []
        for basis in "ZX":
            p = pauli(data_supports["B"], matrices["L" + basis][0], basis, width)
            expected.append(p)
        require(len(correction_array) == 2, "Hex correction array width differs")
        for index, (text, placement) in enumerate(correction_array):
            require(
                placement == native_bell_instruction_count,
                "Hex correction placement must follow the complete native Bell module: "
                f"expected_instruction_cut={native_bell_instruction_count}, actual={placement}",
            )
            actual = stim.PauliString(text)
            actual += stim.PauliString(width - len(actual))
            require(actual == expected[index], "Hex correction order must be Z^(m_X), X^(m_Z)")
    # Physical tableau trials exercise nonzero gauges and all Bell branches.
    frame0, offset, _ = _symbolic_frames(preparations, matrices, data_supports)
    frame_bell = {role: {axis: list(v) for axis, v in f.items()} for role, f in frame0.items()}
    _propagate(frame_bell, entangle, data_supports)
    # Bell resource checks are evaluated before D/A coupling.
    resource_frame = {
        role: {axis: list(v) for axis, v in f.items()} for role, f in frame_bell.items()
    }
    resource = preparations["D"] + preparations["A"] + preparations["B"] + entangle
    exact_bell_flows = 0
    for basis in "XZ":
        for role in ("A", "B"):
            opposite = "Z" if basis == "X" else "X"
            for check in matrices[basis]:
                mask = _xor(resource_frame[role][opposite][j] for j in np.flatnonzero(check))
                flow = stim.Flow(
                    output=pauli(data_supports[role], check, basis, width),
                    measurements=[j for j in range(resource.num_measurements) if (mask >> j) & 1],
                )
                require(
                    resource.has_flow(flow), f"{label} exact recovered {role} check flow failed"
                )
                exact_bell_flows += 1
        mask = _logical_frame(resource_frame, matrices, "A", basis) ^ _logical_frame(
            resource_frame, matrices, "B", basis
        )
        p = pauli(data_supports["A"], matrices["L" + basis][0], basis, width) * pauli(
            data_supports["B"], matrices["L" + basis][0], basis, width
        )
        require(
            resource.has_flow(
                stim.Flow(
                    output=p,
                    measurements=[j for j in range(resource.num_measurements) if (mask >> j) & 1],
                )
            ),
            f"{label} exact corrected Bell {basis}{basis} flow failed",
        )
        exact_bell_flows += 1
    _propagate(frame_bell, bell_measure, data_supports)
    branch_bits = _bell_bits(frame_bell, bell_measure, matrices, data_supports, offset)
    branch_circuit = resource + bell_measure
    parsed = SimpleNamespace(
        circuit=branch_circuit,
        keys=tuple(range(branch_circuit.num_measurements)),
        canonical_keys=tuple(range(branch_circuit.num_measurements)),
    )
    constraints = measurement_constraints(parsed)
    require(
        len(row_space([*constraints, branch_bits["X"], branch_bits["Z"]])) == len(constraints) + 2,
        f"{label} corrected Bell bits are not two independent free outcomes",
    )
    branches, nonzero, closed = Counter(), 0, 0
    coset_sign_flips = 0
    bell_checks = 0
    prefix = preparations["D"] + preparations["A"] + preparations["B"] + entangle
    for trial in range(max(trials, 64)):
        sim = stim.TableauSimulator(seed=0x4B1100 + trial)
        sim.do(prefix)
        record = sim.current_measurement_record()
        nonzero += any(record)
        recovered = sim.copy()
        for role in ("A", "B"):
            _correct(recovered, resource_frame, role, data_supports[role], record)
            for basis in "XZ":
                for check in matrices[basis]:
                    require(
                        recovered.peek_observable_expectation(
                            pauli(data_supports[role], check, basis, width)
                        )
                        == 1,
                        f"{label} {role} recovered code check failed",
                    )
                    bell_checks += 1
        for basis in "XZ":
            p = pauli(data_supports["A"], matrices["L" + basis][0], basis, width) * pauli(
                data_supports["B"], matrices["L" + basis][0], basis, width
            )
            require(
                recovered.peek_observable_expectation(p) == 1,
                f"{label} recovered Bell {basis}{basis} failed",
            )
            bell_checks += 1
        sim.do(bell_measure)
        record = sim.current_measurement_record()
        mx, mz = (_evaluate(branch_bits[b], record) for b in "XZ")
        branches[mx, mz] += 1
        if logical_alternatives is not None:
            alternative = np.asarray(logical_alternatives[input_basis], dtype=np.uint8)
            native = matrices["L" + input_basis][0]
            difference = native ^ alternative
            opposite = "Z" if input_basis == "X" else "X"
            sign_mask = _xor(frame_bell["B"][opposite][j] for j in np.flatnonzero(difference))
            coset_sign_flips += _evaluate(sign_mask, record)
            native_value = sim.peek_observable_expectation(
                pauli(data_supports["B"], native, input_basis, width)
            )
            alternative_value = sim.peek_observable_expectation(
                pauli(data_supports["B"], alternative, input_basis, width)
            )
            require(
                native_value in (-1, 1)
                and alternative_value in (-1, 1)
                and native_value == alternative_value * (-1) ** _evaluate(sign_mask, record),
                f"{label} uncorrected logical coset omitted signed syndrome parity",
            )
        _correct(sim, frame_bell, "B", data_supports["B"], record)
        for bit, basis in ((mx, "Z"), (mz, "X")):
            if bit:
                getattr(sim, basis.lower())(
                    *[data_supports["B"][j] for j in np.flatnonzero(matrices["L" + basis][0])]
                )
        for basis in "XZ":
            for check in matrices[basis]:
                require(
                    sim.peek_observable_expectation(pauli(data_supports["B"], check, basis, width))
                    == 1,
                    f"{label} survivor recovered check failed",
                )
        require(
            sim.peek_observable_expectation(
                pauli(data_supports["B"], matrices["L" + input_basis][0], input_basis, width)
            )
            == (-1) ** input_bit,
            f"{label} open survivor signed eigenvalue failed",
        )
        # Copy before correction to compare independent software parity with a
        # physically corrected destructive readout; no resampling decoder truth.
        before = len(sim.current_measurement_record())
        sim.do(readout)
        result = sim.current_measurement_record()[before:]
        readout_order = _readouts(readout, data_supports, 0)
        require(
            all(readout_order.get(("B", j), (None, None))[0] == input_basis for j in range(n)),
            f"{label} final readout basis differs",
        )
        value = _xor(
            result[readout_order["B", j][1]] for j in np.flatnonzero(matrices["L" + input_basis][0])
        )
        require(value == input_bit, f"{label} closed corrected signed readout failed")
        closed += 1
    require(
        set(branches) == {(0, 0), (0, 1), (1, 0), (1, 1)},
        f"{label} four corrected Bell branches not reached: {branches}",
    )
    require(nonzero > 0, f"{label} no nonzero preparation sector exercised")
    return {
        "A2": {
            "passed": True,
            "tableau_trials": max(trials, 64),
            "nonzero_preparation_trials": nonzero,
            "recovered_check_and_Bell_expectations": bell_checks,
            "exact_signed_resource_flows": exact_bell_flows,
            "recovery": "GF2 free-zero; logical-commuting CSS representatives",
        },
        "A3": {
            "passed": True,
            "two_axis_signed_channel_flows": 2,
            "input_preparation_removed_for_channel_proof": True,
            "channel_flow_record_masks": flow_masks,
            "input_basis": input_basis,
            "input_bit": input_bit,
            "observed_corrected_Bell_branches": {
                f"{x}{z}": count for (x, z), count in sorted(branches.items())
            },
            "exact_independent_Bell_bits": 2,
            "open_state_trials": max(trials, 64),
            "closed_readout_trials": closed,
            "byproduct_rule": "Z^(corrected m_X) X^(corrected m_Z)",
            "raw_signed_coset_trials": max(trials, 64) if logical_alternatives else 0,
            "raw_signed_coset_nonzero_parities": coset_sign_flips,
            "native_correction_placement_validated": correction_array is not None,
            "native_Bell_instruction_count": (
                native_bell_instruction_count if correction_array is not None else None
            ),
        },
    }


def check_full_hex_constraints(bundle):
    """Complete signed record spaces, separately from native annotations.

    Hex's unitary D encoder assumes Stim's default initial all-zero state.
    Flow analysis ordinarily treats unreset input wires as arbitrary ports;
    an analysis-only D reset makes that simulation assumption explicit. Native
    sections and frozen circuits remain unchanged.
    """
    matrices, supports = bundle.matrices, bundle.data_supports
    d, m = bundle.distance, bundle.distance**2 - 1
    preparations = {
        "D": bundle.sections["input"],
        "A": bundle.sections["prep_A"],
        "B": bundle.sections["prep_B"],
    }
    plan = derive_frame_plan(
        preparations,
        bundle.sections["entangle"],
        bundle.sections["bell_measure"],
        matrices,
        supports,
    )
    expected = []
    offset = 0
    for role, basis in (("A", "Z"), ("B", "X")):
        records = preparation_records(preparations[role], matrices, supports[role])
        local = {key: value % m for key, value in records.items()}
        expected += [1 << (offset + local[basis, j]) for j in range(len(matrices[basis]))]
        expected += [
            (1 << (offset + r * m + local[b, j])) ^ (1 << (offset + (r - 1) * m + local[b, j]))
            for r in range(1, d)
            for b in "XZ"
            for j in range(len(matrices[b]))
        ]
        offset += preparations[role].num_measurements
    bell_records = _readouts(bundle.sections["bell_measure"], supports, offset)
    for role, basis in (("D", "X"), ("A", "Z")):
        opposite = "Z" if basis == "X" else "X"
        for check in matrices[basis]:
            expected.append(
                parity(bell_records[role, j][1] for j in np.flatnonzero(check))
                ^ _xor(plan["frames"][role][opposite][j] for j in np.flatnonzero(check))
            )
    expected_open = list(expected)
    offset += bundle.sections["bell_measure"].num_measurements
    final_records = _readouts(bundle.sections["readout"], supports, offset)
    basis = bundle.basis
    opposite = "Z" if basis == "X" else "X"
    for check in matrices[basis]:
        expected.append(
            parity(final_records["B", j][1] for j in np.flatnonzero(check))
            ^ _xor(plan["frames"]["B"][opposite][j] for j in np.flatnonzero(check))
        )
    logical = matrices["L" + basis][0]
    expected.append(
        parity(final_records["B", j][1] for j in np.flatnonzero(logical))
        ^ _xor(plan["survivor_correction"][opposite][j] for j in np.flatnonzero(logical))
        ^ (bundle.bit << bundle.closed_circuit.num_measurements)
    )
    result = {}
    for label, circuit, rows, expected_rank in (
        ("open", bundle.open_circuit, expected_open, 2 * d * m),
        ("closed", bundle.closed_circuit, expected, 2 * d * m + m // 2 + 1),
    ):
        native = physical(circuit)
        initialized = stim.Circuit()
        initialized.append("R", supports["D"])
        initialized += native
        n = initialized.num_measurements
        parsed = SimpleNamespace(
            circuit=initialized, keys=tuple(range(n)), canonical_keys=tuple(range(n))
        )
        actual = measurement_constraints(parsed)
        wanted = row_space(rows)
        require(
            actual == wanted and len(actual) == expected_rank,
            f"Hex full {label} signed record constraints differ: "
            f"actual_rank={len(actual)}, expected_rank={expected_rank}, "
            f"first_difference={next(iter(set(actual) ^ set(wanted)), None)}",
        )
        native_parsed = SimpleNamespace(
            circuit=native, keys=tuple(range(n)), canonical_keys=tuple(range(n))
        )
        native_constraints = measurement_constraints(native_parsed)
        # Hex emits only prep detectors. Verify their actual rows independently,
        # without claiming this deliberately incomplete annotation is complete.
        declared, measured = [], 0
        for inst in circuit.flattened():
            if inst.name in MEASUREMENTS:
                measured += len(inst.targets_copy())
            elif inst.name == "DETECTOR":
                indices = [measured + t.value for t in inst.targets_copy()]
                require(
                    all(0 <= j < measured for j in indices),
                    f"Hex native {label} detector record outside causal prefix",
                )
                row = parity(indices)
                require(
                    initialized.has_flow(stim.Flow(measurements=indices)),
                    f"Hex native {label} declared detector has invalid signed flow: {indices}",
                )
                require(
                    row_space([*wanted, row]) == wanted,
                    f"Hex native {label} detector outside complete signed space",
                )
                declared.append(row)
        expected_native = (2 * d - 1) * m
        require(
            len(declared) == len(row_space(declared)) == expected_native,
            f"Hex native {label} detector count/independence differs",
        )
        require(circuit.num_observables == 0, "Hex native logical output is Python postprocessing")
        result[label] = {
            "measurements": n,
            "complete_signed_constraint_rank": len(actual),
            "independent_expected_rank": expected_rank,
            "free_record_bits": n - len(actual),
            "signed_basis_rows": sum(bool(row >> n) for row in actual),
            "native_detector_annotations": len(declared),
            "native_detector_rank": len(row_space(declared)),
            "native_observable_annotations": circuit.num_observables,
            "native_annotations_incomplete": True,
            "native_arbitrary_input_instrument_rank": len(native_constraints),
            "implicit_D_initialization_constraints": len(actual) - len(native_constraints),
            "default_input_interpretation": (
                "analysis-only R(D.data) before unmodified unitary encoder"
            ),
        }
    addressed = set()
    counts = Counter()
    for inst in bundle.closed_circuit.flattened():
        if inst.name in ANNOTATIONS:
            continue
        targets = inst.targets_copy()
        addressed.update(t.value for t in targets if t.is_qubit_target)
        if inst.name in ("CX", "CZ"):
            counts[inst.name] += len(targets) // 2
    result["physical_counts"] = {
        "allocated_sites": 3 * (2 * d * d - 1),
        "addressed_sites": len(addressed),
        "index_width": bundle.closed_circuit.num_qubits,
        "CX_pairs": counts["CX"],
        "CZ_pairs": counts["CZ"],
        "ticks": bundle.closed_circuit.num_ticks,
    }
    return result


def check_hex_semantics(bundle, trials=64):
    matrices, supports = bundle.matrices, bundle.data_supports
    result = {"A0": check_geometry(bundle)}
    preparations = {
        "D": bundle.sections["input"],
        "A": bundle.sections["prep_A"],
        "B": bundle.sections["prep_B"],
    }
    instruments = {
        role: check_preparation(
            preparations[role], matrices, supports[role], basis, rounds, f"Hex {role}"
        )
        for role, basis, rounds in (
            ("D", bundle.basis, 0),
            ("A", "Z", bundle.distance),
            ("B", "X", bundle.distance),
        )
    }
    result["A1"] = {
        "passed": True,
        "preparations": instruments,
        "surface_code": True,
        "full_record_constraints": check_full_hex_constraints(bundle),
    }
    d = bundle.distance
    coordinates = [(2 * (i // d) + 1, 2 * (d - 1 - i % d) + 1) for i in range(d * d)]
    alternatives = {
        basis: np.asarray([q in geometry(d).logical(basis) for q in coordinates], dtype=np.uint8)
        for basis in "XZ"
    }
    result.update(
        check_protocol_channel(
            preparations,
            bundle.sections["entangle"],
            bundle.sections["bell_measure"],
            bundle.sections["readout"],
            matrices,
            supports,
            bundle.basis,
            bundle.bit,
            trials,
            "Hex",
            bundle.correction_array,
            alternatives,
        )
    )
    return result
