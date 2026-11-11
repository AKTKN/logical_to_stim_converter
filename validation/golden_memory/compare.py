"""Separate A/B/C validators. A mismatch raises an actionable Mismatch assertion."""

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import stim

from .normalize import (
    ANNOTATIONS,
    MEASUREMENTS,
    NOISE,
    atoms,
    canonical_dem,
    causal_moments,
    expected_annotations,
    measurement_constraints,
    noise_locations,
    parity,
    parse,
    require,
    row_space,
)
from .reference_same_schedule import FULL_NOISE, ReferenceNoise, build_reference, geometry
from .reference_stim import build_standard


@dataclass
class ValidationReport:
    level: str
    distance: int
    basis: str
    verified: dict = field(default_factory=dict)


def compile_dut(distance, basis, noise=None):
    """The only construction bridge to the device under test; never an oracle."""
    from logical_to_stim_converter import (
        CircuitCompiler,
        CodeSpec,
        LogicalBlock,
        LogicalInit,
        LogicalMeasure,
        NoiseModel,
        NoiseParameters,
        SyndromeExtraction,
    )

    block = LogicalBlock.placed("D", CodeSpec.rotated_surface(distance))
    model = None if noise is None else NoiseModel(NoiseParameters(**vars(noise)))
    return CircuitCompiler([block], logical_to_block={"D": "D"}).compile(
        [LogicalInit("D", basis, 1), SyndromeExtraction("D", 2), LogicalMeasure("D", basis)],
        noise_model=model,
    )


def annotations(parsed, distance, basis, label):
    expected, logical = expected_annotations(distance, basis)
    require(
        len(parsed.detectors) == len(expected),
        f"{label} detector count expected={len(expected)} actual={len(parsed.detectors)}",
    )
    # Compare both the keyed rows (for signatures) and the spaces (for full constraints).
    actual = Counter(parsed.detectors)
    wanted = Counter(expected.values())
    for anchor, row in expected.items():
        require(
            actual[row] == wanted[row],
            f"{label} detector parity mismatch check/basis/coordinate/round={anchor}: "
            f"expected={parsed.describe(row)}, unexpected="
            f"{[parsed.describe(r) for r in (actual - wanted)]}",
        )
    require(
        row_space(parsed.detectors) == row_space(expected.values()),
        f"{label} detector row space mismatch",
    )
    require(
        parsed.observables == {0: logical},
        f"{label} observable parity mismatch basis={basis}: expected={parsed.describe(logical)}, "
        f"actual={ {i: parsed.describe(r) for i, r in parsed.observables.items()} }",
    )
    return expected, logical


def crosscheck_metadata(compiled, parsed, distance, basis):
    g = geometry(distance)
    expected_rows, _ = expected_annotations(distance, basis)
    anchors = {row: anchor for anchor, row in expected_rows.items()}
    require(
        len(compiled.measurements) == len(parsed.keys)
        and len(compiled.detectors) == len(parsed.detectors)
        and len(compiled.observables) == 1,
        "DUT metadata cardinality mismatch",
    )
    for info in compiled.measurements:
        coordinate = parsed.sites[
            compiled.physical_qubit_map[(info.key.block_id, info.key.local_id)]
        ]
        expected = (
            ("check", info.basis, coordinate, info.key.round_index + 1)
            if info.key.kind == "syndrome"
            else ("readout", info.basis, coordinate)
        )
        require(
            parsed.keys[info.index] == expected
            and info.time_layer == (6 * expected[3] if expected[0] == "check" else 19),
            f"DUT measurement metadata mismatch index={info.index}: "
            f"parsed={parsed.keys[info.index]}, metadata={expected}",
        )
    columns = {k: i for i, k in enumerate(parsed.canonical_keys)}
    for info in compiled.detectors:
        row = parity(columns[parsed.keys[i]] for i in info.measurement_indices)
        coordinate = parsed.sites[compiled.physical_qubit_map[(info.block_id, info.check_id)]]
        check = next(c for c in g.checks if c.coordinate == coordinate)
        expected_support = {q for q in check.support}
        actual_support = {
            parsed.sites[compiled.physical_qubit_map[s]] for s in info.physical_support
        }
        require(
            row == parsed.detectors[info.index]
            and info.basis == check.basis
            and anchors[row][:2] == (check.basis, coordinate)
            and set(info.measurement_keys)
            == {compiled.measurements[i].key for i in info.measurement_indices}
            and actual_support == expected_support,
            f"DUT detector metadata mismatch check={check}, row={parsed.describe(row)}",
        )
    for info in compiled.observables:
        row = parity(columns[parsed.keys[i]] for i in info.measurement_indices)
        require(
            row == parsed.observables[info.index] and info.basis == basis,
            f"DUT observable metadata mismatch basis={basis}, index={info.index}",
        )


