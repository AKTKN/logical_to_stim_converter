"""Independent Knill signed instruments, moments, categorical faults and mutations."""

from dataclasses import replace

import pytest
import stim

from validation.golden_knill.compare import (
    _matrices_and_supports,
    check_dut_ideal_semantics,
    check_hex_ideal_semantics,
    check_m9_noise,
    check_same_schedule_ideal,
    check_same_schedule_noise,
    compare_ideal_circuits,
    compare_noisy_circuits,
    crosscheck_metadata,
)
from validation.golden_knill.dut_adapter import compile_dut, protocol_sections
from validation.golden_knill.hex_semantics import check_protocol_channel, check_round_instrument
from validation.golden_knill.normalize import Mismatch, atoms, parse
from validation.golden_knill.reference_noise import FULL_NOISE, add_noise
from validation.golden_knill.reference_same_schedule import build_reference


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
def test_hex_and_dut_signed_identity_channel(distance, basis, bit):
    result = check_hex_ideal_semantics(distance, basis, bit=bit)
    assert all(result.verified[k]["passed"] for k in ("A0", "A1", "A2", "A3"))
    for source in ("Hex", "DUT"):
        assert result.verified[source]["A3"]["two_axis_signed_channel_flows"] == 2
        assert len(result.verified[source]["A3"]["observed_corrected_Bell_branches"]) == 4
    assert result.verified["DUT"]["DUT_frame_metadata"]["every_survivor_physical_XZ_site"]


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_virtual_signed_input_frame(distance, basis):
    result = check_dut_ideal_semantics(distance, basis, bit=1, virtual=True)
    assert result["DUT_frame_metadata"]["virtual_input"]
    assert result["DUT_frame_metadata"]["executed_frame_signed_state"]


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("open_output", [False, True])
def test_same_schedule_ideal_complete_signed_space(distance, basis, open_output):
    result = check_same_schedule_ideal(distance, basis, open_output=open_output)
    assert result.verified["B1"]["sites"] == 3 * (2 * distance**2 - 1)
    assert result.verified["B2"]["complete_signed_space"]
    assert (
        len(result.verified["B2"]["detector_basis_map_hex"]) == result.verified["B2"]["detectors"]
    )


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("kind", ["closed", "open", "heterogeneous"])
def test_independent_ordinary_channels_and_native_dem(distance, basis, kind):
    result = check_same_schedule_noise(
        distance, basis, open_output=kind == "open", heterogeneous=kind == "heterogeneous"
    )
    assert result.verified["C1"]["exact_native_dem"]
    assert result.verified["C1"]["fault_probes"]["all_Bell_CX_15_Paulis"]
    assert result.verified["C1"]["fault_probes"]["terminal_idle_all_inert"]
    assert result.verified["C1"]["fault_probes"]["terminal_idle_probes"] == (
        (2 if kind == "open" else 1) * 3 * (distance**2 - 1)
    )
    assert result.verified["C1"]["fault_probes"]["survivor_physical_actions"] == (kind == "open")


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("p_st", [0, 0.003])
@pytest.mark.parametrize("background", [False, True])
def test_m9_independent_suppression_boundary_and_dem(distance, basis, p_st, background):
    result = check_m9_noise(distance, basis, p_st=p_st, background=background, probes=False)
    assert result.verified["C2"]["exact_native_dem"]
    assert result.verified["C2"]["ordinary_gate_passed"]


def _rewrite_one(circuit, predicate, edit):
    result, changed = stim.Circuit(), False
    for instruction in atoms(circuit):
        if not changed and predicate(instruction):
            for replacement in edit(instruction):
                result.append(replacement)
            changed = True
        else:
            result.append(instruction)
    assert changed, "Mutation must change a real physical instruction"
    return result


@pytest.mark.parametrize("mutation", ["delete", "reverse", "support", "timing", "bell_basis"])
def test_B1_physical_mutations_fail_at_causal_schedule(mutation):
    r = build_reference(3, "Z")
    compare_ideal_circuits(r.circuit, r.circuit, 3, "Z")
    if mutation == "bell_basis":

        def predicate(i):
            return i.name == "MX" and i.targets_copy()[0].value == r.indices["D", (1, 1)]

        def edit(i):
            return [stim.CircuitInstruction("M", i.targets_copy())]

        diagnostic = "readout basis"
    else:

        def predicate(i):
            return i.name == "CX"

        def edit(i):
            targets = i.targets_copy()
            if mutation == "delete":
                return []
            if mutation == "reverse":
                return [stim.CircuitInstruction("CX", targets[::-1])]
            if mutation == "support":
                return [stim.CircuitInstruction("CX", [targets[0], r.indices["D", (5, 5)]])]
            return [stim.CircuitInstruction("TICK"), i]

        diagnostic = "B1.*(schedule|moment/TICK)"
    mutant = _rewrite_one(r.circuit, predicate, edit)
    with pytest.raises(Mismatch, match=diagnostic):
        compare_ideal_circuits(mutant, r.circuit, 3, "Z")


