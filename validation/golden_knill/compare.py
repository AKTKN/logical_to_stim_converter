"""Independent Knill physical, signed annotation, noise and channel comparisons."""

from collections import Counter
from dataclasses import dataclass, field
from itertools import zip_longest

import numpy as np
import stim

from validation.golden_memory.reference_same_schedule import geometry

from .dut_adapter import compile_dut, protocol_sections
from .normalize import (
    MEASUREMENTS,
    atoms,
    basis_map,
    canonical_dem,
    causal_moments,
    event_moments,
    measurement_constraints,
    noise_locations,
    parity,
    parse,
    patch_site,
    require,
    row_space,
)


@dataclass
class ValidationReport:
    level: str
    distance: int
    basis: str
    verified: dict = field(default_factory=dict)


def _reference(distance, basis, open_output, reference):
    from .reference_same_schedule import build_reference

    return reference or build_reference(distance, basis, open_output=open_output)


def crosscheck_metadata(compiled, parsed, distance, basis, *, open_output=False, reference=None):
    """Audit metadata against independent physical coordinates and record semantics."""
    require(
        compiled.logical_to_block == {"D": "P2"},
        f"A3 logical relocation incorrect: {compiled.logical_to_block}",
    )
    require(
        len(compiled.relocation_history) == 1
        and compiled.relocation_history[0].logical_id == "D"
        and compiled.relocation_history[0].source_block_id == "P0"
        and compiled.relocation_history[0].output_block_id == "P2",
        "A3 relocation history disagrees with D -> P2",
    )
    require(
        compiled.open_logical_outputs == ({"D": "P2"} if open_output else {}),
        "A3 open survivor output mapping mismatch",
    )
    require(
        [compiled.block_status[f"P{i}"].value for i in range(3)]
        == ["measured", "measured", "active" if open_output else "measured"],
        "A3 retired/survivor physical block states mismatch",
    )
    require(
        len(compiled.block_uses) == 3 and {u.use_id.epoch for u in compiled.block_uses} == {0},
        "B1 expected three unique physical reset epochs",
    )
    require(
        len(compiled.measurements) == len(parsed.keys)
        and len(compiled.detectors) == len(parsed.detectors),
        "B2 measurement/detector metadata cardinality mismatch",
    )
    record_moments, moment = {}, 0
    for inst in atoms(parsed.circuit):
        if inst.name == "TICK":
            moment += 1
        elif inst.name in MEASUREMENTS:
            record_moments[len(record_moments)] = moment
    for info in compiled.measurements:
        coordinate = parsed.sites[compiled.physical_qubit_map[info.key.block_id, info.key.local_id]]
        patch, _ = patch_site(coordinate, distance)
        expected = (
            ("check", patch, info.basis, coordinate, info.key.round_index + 1)
            if info.key.kind == "syndrome"
            else ("readout", patch, info.basis, coordinate)
        )
        require(
            parsed.keys[info.index] == expected
            and info.key.epoch == 0
            and info.time_layer == record_moments[info.index],
            f"B2 measurement metadata mismatch index={info.index},expected={expected},"
            f"actual={parsed.keys[info.index]},moment={record_moments[info.index]}",
        )
    columns = {k: i for i, k in enumerate(parsed.canonical_keys)}
    g = geometry(distance)
    checks = {c.coordinate: c for c in g.checks}
    reference = _reference(distance, basis, open_output, reference)
    for info in compiled.detectors:
        row = parity(columns[parsed.keys[i]] for i in info.measurement_indices)
        require(
            row == parsed.detectors[info.index], f"B2 detector metadata parity index={info.index}"
        )
        coordinate = parsed.sites[compiled.physical_qubit_map[info.block_id, info.check_id]]
        patch, local = patch_site(coordinate, distance)
        require(
            local in checks and checks[local].basis == info.basis,
            f"B2 detector check anchor index={info.index},patch={patch},site={coordinate}",
        )
        matching_anchors = [
            anchor
            for anchor, expected_row in reference.annotation_anchors.items()
            if anchor[1:4] == (patch, info.basis, local) and expected_row == row
        ]
        require(
            len(matching_anchors) == 1,
            f"B2 detector semantic anchor index={info.index},patch={patch},"
            f"check={local},basis={info.basis},row={parsed.describe(row)}",
        )
        expected_support = set()
        for i in info.measurement_indices:
            key = parsed.keys[i]
            _, key_local = patch_site(key[3], distance)
            if key[0] == "check":
                offset = key[3][0] - key_local[0]
                expected_support.update((q[0] + offset, q[1]) for q in checks[key_local].support)
            else:
                expected_support.add(key[3])
        actual_support = {
            parsed.sites[compiled.physical_qubit_map[s]] for s in info.physical_support
        }
        require(
            actual_support == expected_support,
            f"B2 detector physical support index={info.index},anchor={coordinate},"
            f"expected={expected_support},actual={actual_support}",
        )
        source_blocks = {compiled.measurements[i].key.block_id for i in info.measurement_indices}
        require(
            set(info.supporting_block_ids) == source_blocks
            and {u.block_id for u in info.source_use_ids} == source_blocks
            and info.anchor_use_id.block_id == info.block_id
            and info.anchor_use_id.epoch == 0,
            f"B2 detector block/use provenance index={info.index}",
        )
    for info in compiled.observables:
        row = parity(columns[parsed.keys[i]] for i in info.measurement_indices)
        require(
            row == parsed.observables[info.index]
            and info.basis == basis
            and info.block_id == "P2"
            and info.logical_id == "D",
            f"B2 observable metadata basis/coset index={info.index}",
        )
    bell = compiled.bell_measurements[0]
    require(
        bell.physical_output_frame.block_id == "P2"
        and bell.physical_output_frame.block_use_id.block_id == "P2"
        and bell.physical_output_frame.block_use_id.epoch == 0,
        "A3 physical survivor frame attached to wrong block/use",
    )
    by_key = {m.key: m.index for m in compiled.measurements}
    for axis, terms, patch, read_basis in (
        ("x", bell.raw_byproduct.x_terms, "A", "Z"),
        ("z", bell.raw_byproduct.z_terms, "D", "X"),
    ):
        actual = {parsed.keys[by_key[k]] for k in terms}
        offset = ("D", "A", "B").index(patch) * (2 * distance + 2)
        expected = {
            ("readout", patch, read_basis, (q[0] + offset, q[1])) for q in g.logical(read_basis)
        }
        require(
            actual == expected,
            f"A3 raw byproduct {axis} must follow Z^m_X X^m_Z: expected={expected},actual={actual}",
        )
    require(
        not bell.raw_byproduct.x_constant and not bell.raw_byproduct.z_constant,
        "A3 raw byproduct unexpected signed constant",
    )