def round_instruments(parsed, distance, *, standard):
    """Discard ancillas at each boundary. MR supplies the next round's R state.

    The first standard R is split to omit the data preparation. Later standard
    segments start with an explicit ancilla R, the exact output of the prior MR.
    No ancilla output Pauli is imposed; all flow ports are on data alone.
    """
    g = geometry(distance)
    ancillas = {i for i, q in parsed.sites.items() if q not in g.data}
    result, segment, measured = [], stim.Circuit(), 0
    for inst in atoms(parsed.circuit.without_noise()):
        if inst.name in ANNOTATIONS:
            continue
        ts = inst.targets_copy()
        if inst.name == "TICK":
            segment.append(inst)
            continue
        if inst.name in ("R", "RX") and ts[0].value not in ancillas:
            continue
        if inst.name in MEASUREMENTS and ts[0].value not in ancillas:
            continue
        segment.append(inst)
        if inst.name in MEASUREMENTS:
            measured += 1
            if measured == len(ancillas):
                result.append(segment)
                segment, measured = stim.Circuit(), 0
                if standard:
                    segment.append("R", sorted(ancillas))
    require(len(result) == 3, f"Round instrument count expected=3 actual={len(result)}")
    return result


def check_round_flows(parsed, distance, *, standard, label):
    g = geometry(distance)
    lookup = {q: i for i, q in parsed.sites.items()}
    count = 0
    for t, segment in enumerate(round_instruments(parsed, distance, standard=standard), 1):
        record = {}
        for inst in atoms(segment):
            if inst.name in MEASUREMENTS:
                record[parsed.sites[inst.targets_copy()[0].value]] = len(record)
        for c in g.checks:
            p = stim.PauliString(parsed.circuit.num_qubits)
            for q in c.support:
                p[lookup[q]] = c.basis
            flows = [
                stim.Flow(input=p, measurements=[record[c.coordinate]]),
                stim.Flow(output=p, measurements=[record[c.coordinate]]),
            ]
            for flow in flows:
                require(
                    segment.has_flow(flow),
                    f"{label} round flow mismatch round={t}, check={c}, signed_flow={flow}",
                )
                count += 1
        for b in "XZ":
            p = stim.PauliString(parsed.circuit.num_qubits)
            for q in g.logical(b):
                p[lookup[q]] = b
            flow = stim.Flow(input=p, output=p)
            require(
                segment.has_flow(flow),
                f"{label} logical round flow mismatch round={t}, basis={b}, support={g.logical(b)}",
            )
            count += 1
    return count


def ideal_semantic_equivalence(dut, distance, basis, *, standard_circuit=None):
    circuit = dut.ideal_circuit if hasattr(dut, "ideal_circuit") else dut
    standard_circuit = (
        build_standard(distance, basis) if standard_circuit is None else standard_circuit
    )
    report = ValidationReport("A", distance, basis)
    spaces = []
    for label, candidate, standard in (("DUT", circuit, False), ("Stim", standard_circuit, True)):
        parsed = parse(candidate, distance, basis, standard=standard)
        rows, logical = annotations(parsed, distance, basis, label)
        expected = row_space([*rows.values(), logical])
        actual = measurement_constraints(parsed)
        difference = set(actual) ^ set(expected)
        require(
            actual == expected,
            f"{label} complete signed affine space mismatch: expected_rank={len(expected)}, "
            f"actual_rank={len(actual)}, first_row="
            f"{parsed.describe(min(difference)) if difference else None}",
        )
        require(
            len(actual) == 3 * (distance**2 - 1) + 1,
            f"{label} ideal affine rank mismatch {len(actual)}",
        )
        require(
            len(parsed.keys) - len(actual) == distance**2 - 1,
            f"{label} additional or missing ideal record constraints",
        )
        report.verified[label + "_round_signed_flows"] = check_round_flows(
            parsed, distance, standard=standard, label=label
        )
        det, obs = candidate.compile_detector_sampler(seed=711).sample(
            64, separate_observables=True
        )
        require(not det.any() and not obs.any(), f"{label} nonzero ideal detector/observable smoke")
        if label == "DUT" and hasattr(dut, "measurements"):
            crosscheck_metadata(dut, parsed, distance, basis)
        spaces.append(actual)
    require(spaces[0] == spaces[1], "A mapped affine supports disagree")
    report.verified.update(
        affine_rank=len(spaces[0]),
        free_record_bits=distance**2 - 1,
        occupied_sites=2 * distance**2 - 1,
        measurements=4 * distance**2 - 3,
        detectors=3 * (distance**2 - 1),
        observables=1,
    )
    return report