@pytest.mark.parametrize("kind", ["delete", "reverse", "support"])
def test_A1_signed_instrument_detects_check_CX_corruption(kind):
    c = compile_dut(3, "Z", open_output=True)
    matrices, supports = _matrices_and_supports(c, 3)
    r = build_reference(3, "Z")
    # One independent round, excluding its data reset and subsequent preparation.
    segment, t = stim.Circuit(), 0
    for i in r.circuit:
        if i.name == "TICK":
            t += 1
        elif 1 <= t <= 6 and i.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS"):
            segment.append(i)
    ref_support = tuple(r.indices["D", q] for q in r.geometry.data)
    check_round_instrument(segment, matrices, {b: matrices["L" + b] for b in "XZ"}, ref_support)

    def edit(i):
        targets = i.targets_copy()
        if kind == "delete":
            return []
        return [
            stim.CircuitInstruction(
                "CX", targets[::-1] if kind == "reverse" else [targets[0], r.indices["D", (5, 5)]]
            )
        ]

    mutant = _rewrite_one(segment, lambda i: i.name == "CX", edit)
    with pytest.raises(Mismatch, match="signed.*instrument failed"):
        check_round_instrument(mutant, matrices, {b: matrices["L" + b] for b in "XZ"}, ref_support)


@pytest.mark.parametrize("mutation", ["detector", "observable", "representative"])
def test_B2_signed_annotation_mutations(mutation):
    r = build_reference(3, "Z")
    compare_ideal_circuits(r.circuit, r.circuit, 3, "Z")
    name = "DETECTOR" if mutation == "detector" else "OBSERVABLE_INCLUDE"

    def edit(i):
        targets = i.targets_copy()
        if mutation == "representative":
            # A physical data representative changed without its syndrome term.
            targets += [stim.target_rec(-1), stim.target_rec(-2)]
        else:
            targets[0] = stim.target_rec(targets[0].value + 1)
        return [stim.CircuitInstruction(i.name, targets, i.gate_args_copy())]

    mutant = _rewrite_one(r.circuit, lambda i: i.name == name, edit)
    with pytest.raises(Mismatch, match="B2.*(parity|observable|record|constraint)"):
        compare_ideal_circuits(mutant, r.circuit, 3, "Z")


@pytest.mark.parametrize("mutation", ["entangle", "readout", "preparation_frame"])
def test_A2_A3_physical_and_gauge_mutations(mutation, monkeypatch):
    import validation.golden_knill.hex_semantics as semantics

    c = compile_dut(3, "Z", open_output=True)
    sections = protocol_sections(c)
    matrices, supports = _matrices_and_supports(c, 3)
    readout = stim.Circuit()
    readout.append("M", supports["B"])
    args = (
        {p: sections[p] for p in "DAB"},
        sections["entangle"],
        sections["bell_measure"],
        readout,
        matrices,
        supports,
        "Z",
        0,
    )
    check_protocol_channel(*args)
    if mutation == "entangle":
        sections["entangle"] = _rewrite_one(
            sections["entangle"],
            lambda i: i.name == "CX",
            lambda i: [stim.CircuitInstruction("CX", i.targets_copy()[::-1])],
        )
    elif mutation == "readout":
        sections["bell_measure"] = _rewrite_one(
            sections["bell_measure"],
            lambda i: i.name == "MX",
            lambda i: [stim.CircuitInstruction("M", i.targets_copy())],
        )
    else:
        original = semantics._symbolic_frames

        def missing_frame(*a, **kw):
            frames, offset, records = original(*a, **kw)
            frames["A"] = {axis: [0] * len(v) for axis, v in frames["A"].items()}
            return frames, offset, records

        monkeypatch.setattr(semantics, "_symbolic_frames", missing_frame)
    args = (
        {p: sections[p] for p in "DAB"},
        sections["entangle"],
        sections["bell_measure"],
        readout,
        matrices,
        supports,
        "Z",
        0,
    )
    with pytest.raises(Mismatch, match="(signed two-axis identity|Bell.*basis|recovered.*flow)"):
        check_protocol_channel(*args)