def compare_ideal_circuits(actual, expected, distance, basis, *, open_output=False):
    """B1 and B2 are explicit gates: noise comparisons must pass both first."""
    a = parse(actual, distance, basis, open_output=open_output)
    b = parse(expected, distance, basis, open_output=open_output)
    ma, mb = causal_moments(a), causal_moments(b)
    require(len(ma) == len(mb), f"B1 global moment/TICK count DUT={len(ma)},reference={len(mb)}")
    for moment, (ac, ex) in enumerate(zip(ma, mb, strict=True)):
        require(ac == ex, f"B1 causal physical schedule moment={moment},expected={ex},actual={ac}")
    require(a.canonical_keys == b.canonical_keys, "B1 physical semantic record mapping differs")
    ca, cb = measurement_constraints(a), measurement_constraints(b)
    require(ca == cb, "B2 complete signed affine instrument constraints differ")
    transform = basis_map(a.detectors, b.detectors)
    require(set(a.observables) == set(b.observables), "B2 observable ID set differs")
    for obs_id, row in b.observables.items():
        require(
            row_space([*b.detectors, a.observables[obs_id] ^ row]) == row_space(b.detectors),
            f"B2 observable coset mismatch id={obs_id},"
            f"expected={b.describe(row)},actual={a.describe(a.observables[obs_id])}",
        )
    require(
        row_space([*a.detectors, *a.observables.values()]) == ca,
        "B2 DUT annotations do not span complete deterministic signed constraints",
    )
    require(
        row_space([*b.detectors, *b.observables.values()]) == cb,
        "B2 independent annotations do not span complete deterministic signed constraints",
    )
    counts = Counter(e.name for events in event_moments(a) for e in events)
    n = distance * distance
    require(
        counts["CX"] == 4 * distance * (distance - 1) * (1 + 2 * distance) + 2 * n,
        f"B1 independent physical CX count violated: {counts['CX']}",
    )
    return (
        a,
        b,
        {
            "B1": {
                "passed": True,
                "sites": len(a.sites),
                "moments": len(ma),
                "ticks": len(ma) - 1,
                "physical_gates": dict(counts),
                "measurements": len(a.keys),
                "open_output": open_output,
            },
            "B2": {
                "passed": True,
                "signed_affine_rank": len(ca),
                "raw_free_dimension": len(a.keys) - len(ca),
                "detectors": len(a.detectors),
                "observables": len(a.observables),
                "detector_basis_map_hex": [hex(r) for r in transform],
                "identical_detector_rows": a.detectors == b.detectors,
                "complete_signed_space": True,
                "observable_coset": True,
            },
        },
    )