@dataclass(frozen=True)
class Fault:
    key: tuple
    atom: int
    pauli: str
    probability: float
    result: bool = False


def common_faults(parsed, distance):
    """Read actual noisy operations, with explicit elementary (not DEM-row) identity."""
    stream = atoms(parsed.circuit)
    g = geometry(distance)
    checks = {c.coordinate: c for c in g.checks}
    history, seen, faults = {}, Counter(), {}
    for index, inst in enumerate(stream):
        name = inst.name
        if name in ANNOTATIONS or name == "TICK":
            continue
        require(
            name not in NOISE - {"X_ERROR", "Z_ERROR"},
            f"B unsupported noise channel outside reset/readout scope: {inst}",
        )
        q = inst.targets_copy()[0].value
        coordinate = parsed.sites[q]
        check = checks.get(coordinate)
        b = check.basis if check else parsed.keys[-1][1]
        role = "check" if check else "data"
        if name in ("X_ERROR", "Z_ERROR"):
            previous = history.get(q)
            # A pre-measure error's next physical operation on this wire is M/MX/MR.
            following = next(
                (
                    op
                    for op in stream[index + 1 :]
                    if op.name not in ANNOTATIONS | NOISE | {"TICK"}
                    and q in [t.value for t in op.targets_copy()]
                ),
                None,
            )
            measurement = following is not None and following.name in MEASUREMENTS
            kind = "measurement" if measurement else "reset"
            if not measurement:
                require(
                    previous in ("R", "RX", "MR"),
                    f"B reset fault has no causal reset parent site={coordinate}: {inst}",
                )
            t = seen[coordinate] + 1 if check else 0
            key = (kind, role, b, coordinate, t)
            require(key not in faults, f"B duplicate elementary mechanism {key}")
            faults[key] = Fault(key, index, name[0], inst.gate_args_copy()[0])
        elif name in MEASUREMENTS:
            if inst.gate_args_copy() and inst.gate_args_copy()[0]:
                key = ("measurement", role, b, coordinate, seen[coordinate] + 1 if check else 0)
                require(key not in faults, f"B duplicate result flip {key}")
                faults[key] = Fault(
                    key, index, "Z" if name == "MX" else "X", inst.gate_args_copy()[0], True
                )
            seen[coordinate] += 1
            history[q] = name
        elif name not in NOISE:
            for target in inst.targets_copy():
                history[target.value] = name
    return faults


def force_fault(parsed, fault):
    circuit = stim.Circuit()
    for index, inst in enumerate(atoms(parsed.circuit)):
        if index == fault.atom:
            circuit.append(fault.pauli, [inst.targets_copy()[0].value])
        if inst.name in NOISE:
            continue
        if inst.name in MEASUREMENTS:
            circuit.append(inst.name, inst.targets_copy())
        else:
            circuit.append(inst)
    return circuit


def signature(circuit, distance, basis, *, standard=False):
    """Exact deterministic annotated response; verify every signed parity with Stim."""
    parsed = parse(circuit, distance, basis, standard=standard)
    rows, logical = annotations(parsed, distance, basis, "fault signature")
    sample = circuit.reference_sample()
    signed, response = [], []
    for row in [r for _, r in sorted(rows.items())] + [logical]:
        records = [
            parsed.key_to_record[k] for j, k in enumerate(parsed.canonical_keys) if (row >> j) & 1
        ]
        bit = bool(np.bitwise_xor.reduce(sample[records]))
        response.append(bit)
        signed.append(stim.Flow(output=stim.PauliString("-" if bit else "+"), measurements=records))
    require(circuit.has_all_flows(signed), "Fault response is not a deterministic signed parity")
    return tuple(response)