def test_A3_byproduct_XZ_metadata_swap_is_detected():
    c = compile_dut(3, "Z", open_output=True)
    p = parse(c.ideal_circuit, 3, "Z", open_output=True)
    crosscheck_metadata(c, p, 3, "Z", open_output=True)
    bell = c.bell_measurements[0]
    swapped = replace(
        bell.raw_byproduct, x_terms=bell.raw_byproduct.z_terms, z_terms=bell.raw_byproduct.x_terms
    )
    mutant = replace(c, bell_measurements=(replace(bell, raw_byproduct=swapped),))
    with pytest.raises(Mismatch, match=r"raw byproduct.*Z\^m_X X\^m_Z"):
        crosscheck_metadata(mutant, p, 3, "Z", open_output=True)


@pytest.mark.parametrize("mutation", ["support", "logical"])
def test_A0_native_Hex_geometry_mutations(mutation):
    from validation.golden_knill.fixtures import verify_hex_fixture
    from validation.golden_knill.hex_semantics import check_geometry

    bundle = verify_hex_fixture(3, "Z")
    assert check_geometry(bundle)["passed"]
    matrices = {k: v.copy() for k, v in bundle.matrices.items()}
    matrices["X" if mutation == "support" else "LX"][0, 0] ^= 1
    with pytest.raises(Mismatch, match="A0.*(anticommute|commutation|coset)"):
        check_geometry(replace(bundle, matrices=matrices))


@pytest.mark.parametrize("mutation", ["byproduct", "signed_input"])
def test_A3_branch_specific_signed_channel_mutations(mutation, monkeypatch):
    import validation.golden_knill.hex_semantics as semantics

    c = compile_dut(3, "X", open_output=True)
    sections = protocol_sections(c)
    matrices, supports = _matrices_and_supports(c, 3)
    readout = stim.Circuit()
    readout.append("MX", supports["B"])
    args = (
        {p: sections[p] for p in "DAB"},
        sections["entangle"],
        sections["bell_measure"],
        readout,
        matrices,
        supports,
        "X",
        0,
    )
    check_protocol_channel(*args)
    if mutation == "byproduct":
        original = semantics._bell_bits

        def swap_bits(*a, **kw):
            bits = original(*a, **kw)
            return {"X": bits["Z"], "Z": bits["X"]}

        monkeypatch.setattr(semantics, "_bell_bits", swap_bits)
    else:
        args = (*args[:-1], 1)
    with pytest.raises(Mismatch, match="(signed two-axis identity channel|signed eigenvalue)"):
        check_protocol_channel(*args)


@pytest.mark.parametrize(
    "mutation",
    [
        "before_reset",
        "drop_CX",
        "duplicate_CX",
        "CX_probability",
        "CX_target",
        "measurement",
        "D_waiting_idle",
        "inactive_idle",
    ],
)
def test_C1_exact_noise_location_mutations(mutation):
    r = build_reference(3, "Z")
    noisy = add_noise(r)
    compare_noisy_circuits(noisy, noisy, 3, "Z", r)
    if mutation == "before_reset":
        instructions = atoms(noisy)
        index = next(i for i, inst in enumerate(instructions) if inst.name == "X_ERROR")
        fault = instructions.pop(index)
        reset = next(
            i
            for i, inst in enumerate(instructions)
            if inst.name == "R" and inst.targets_copy() == fault.targets_copy()
        )
        instructions.insert(reset, fault)
        mutant = stim.Circuit()
        for inst in instructions:
            mutant.append(inst)
    elif mutation == "inactive_idle":
        mutant = noisy.copy()
        mutant.insert(0, stim.CircuitInstruction("DEPOLARIZE1", [r.indices["A", (1, 1)]], [0.05]))
    elif mutation == "D_waiting_idle":
        mutant, changed, moment = stim.Circuit(), False, 0
        for inst in atoms(noisy):
            if inst.name == "TICK":
                moment += 1
            if (
                not changed
                and moment == r.resource_first_moment
                and inst.name == "DEPOLARIZE1"
                and inst.targets_copy()[0].value == r.indices["D", (1, 1)]
            ):
                changed = True
                continue
            mutant.append(inst)
        assert changed
    else:
        name = "M" if mutation == "measurement" else "DEPOLARIZE2"

        def edit(i):
            if mutation == "drop_CX":
                return []
            if mutation == "duplicate_CX":
                return [i, i]
            if mutation == "CX_probability":
                return [stim.CircuitInstruction(i.name, i.targets_copy(), [0.031])]
            if mutation == "CX_target":
                return [stim.CircuitInstruction(i.name, i.targets_copy()[::-1], i.gate_args_copy())]
            return [stim.CircuitInstruction("MX", i.targets_copy(), i.gate_args_copy())]

        mutant = _rewrite_one(noisy, lambda i: i.name == name, edit)
    with pytest.raises(Mismatch, match="(exact noise multiset|check readout basis)"):
        compare_noisy_circuits(mutant, noisy, 3, "Z", r)