def check_same_schedule_ideal(
    distance,
    basis,
    *,
    open_output=False,
    dut=None,
    reference=None,
):
    reference = _reference(distance, basis, open_output, reference)
    dut = dut or compile_dut(distance, basis, open_output=open_output)
    a, _, details = compare_ideal_circuits(
        dut.ideal_circuit, reference.circuit, distance, basis, open_output=open_output
    )
    crosscheck_metadata(dut, a, distance, basis, open_output=open_output, reference=reference)
    return ValidationReport("B1/B2", distance, basis, details)


def _settings(heterogeneous):
    if not heterogeneous:
        return {}, {}
    return (
        {
            "LogicalInit": {"reset": 0.061, "idle": 0.062},
            "TransversalCNOT": {"two_qubit": 0.063},
            "LogicalMeasure": {"measurement": 0.064, "idle": 0.065},
        },
        {
            "D.init": {"reset": 0.071, "measurement": 0},
            "KnillEC": {"two_qubit": 0.072, "idle": 0.073},
            "B.readout": {"measurement": 0.074, "idle": 0},
        },
    )


def _independent_overrides(instance_overrides):
    """Authored composite policy applies to precisely these six primitive uses."""
    result = {k: v for k, v in instance_overrides.items() if k != "KnillEC"}
    if "KnillEC" in instance_overrides:
        for operation in (
            "A.prep",
            "B.prep",
            "Bell.entangle",
            "Bell.measure.cnot",
            "D.bell_readout",
            "A.bell_readout",
        ):
            result[operation] = instance_overrides["KnillEC"]
    return result