def common_noise_equivalence(dut, distance, basis, *, standard_circuit=None):
    circuit = dut.circuit if hasattr(dut, "circuit") else dut
    standard_circuit = (
        build_standard(distance, basis, common_noise=True)
        if standard_circuit is None
        else standard_circuit
    )
    a = parse(circuit, distance, basis)
    b = parse(standard_circuit, distance, basis, standard=True)
    annotations(a, distance, basis, "B DUT")
    annotations(b, distance, basis, "B Stim")
    fa, fb = common_faults(a, distance), common_faults(b, distance)
    unmatched = {k for k in fb if k not in fa}
    expected_inert = {
        ("reset", "check", c.basis, c.coordinate, 4) for c in geometry(distance).checks
    }
    require(
        unmatched == expected_inert and set(fa) == set(fb) - unmatched,
        f"B elementary location bijection mismatch DUT_only={set(fa) - set(fb)}, "
        f"Stim_only={unmatched}, expected_inert={expected_inert}",
    )
    require(len(fa) == 2 * (4 * distance**2 - 3), f"B matched fault count differs: {len(fa)}")
    zero, signatures = 0, Counter()
    for key in sorted(fa):
        require(
            fa[key].probability == fb[key].probability == 0.01,
            f"B probability mismatch mechanism={key}: DUT={fa[key]}, Stim={fb[key]}",
        )
        sa = signature(force_fault(a, fa[key]), distance, basis)
        sb = signature(force_fault(b, fb[key]), distance, basis, standard=True)
        require(sa == sb, f"B fault signature mismatch mechanism={key}: DUT={sa}, Stim={sb}")
        zero += not any(sa)
        signatures[sa] += 1
    for key in sorted(unmatched):
        s = signature(force_fault(b, fb[key]), distance, basis, standard=True)
        require(not any(s), f"B terminal MR reset is not inert mechanism={key}: signature={s}")
    return ValidationReport(
        "B",
        distance,
        basis,
        {
            "matched_elementary_faults": len(fa),
            "matched_zero_signature": zero,
            "unmatched_inert_terminal_MR_resets": len(unmatched),
            "distinct_matched_signatures": len(signatures),
        },
    )


def exact_schedule_equivalence(dut, distance, basis, *, noisy=False, reference=None):
    circuit = dut.circuit if hasattr(dut, "circuit") else dut
    reference = (
        build_reference(distance, basis, FULL_NOISE if noisy else ReferenceNoise())
        if reference is None
        else reference
    )
    a, b = parse(circuit, distance, basis), parse(reference, distance, basis)
    annotations(a, distance, basis, "C DUT")
    annotations(b, distance, basis, "C golden")
    ma, mb = causal_moments(a), causal_moments(b)
    require(
        len(ma) == len(mb) == 20,
        f"C physical moment/TICK count expected=20/19 actual_DUT={len(ma)}/{len(ma) - 1} "
        f"golden={len(mb)}/{len(mb) - 1}",
    )
    for moment, (actual, expected) in enumerate(zip(ma, mb, strict=True)):
        require(
            actual == expected,
            f"C physical schedule mismatch moment={moment}, round={(moment - 1) // 6 + 1}: "
            f"expected={expected}, actual={actual}",
        )
    la, lb = noise_locations(a), noise_locations(b)
    require(la == lb, f"C noise multiset mismatch missing={lb - la}, unexpected={la - lb}")
    counts = Counter()
    for location, count in la.items():
        category = "reset" if location.channel in ("X_ERROR", "Z_ERROR") else location.channel
        counts[category] += count
    if noisy:
        n, m = distance**2, distance**2 - 1
        expected_counts = Counter(
            {
                "reset": n + 3 * m,
                "DEPOLARIZE2": 12 * distance * (distance - 1),
                "measurement_flip": n + 3 * m,
                "DEPOLARIZE1": 2 * m + 3 * (2 * n + 4 * (2 * distance - 1)),
            }
        )
        require(
            counts == expected_counts,
            f"C atomic noise counts expected={expected_counts}, actual={counts}",
        )
    else:
        require(not counts, f"C ideal circuit unexpectedly has noise {counts}")
    # Re-extract from every physical instruction, with independently canonical annotations.
    da, db = canonical_dem(a, distance, basis), canonical_dem(b, distance, basis)
    require(da == db, "C native canonical DEM mismatch (exact double probabilities)")
    probes = 0
    # Beginning, middle and end of each round; force all three Pauli axes on data.
    # These probes compare physical propagation separately from stochastic channels.
    ideal_a = a.circuit.without_noise()
    ideal_b = b.circuit.without_noise()
    coordinate = geometry(distance).data[0]
    for moment in (1, 3, 6, 7, 9, 12, 13, 15, 18):
        for pauli in "XYZ":

            def inject(candidate):
                parsed = parse(candidate, distance, basis)
                q = next(i for i, c in parsed.sites.items() if c == coordinate)
                out, current = stim.Circuit(), 0
                for inst in candidate.flattened():
                    if inst.name == "TICK":
                        if current == moment:
                            out.append(pauli, [q])
                        current += 1
                    out.append(inst)
                return out

            sa = signature(inject(ideal_a), distance, basis)
            sb = signature(inject(ideal_b), distance, basis)
            require(
                sa == sb,
                f"C deterministic probe mismatch moment={moment}, site={coordinate}, "
                f"Pauli={pauli}, DUT={sa}, golden={sb}",
            )
            probes += 1
    return ValidationReport(
        "C2" if noisy else "C1",
        distance,
        basis,
        {
            "moments": len(ma),
            "ticks": len(ma) - 1,
            "noise_locations": dict(counts),
            "exact_native_dem": True,
            "deterministic_Pauli_probes": probes,
        },
    )