@pytest.mark.parametrize("mutation", ["ancilla", "double", "before_SE", "zero_suppression"])
def test_C2_m9_boundary_mutations(mutation):
    r = build_reference(3, "Z")
    p = 0 if mutation == "zero_suppression" else 0.003
    noisy = add_noise(r, FULL_NOISE, m9_enabled=True, p_st=p)
    compare_noisy_circuits(noisy, noisy, 3, "Z", r)
    if mutation == "zero_suppression":
        mutant = add_noise(r, FULL_NOISE)
    elif mutation == "before_SE":
        instructions = atoms(noisy)
        selected = next(
            i
            for i, inst in enumerate(instructions)
            if inst.name == "DEPOLARIZE1" and inst.gate_args_copy() == [0.003]
        )
        channel = instructions.pop(selected)
        instructions.insert(
            next(i for i, inst in enumerate(instructions) if inst.name == "TICK"), channel
        )
        mutant = stim.Circuit()
        for inst in instructions:
            mutant.append(inst)
    else:

        def edit(i):
            if mutation == "double":
                return [i, i]
            q = r.indices["A", r.geometry.checks[0].coordinate]
            return [stim.CircuitInstruction(i.name, [q], i.gate_args_copy())]

        mutant = _rewrite_one(
            noisy, lambda i: i.name == "DEPOLARIZE1" and i.gate_args_copy() == [0.003], edit
        )
    with pytest.raises(Mismatch, match="exact noise multiset"):
        compare_noisy_circuits(mutant, noisy, 3, "Z", r)


def test_noise_gate_stops_after_ideal_failure():
    r = build_reference(3, "Z")
    c = compile_dut(3, "Z", FULL_NOISE)
    mutant = _rewrite_one(c.ideal_circuit, lambda i: i.name == "CX", lambda i: [])
    with pytest.raises(Mismatch, match="B1 causal physical schedule"):
        check_same_schedule_noise(3, "Z", dut=replace(c, ideal_circuit=mutant), probes=False)
    assert r.circuit.num_measurements == c.ideal_circuit.num_measurements


def test_extra_noisy_tick_fails_with_schedule_diagnostic():
    r = build_reference(3, "Z")
    noisy = add_noise(r)
    compare_noisy_circuits(noisy, noisy, 3, "Z", r)
    mutant = noisy.copy()
    mutant.append("TICK")
    mutant.append("DEPOLARIZE1", [r.indices["B", (1, 1)]], 0.05)
    with pytest.raises(
        Mismatch, match=r"noisy TICK count expected=29,actual=30,independent_reference=29"
    ):
        compare_noisy_circuits(mutant, noisy, 3, "Z", r)


def test_native_dem_prior_mismatch_reports_exact_instruction_and_components(monkeypatch):
    import validation.golden_knill.compare as comparison

    r = build_reference(3, "Z")
    noisy = add_noise(r)
    compare_noisy_circuits(noisy, noisy, 3, "Z", r)
    actual_probability, expected_probability = 0.010000000000000002, 0.01
    actual = stim.DetectorErrorModel()
    expected = stim.DetectorErrorModel()
    targets = [
        stim.target_relative_detector_id(0),
        stim.target_relative_detector_id(1),
        stim.target_separator(),
        stim.target_relative_detector_id(2),
        stim.target_logical_observable_id(0),
    ]
    actual.append("error", actual_probability, targets)
    expected.append("error", expected_probability, targets)
    models = iter((actual, expected))
    monkeypatch.setattr(comparison, "canonical_dem", lambda *args: next(models))
    with pytest.raises(Mismatch, match="native exact common-basis DEM mismatch") as caught:
        compare_noisy_circuits(noisy, noisy, 3, "Z", r)
    diagnostic = str(caught.value)
    assert "first_native_instruction=0" in diagnostic
    assert actual_probability.hex() in diagnostic and expected_probability.hex() in diagnostic
    assert "correlated_components=[['D0', 'D1'], ['D2', 'L0']]" in diagnostic
    assert "targets=['D0', 'D1', '^', 'D2', 'L0']" in diagnostic


@pytest.mark.parametrize("level", ["C1", "C2"])
def test_explicit_empty_noisy_candidate_is_checked(level):
    checker = check_same_schedule_noise if level == "C1" else check_m9_noise
    baseline = checker(3, "Z", probes=False)
    assert baseline.verified[level]["passed"]
    with pytest.raises(Mismatch, match="occupied physical sites mismatch"):
        checker(3, "Z", noisy_circuit=stim.Circuit(), probes=False)