def compare_noisy_circuits(actual, expected, distance, basis, reference, *, open_output=False):
    """Compare complete physical noise traces before exact native DEM extraction."""
    a = parse(actual, distance, basis, open_output=open_output)
    b = parse(expected, distance, basis, open_output=open_output)
    ma, mb = causal_moments(a), causal_moments(b)
    require(
        len(ma) == len(mb) == len(reference.moments),
        f"C1/C2 noisy TICK count expected={len(mb) - 1},actual={len(ma) - 1},"
        f"independent_reference={len(reference.moments) - 1}",
    )

    def keyed_locations(parsed):
        result = Counter()
        for location, multiplicity in noise_locations(parsed).items():
            stage = reference.moments[location.moment].stage
            uses = tuple(sorted({(patch_site(q, distance)[0], 0) for q in location.targets}))
            result[(stage, uses, location)] += multiplicity
        return result

    la, lb = keyed_locations(a), keyed_locations(b)
    require(la == lb, f"C1/C2 exact noise multiset missing={lb - la},unexpected={la - lb}")
    for moment, (ac, ex) in enumerate(zip(ma, mb, strict=True)):
        require(
            ac == ex,
            f"C1/C2 noisy causal physical schedule moment={moment},"
            f"stage={reference.moments[moment].stage},expected={ex},actual={ac}",
        )
    counts, stages, probabilities = Counter(), Counter(), {}
    for (_, _, location), count in lb.items():
        channel = location.channel
        counts[channel] += count
        stage = reference.moments[location.moment].stage
        if (
            location.moment == reference.resource_boundary_moment + 1
            and location.channel == "DEPOLARIZE1"
            and location.side == "before"
        ):
            stage = "resource_post_se"
        patches = ",".join(sorted({patch_site(q, distance)[0] + "@0" for q in location.targets}))
        stages[f"{stage}:{patches}:{channel}"] += count
        probabilities.setdefault(channel, set()).add(location.probability)
    ideal_ref = parse(reference.circuit, distance, basis, open_output=open_output)
    da, db = canonical_dem(a, ideal_ref), canonical_dem(b, ideal_ref)
    if da != db:

        def describe(instruction):
            if instruction is None:
                return "<end of native DEM>"
            args = [(repr(p), float(p).hex()) for p in instruction.args_copy()]
            targets = [str(t) for t in instruction.targets_copy()]
            components = [[]]
            for target in targets:
                if target == "^":
                    components.append([])
                else:
                    components[-1].append(target)
            return (
                f"instruction={str(instruction)!r},type={instruction.type},"
                f"exact_args_repr_hex={args},targets={targets},"
                f"correlated_components={components}"
            )

        first = next(
            (i, actual_row, expected_row)
            for i, (actual_row, expected_row) in enumerate(
                zip_longest(da.flattened(), db.flattened())
            )
            if actual_row != expected_row
        )
        require(
            False,
            f"C1/C2 native exact common-basis DEM mismatch "
            f"DUT_rows={da.num_errors},reference_rows={db.num_errors},"
            f"first_native_instruction={first[0]},DUT=({describe(first[1])}),"
            f"reference=({describe(first[2])})",
        )
    return {
        "passed": True,
        "noise_locations": dict(counts),
        "noise_locations_by_stage_use": dict(sorted(stages.items())),
        "exact_probabilities": {k: sorted(v) for k, v in probabilities.items()},
        "exact_native_dem": True,
        "dem_errors": da.num_errors,
        "common_independent_detector_basis": True,
    }


def check_same_schedule_noise(
    distance,
    basis,
    *,
    open_output=False,
    heterogeneous=False,
    dut=None,
    noisy_circuit=None,
    reference=None,
    probes=True,
):
    from .faults import check_fault_probes
    from .reference_noise import ReferenceNoise, add_noise

    reference = _reference(distance, basis, open_output, reference)
    noise = ReferenceNoise(0.01, 0.02, 0.03, 0.04, 0.05)
    type_overrides, instance_overrides = _settings(heterogeneous)
    dut = dut or compile_dut(
        distance,
        basis,
        noise,
        open_output=open_output,
        type_overrides=type_overrides,
        instance_overrides=instance_overrides,
    )
    # This gate is deliberately before constructing or comparing the noisy oracle.
    baseline = check_same_schedule_ideal(
        distance, basis, open_output=open_output, dut=dut, reference=reference
    )
    expected = add_noise(
        reference,
        noise,
        type_overrides=type_overrides,
        instance_overrides=_independent_overrides(instance_overrides),
    )
    details = compare_noisy_circuits(
        dut.circuit if noisy_circuit is None else noisy_circuit,
        expected,
        distance,
        basis,
        reference,
        open_output=open_output,
    )
    details["heterogeneous_precedence"] = heterogeneous
    if probes:
        details["fault_probes"] = check_fault_probes(
            dut.ideal_circuit, reference, distance, basis, open_output=open_output
        )
    return ValidationReport("C1", distance, basis, {**baseline.verified, "C1": details})


def check_m9_noise(
    distance,
    basis,
    *,
    p_st=0.003,
    background=True,
    open_output=False,
    dut=None,
    noisy_circuit=None,
    reference=None,
    probes=True,
):
    from .faults import check_fault_probes
    from .reference_noise import ReferenceNoise, add_noise

    reference = _reference(distance, basis, open_output, reference)
    noise = ReferenceNoise(0.01, 0.02, 0.03, 0.04, 0.05) if background else ReferenceNoise()
    # Ordinary validation is a mandatory gate even for zero-background M9 cases.
    ordinary = check_same_schedule_noise(
        distance, basis, open_output=open_output, reference=reference, probes=False
    )
    dut = dut or compile_dut(
        distance, basis, noise, open_output=open_output, m9_enabled=True, p_st=p_st
    )
    check_same_schedule_ideal(
        distance, basis, open_output=open_output, dut=dut, reference=reference
    )
    expected = add_noise(reference, noise, m9_enabled=True, p_st=p_st)
    details = compare_noisy_circuits(
        dut.circuit if noisy_circuit is None else noisy_circuit,
        expected,
        distance,
        basis,
        reference,
        open_output=open_output,
    )
    details.update(
        {
            "p_st": p_st,
            "ordinary_background": background,
            "ordinary_gate_passed": ordinary.verified["C1"]["passed"],
        }
    )
    boundaries = dut.resource_preparation_boundaries
    require(
        len(boundaries) == 2 and {b.block_use_id.block_id for b in boundaries} == {"P1", "P2"},
        "C2 M9 resource boundary ownership mismatch",
    )
    require(
        all((b.channel_instruction is not None) == bool(p_st) for b in boundaries),
        "C2 M9 zero/nonzero stochastic boundary mismatch",
    )
    ideal_ticks = [i + 1 for i, inst in enumerate(dut.ideal_circuit) if inst.name == "TICK"]
    for boundary in boundaries:
        patch = {"P1": "A", "P2": "B"}[boundary.block_use_id.block_id]
        expected_sites = {
            reference.sites[reference.indices[patch, q]] for q in reference.geometry.data
        }
        actual_sites = {
            tuple(
                map(
                    int,
                    dut.ideal_circuit.get_final_qubit_coordinates()[dut.physical_qubit_map[s]][:2],
                )
            )
            for s in boundary.data_sites
        }
        require(
            boundary.first_layer == reference.resource_first_moment
            and boundary.final_se_layer == reference.resource_boundary_moment
            and boundary.ideal_boundary_instruction
            == ideal_ticks[reference.resource_boundary_moment]
            and actual_sites == expected_sites,
            f"C2 M9 independent boundary/data metadata patch={patch},"
            f"expected interval={reference.resource_first_moment}:"
            f"{reference.resource_boundary_moment},sites={expected_sites},actual={boundary}",
        )
        if boundary.channel_instruction is not None:
            prefix = list(dut.circuit)[: boundary.channel_instruction]
            while prefix and prefix[-1].tag.startswith("resource_post_se:"):
                prefix.pop()
            require(
                prefix[-1].name == "TICK"
                and sum(inst.name == "TICK" for inst in prefix)
                == reference.resource_boundary_moment + 1,
                f"C2 M9 channel must immediately follow existing final SE TICK patch={patch}",
            )
    if probes:
        details["fault_probes"] = check_fault_probes(
            dut.ideal_circuit, reference, distance, basis, open_output=open_output
        )
    return ValidationReport(
        "C2",
        distance,
        basis,
        {
            "B1": ordinary.verified["B1"],
            "B2": ordinary.verified["B2"],
            "ordinary_gate": {"passed": True, "exact_native_dem": True},
            "C2": details,
        },
    )


def _matrices_and_supports(compiled, distance):
    """Independent lattice matrices, aligned to physical occupied coordinates."""
    g = geometry(distance)
    coordinates = {
        tuple(map(int, q[:2])): i
        for i, q in compiled.ideal_circuit.get_final_qubit_coordinates().items()
    }
    matrices = {
        b: np.array(
            [[q in c.support for q in g.data] for c in g.checks if c.basis == b], dtype=np.uint8
        )
        for b in "XZ"
    }
    matrices.update(
        {"L" + b: np.array([[q in g.logical(b) for q in g.data]], dtype=np.uint8) for b in "XZ"}
    )
    supports = {
        p: tuple(coordinates[q[0] + i * (2 * distance + 2), q[1]] for q in g.data)
        for i, p in enumerate(("D", "A", "B"))
    }
    return matrices, supports


def check_dut_frame_metadata(
    compiled, distance, basis, sections, matrices, supports, *, bit=0, virtual=False, trials=64
):
    """Supply independent CSS recovery to public replay; compare every survivor site."""
    from .hex_semantics import derive_frame_plan, solve_gf2

    parsed = parse(compiled.ideal_circuit, distance, basis, open_output=True)
    g = geometry(distance)
    preparations = {p: sections[p] for p in ("D", "A", "B")}
    plan = derive_frame_plan(
        preparations, sections["entangle"], sections["bell_measure"], matrices, supports
    )
    # The oracle assembles disjoint preparations serially. Only records are
    # permuted here; no physical schedule equivalence is inferred from this view.
    serial = stim.Circuit()
    for inst in compiled.ideal_circuit:
        if inst.name == "QUBIT_COORDS":
            serial.append(inst)
    serial += sections["D"] + sections["A"] + sections["B"]
    serial += sections["entangle"] + sections["bell_measure"]
    serial_parsed = parse(serial, distance, basis, open_output=True)
    simulators, records = [], []
    for shot in range(max(64, trials)):
        sim = stim.TableauSimulator(seed=0x714000 + shot)
        sim.do(compiled.ideal_circuit)
        simulators.append(sim)
        records.append(sim.current_measurement_record())
    raw = np.array(records, dtype=np.bool_)
    serial_raw = raw[:, [parsed.key_to_record[k] for k in serial_parsed.keys]]

    def evaluate(mask):
        indices = [j for j in range(serial_raw.shape[1]) if (mask >> j) & 1]
        return (
            np.logical_xor.reduce(serial_raw[:, indices], axis=1)
            if indices
            else np.zeros(len(raw), dtype=np.bool_)
        )

    corrections = {}
    for prep in compiled.preparations:
        patch = ("D", "A", "B")[int(prep.block_id[1:])]
        final = 1 if patch == "D" else distance
        offset = ("D", "A", "B").index(patch) * (2 * distance + 2)
        syndromes = {
            b: raw[
                :,
                [
                    parsed.key_to_record[
                        ("check", patch, b, (c.coordinate[0] + offset, c.coordinate[1]), final)
                    ]
                    for c in g.checks
                    if c.basis == b
                ],
            ]
            for b in "XZ"
        }
        xs = [
            solve_gf2(np.vstack((matrices["Z"], matrices["LZ"])), np.r_[s, 0])
            for s in syndromes["Z"]
        ]
        zs = [
            solve_gf2(np.vstack((matrices["X"], matrices["LX"])), np.r_[s, 0])
            for s in syndromes["X"]
        ]
        positions = [
            g.data.index(
                patch_site(parsed.sites[compiled.physical_qubit_map[prep.block_id, q]], distance)[1]
            )
            for q in prep.data_ids
        ]
        corrections[prep.module_id] = tuple(
            prep.resolve(x[positions], z[positions]) for x, z in zip(xs, zs, strict=True)
        )
    evaluated = compiled.evaluate_frames(raw, corrections)
    actual_bell = next(iter(evaluated.bell_measurements.values()))
    for b, actual in (("X", actual_bell.corrected_x), ("Z", actual_bell.corrected_z)):
        expected_bit = evaluate(plan["bell_bits"][b]) ^ bool(virtual and bit and b == basis)
        require(
            np.array_equal(actual, expected_bit),
            f"A3 DUT corrected Bell {b} disagrees with independent preparation frame",
        )
    for shot, frame in enumerate(evaluated.final_frames["D"]):
        for axis, actual in (("X", frame.x_support), ("Z", frame.z_support)):
            expected = {
                supports["B"][j]
                for j, mask in enumerate(plan["survivor_correction"][axis])
                if evaluate(mask)[shot]
            }
            if virtual and bit and axis == ("Z" if basis == "X" else "X"):
                logical = {supports["B"][j] for j in np.flatnonzero(matrices["L" + axis][0])}
                expected.symmetric_difference_update(logical)
            actual_sites = {compiled.physical_qubit_map["P2", q] for q in actual}
            require(
                actual_sites == expected,
                f"A3 DUT survivor physical frame axis={axis},shot={shot},"
                f"expected={expected},actual={actual_sites}",
            )
        sim = simulators[shot].copy()
        for axis, terms in (("x", frame.x_support), ("z", frame.z_support)):
            if terms:
                getattr(sim, axis)(*[compiled.physical_qubit_map["P2", q] for q in terms])
        p = stim.PauliString(compiled.ideal_circuit.num_qubits)
        for j in np.flatnonzero(matrices["L" + basis][0]):
            p[supports["B"][j]] = basis
        require(
            sim.peek_observable_expectation(p) == (-1) ** bit,
            f"A3 DUT executed survivor frame signed state basis={basis},bit={bit},shot={shot}",
        )
    return {
        "passed": True,
        "same_raw_records": len(raw),
        "independent_CSS_recovery": True,
        "corrected_Bell_bits": True,
        "every_survivor_physical_XZ_site": True,
        "executed_frame_signed_state": True,
        "virtual_input": virtual,
    }


def check_dut_ideal_semantics(distance, basis, *, bit=0, virtual=False, trials=64, dut=None):
    from .hex_semantics import check_preparation, check_protocol_channel

    dut = dut or compile_dut(distance, basis, open_output=True, bit=bit, virtual=virtual)
    sections = protocol_sections(dut)
    matrices, supports = _matrices_and_supports(dut, distance)
    instruments = {
        p: check_preparation(sections[p], matrices, supports[p], b, r, f"DUT {p}")
        for p, b, r in (("D", basis, 1), ("A", "X", distance), ("B", "Z", distance))
    }
    # A direct final physical readout of B is used on an independent simulator.
    readout = stim.Circuit()
    readout.append("MX" if basis == "X" else "M", supports["B"])
    semantics = check_protocol_channel(
        {p: sections[p] for p in ("D", "A", "B")},
        sections["entangle"],
        sections["bell_measure"],
        readout,
        matrices,
        supports,
        basis,
        0 if virtual else bit,
        trials,
        "DUT",
    )
    parsed = parse(dut.ideal_circuit, distance, basis, open_output=True)
    crosscheck_metadata(dut, parsed, distance, basis, open_output=True)
    frames = check_dut_frame_metadata(
        dut, distance, basis, sections, matrices, supports, bit=bit, virtual=virtual, trials=trials
    )
    # Certify the actual public closed program, including signed and virtual
    # inputs. The expected physical parity comes from independent logical strings.
    closed = compile_dut(distance, basis, bit=bit, virtual=virtual)
    closed_parsed = parse(closed.ideal_circuit, distance, basis)
    independent = _reference(distance, basis, False, None)
    independent_parsed = parse(independent.circuit, distance, basis)
    logical_row = independent_parsed.observables[0]
    record_indices = [
        closed_parsed.key_to_record[k]
        for j, k in enumerate(closed_parsed.canonical_keys)
        if (logical_row >> j) & 1
    ]
    flow = stim.Flow(
        measurements=record_indices, output=stim.PauliString("-" if bit and not virtual else "+")
    )
    require(
        closed.ideal_circuit.has_flow(flow),
        f"A3 actual closed public program signed parity basis={basis},bit={bit}: {flow}",
    )
    require(
        row_space([*independent_parsed.detectors, closed_parsed.observables[0] ^ logical_row])
        == row_space(independent_parsed.detectors)
        and closed.observables[0].expected_value == bit
        and closed.observables[0].frame_correction.constant == bool(virtual and bit),
        "A3 actual closed public observable signed metadata/coset mismatch",
    )
    semantics["A3"]["actual_closed_public_signed_parity"] = True
    return {
        "A1": {"passed": True, "preparations": instruments},
        **semantics,
        "DUT_frame_metadata": frames,
    }


def check_hex_ideal_semantics(distance, basis, *, bit=0, hex_bundle=None, trials=64):
    from .fixtures import verify_hex_fixture
    from .hex_semantics import check_hex_semantics

    bundle = hex_bundle if hex_bundle is not None else verify_hex_fixture(distance, basis, bit=bit)
    hex_result = check_hex_semantics(bundle, trials=trials)
    dut_result = check_dut_ideal_semantics(distance, basis, bit=bit, trials=trials)
    return ValidationReport(
        "A0/A1/A2/A3",
        distance,
        basis,
        {
            "Hex": hex_result,
            "DUT": dut_result,
            **{k: {"passed": True} for k in ("A0", "A1", "A2", "A3")},
        },
    )
