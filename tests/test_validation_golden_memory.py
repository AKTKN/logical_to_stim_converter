"""Independent A/B/C physical oracles, exact signed spaces and deliberate corruptions."""

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import stim

from validation.golden_memory.compare import (
    annotations,
    check_round_flows,
    common_noise_equivalence,
    compile_dut,
    exact_schedule_equivalence,
    ideal_semantic_equivalence,
)
from validation.golden_memory.normalize import (
    Mismatch,
    atoms,
    causal_moments,
    measurement_constraints,
    noise_locations,
    parse,
    row_space,
)
from validation.golden_memory.reference_same_schedule import (
    FULL_NOISE,
    ReferenceNoise,
    build_reference,
    geometry,
)
from validation.golden_memory.reference_stim import build_standard
from validation.golden_memory.run import FIXTURES, verify_fixture

CASES = [(d, b) for d in (3, 5) for b in ("X", "Z")]


@pytest.fixture(scope="module", params=CASES, ids=lambda c: f"d{c[0]}_{c[1]}")
def case(request):
    d, b = request.param
    return d, b, compile_dut(d, b)


def test_A_complete_signed_semantic_equivalence(case):
    d, b, dut = case
    result = ideal_semantic_equivalence(dut, d, b)
    assert result.verified["affine_rank"] == {3: 25, 5: 73}[d]
    assert result.verified["free_record_bits"] == {3: 8, 5: 24}[d]
    standard = build_standard(d, b)
    assert standard.num_qubits > len(standard.get_final_qubit_coordinates())
    parsed = parse(standard, d, b, standard=True)
    # Complementary first-round checks remain random: neither signed constant is a flow.
    key = next(k for k in parsed.keys if k[0] == "check" and k[1] != b and k[3] == 1)
    record = parsed.key_to_record[key]
    assert not standard.has_flow(stim.Flow(measurements=[record]))
    assert not standard.has_flow(stim.Flow(output=stim.PauliString("-"), measurements=[record]))


def test_C1_independent_ideal_fixture(case):
    d, b, dut = case
    fixture = verify_fixture(d, b)
    result = exact_schedule_equivalence(dut, d, b, reference=fixture)
    assert result.verified["ticks"] == 19
    assert result.verified["deterministic_Pauli_probes"] == 27


def test_B_all_matched_elementary_faults(case):
    d, b, _ = case
    dut = compile_dut(d, b, ReferenceNoise(reset=0.01, measurement=0.01))
    result = common_noise_equivalence(dut, d, b)
    assert result.verified["matched_elementary_faults"] == {3: 66, 5: 194}[d]
    assert result.verified["unmatched_inert_terminal_MR_resets"] == d * d - 1
    assert result.verified["matched_zero_signature"] == 0


def test_C2_full_noisy_causal_schedule(case):
    d, b, _ = case
    dut = compile_dut(d, b, FULL_NOISE)
    result = exact_schedule_equivalence(dut, d, b, noisy=True)
    expected = {3: (33, 72, 33, 130), 5: (97, 240, 97, 306)}[d]
    counts = result.verified["noise_locations"]
    assert (
        tuple(counts[k] for k in ("reset", "DEPOLARIZE2", "measurement_flip", "DEPOLARIZE1"))
        == expected
    )
    assert result.verified["exact_native_dem"]


@pytest.mark.parametrize("d", [3, 5])
def test_independent_geometry_algebra_and_reviewed_supports(d):
    g = geometry(d)
    assert len(g.sites) == len(set(g.sites)) == 2 * d * d - 1
    masks = {
        b: [sum(1 << g.data.index(q) for q in c.support) for c in g.checks if c.basis == b]
        for b in "XZ"
    }
    assert len(row_space(masks["X"])) + len(row_space(masks["Z"])) == d * d - 1
    assert all((x & z).bit_count() % 2 == 0 for x in masks["X"] for z in masks["Z"])
    logicals = {b: sum(1 << g.data.index(q) for q in g.logical(b)) for b in "XZ"}
    assert (logicals["X"] & logicals["Z"]).bit_count() % 2 == 1
    for b, other in (("X", "Z"), ("Z", "X")):
        assert all((logicals[b] & check).bit_count() % 2 == 0 for check in masks[other])
    if d == 3:
        labels = {q: f"D{i + 1}" for i, q in enumerate(g.data)}
        assert [
            [{labels[q] for q in c.support} for c in g.checks if c.basis == b] for b in "XZ"
        ] == [
            [{"D1", "D2"}, {"D2", "D3", "D5", "D6"}, {"D4", "D5", "D7", "D8"}, {"D8", "D9"}],
            [{"D1", "D2", "D4", "D5"}, {"D3", "D6"}, {"D4", "D7"}, {"D5", "D6", "D8", "D9"}],
        ]
        assert [{labels[q] for q in g.logical(b)} for b in "XZ"] == [
            {"D1", "D4", "D7"},
            {"D1", "D2", "D3"},
        ]


def assemble(stream):
    circuit = stim.Circuit()
    for inst in stream:
        circuit.append(inst)
    return circuit


def edit_first(circuit, name, edit):
    stream = atoms(circuit)
    index = next(i for i, inst in enumerate(stream) if inst.name == name)
    replacement = edit(stream[index])
    stream[index : index + 1] = replacement
    return assemble(stream)


def altered(inst, *, name=None, targets=None, args=None):
    return stim.CircuitInstruction(
        name or inst.name,
        inst.targets_copy() if targets is None else targets,
        inst.gate_args_copy() if args is None else args,
    )


@pytest.fixture(scope="module")
def ideal3():
    circuit = compile_dut(3, "Z").ideal_circuit
    ideal_semantic_equivalence(circuit, 3, "Z")
    exact_schedule_equivalence(circuit, 3, "Z")
    return circuit


@pytest.mark.parametrize("mutation", ["delete", "reverse", "support"])
def test_physical_check_CX_corruptions_fail_A_and_C(ideal3, mutation):
    def edit(inst):
        ts = inst.targets_copy()
        if mutation == "delete":
            return []
        if mutation == "reverse":
            return [altered(inst, targets=ts[::-1])]
        # Preserve the gate count, but substitute a data vertex outside this check.
        parsed = parse(ideal3, 3, "Z")
        anc = next(q.value for q in ts if parsed.sites[q.value] not in geometry(3).data)
        check = next(c for c in geometry(3).checks if c.coordinate == parsed.sites[anc])
        wrong = next(
            i for i, q in parsed.sites.items() if q in geometry(3).data and q not in check.support
        )
        return [altered(inst, targets=[q if q.value == anc else wrong for q in ts])]

    bad = edit_first(ideal3, "CX", edit)
    with pytest.raises(Mismatch, match="signed affine space|round flow"):
        ideal_semantic_equivalence(bad, 3, "Z")
    with pytest.raises(Mismatch, match="physical schedule mismatch moment="):
        exact_schedule_equivalence(bad, 3, "Z")


def test_noncommuting_layer_swap_fails_C(ideal3):
    stream, moments = atoms(ideal3), [[]]
    for inst in stream:
        if inst.name == "TICK":
            moments.append([])
        else:
            moments[-1].append(inst)
    moments[2], moments[3] = moments[3], moments[2]
    bad = stim.Circuit()
    for i, moment in enumerate(moments):
        if i:
            bad.append("TICK")
        bad += assemble(moment)
    with pytest.raises(Mismatch, match="physical schedule mismatch moment=2"):
        exact_schedule_equivalence(bad, 3, "Z")


@pytest.mark.parametrize("name", ["DETECTOR", "OBSERVABLE_INCLUDE"])
def test_annotation_corruption_fails_A_and_C(ideal3, name):
    bad = edit_first(ideal3, name, lambda inst: [altered(inst, targets=[stim.target_rec(-1)])])
    for validator in (ideal_semantic_equivalence, exact_schedule_equivalence):
        with pytest.raises(Mismatch, match="detector parity|observable parity"):
            validator(bad, 3, "Z")


def test_check_support_annotation_with_same_counts_is_rejected(ideal3):
    stream = atoms(ideal3)
    index = next(
        i
        for i, inst in enumerate(stream)
        if inst.name == "DETECTOR" and len(inst.targets_copy()) == 5
    )
    ts = stream[index].targets_copy()
    ts[-1] = stim.target_rec(-8)  # A different data vertex; cardinality remains five.
    stream[index] = altered(stream[index], targets=ts)
    bad = assemble(stream)
    for validator in (ideal_semantic_equivalence, exact_schedule_equivalence):
        with pytest.raises(Mismatch, match="detector parity"):
            validator(bad, 3, "Z")


def test_final_tick_boundary_is_required(ideal3):
    stream = atoms(ideal3)
    del stream[max(i for i, inst in enumerate(stream) if inst.name == "TICK")]
    with pytest.raises(Mismatch, match="moment/TICK count"):
        exact_schedule_equivalence(assemble(stream), 3, "Z")


@pytest.fixture(scope="module")
def noisy3():
    circuit = compile_dut(3, "Z", FULL_NOISE).circuit
    exact_schedule_equivalence(circuit, 3, "Z", noisy=True)
    return circuit


@pytest.mark.parametrize(
    "mutation",
    [
        "reset_before",
        "reset_basis",
        "reset_target",
        "CX_noise_omit",
        "CX_noise_probability",
        "CX_noise_target",
        "idle_omit",
        "idle_duplicate",
        "idle_used",
        "idle_inactive",
        "idle_after_terminal",
        "measurement_probability",
        "measurement_target",
    ],
)
def test_noisy_schedule_mutations_are_rejected(noisy3, mutation):
    stream = atoms(noisy3)

    def find(name):
        return next(i for i, inst in enumerate(stream) if inst.name == name)

    if mutation.startswith("reset"):
        i = find("X_ERROR")
        inst = stream[i]
        q = inst.targets_copy()[0].value
        if mutation == "reset_before":
            reset = next(
                j
                for j, op in enumerate(stream)
                if op.name == "R" and op.targets_copy()[0].value == q
            )
            del stream[i]
            stream.insert(reset, inst)
        elif mutation == "reset_basis":
            stream[i] = altered(inst, name="Z_ERROR")
        else:
            stream[i] = altered(inst, targets=[0])  # Ancilla, not reset data.
    elif mutation.startswith("CX_noise"):
        i = find("DEPOLARIZE2")
        if mutation == "CX_noise_omit":
            del stream[i]
        elif mutation == "CX_noise_probability":
            stream[i] = altered(stream[i], args=[0.031])
        else:
            stream[i] = altered(stream[i], targets=stream[i].targets_copy()[::-1])
    elif mutation.startswith("idle"):
        i = find("DEPOLARIZE1")
        if mutation == "idle_omit":
            del stream[i]
        elif mutation == "idle_duplicate":
            stream.insert(i, stream[i])
        elif mutation == "idle_used":
            q = next(inst.targets_copy()[0].value for inst in stream if inst.name == "R")
            stream[i] = altered(stream[i], targets=[q])
        elif mutation == "idle_inactive":
            stream.insert(0, stim.CircuitInstruction("QUBIT_COORDS", [100], [100, 100]))
            stream.append(stim.CircuitInstruction("DEPOLARIZE1", [100], [0.05]))
        else:
            stream += [
                stim.CircuitInstruction("TICK", []),
                stim.CircuitInstruction("DEPOLARIZE1", [0], [0.05]),
            ]
    else:
        i = find("MX")
        if mutation == "measurement_probability":
            stream[i] = altered(stream[i], args=[0.041])
        else:
            # Move the result-flip channel to a different measurement, keeping gates fixed.
            j = next(j for j in range(i + 1, len(stream)) if stream[j].name == "MX")
            stream[i] = altered(stream[i], args=[])
            stream[j] = altered(stream[j], args=[0.08])
    with pytest.raises(Mismatch, match="schedule mismatch|site bijection|moment/TICK"):
        exact_schedule_equivalence(assemble(stream), 3, "Z", noisy=True)


@pytest.mark.parametrize("mutation", ["reset_basis", "fault_target", "probability"])
def test_B_rejects_changed_elementary_faults(mutation):
    dut = compile_dut(3, "Z", ReferenceNoise(reset=0.01, measurement=0.01)).circuit
    common_noise_equivalence(dut, 3, "Z")
    if mutation == "reset_basis":
        bad = edit_first(dut, "X_ERROR", lambda inst: [altered(inst, name="Z_ERROR")])
        diagnostic = "fault signature mismatch mechanism="
    elif mutation == "probability":
        bad = edit_first(dut, "MX", lambda inst: [altered(inst, args=[0.02])])
        diagnostic = "probability mismatch mechanism="
    else:
        # Duplicate a physical fault target while retaining the channel count.
        standard = build_standard(3, "Z", common_noise=True)
        stream = atoms(standard)
        i = next(
            i
            for i, inst in enumerate(stream)
            if inst.name == "X_ERROR" and stream[i + 1].name == "X_ERROR"
        )
        # Alter a physical reset fault target to a different role without dropping its channel.
        stream[i] = altered(stream[i], targets=[stream[i + 1].targets_copy()[0]])
        with pytest.raises(Mismatch, match="duplicate elementary|location bijection|causal reset"):
            common_noise_equivalence(dut, 3, "Z", standard_circuit=assemble(stream))
        return
    with pytest.raises(Mismatch, match=diagnostic):
        common_noise_equivalence(bad, 3, "Z")


def test_signed_elimination_tracks_phases_and_absence_of_extra_constraints(ideal3):
    # Bell's XX and ZZ generators multiply to -YY; the deterministic Y parity is odd.
    circuit = stim.Circuit("R 0 1\nH 0\nCX 0 1\nMY 0 1")
    from validation.golden_memory.normalize import Parsed

    keys = (("readout", "Y", (0, 0)), ("readout", "Y", (1, 0)))
    parsed = Parsed(circuit, {}, keys, dict(zip(keys, range(2))), (), {})
    assert measurement_constraints(parsed) == (0b111,)
    # Extra data preparation/gate changes the signed ideal support even with annotations intact.
    bad = edit_first(
        ideal3, "M", lambda inst: [stim.CircuitInstruction("X", inst.targets_copy()), inst]
    )
    with pytest.raises(Mismatch, match="signed affine space"):
        ideal_semantic_equivalence(bad, 3, "Z")
    # Missing a round interaction fails the independent nondemolition proof directly.
    bad = edit_first(ideal3, "CX", lambda _: [])
    with pytest.raises(Mismatch, match="round flow mismatch round=1"):
        check_round_flows(parse(bad, 3, "Z"), 3, standard=False, label="mutated")


def test_GF2_annotation_multiplicity_and_permutation(ideal3):
    parsed = parse(ideal3, 3, "Z")
    assert row_space([0b101, 0b110, 0b011]) == row_space([0b110, 0b101])
    # Repeated record operands cancel modulo two; annotation order is immaterial.
    changed = edit_first(
        ideal3,
        "DETECTOR",
        lambda inst: [
            altered(inst, targets=inst.targets_copy() + [stim.target_rec(-1), stim.target_rec(-1)])
        ],
    )
    annotations(parse(changed, 3, "Z"), 3, "Z", "multiplicity")
    assert parse(changed, 3, "Z").detectors == parsed.detectors


def test_normalization_commutes_only_disjoint_events(noisy3):
    parsed = parse(noisy3, 3, "Z")
    stream = atoms(noisy3)
    first_reset = next(i for i, inst in enumerate(stream) if inst.name == "R")
    # Adjacent resets are disjoint and may be represented in either order.
    stream[first_reset], stream[first_reset + 1] = stream[first_reset + 1], stream[first_reset]
    assert causal_moments(parse(assemble(stream), 3, "Z")) == causal_moments(parsed)
    # A duplicate idle channel survives the Counter and is never collapsed into a set.
    duplicate = edit_first(noisy3, "DEPOLARIZE1", lambda inst: [inst, inst])
    counter = noise_locations(parse(duplicate, 3, "Z"))
    assert sum(counter.values()) == sum(noise_locations(parsed).values()) + 1
    # Production metadata is cross-checked, not accepted as expected physics.
    compiled = compile_dut(3, "Z")
    records = (replace(compiled.measurements[0], basis="Z"), *compiled.measurements[1:])
    with pytest.raises(Mismatch, match="measurement metadata mismatch"):
        ideal_semantic_equivalence(replace(compiled, measurements=records), 3, "Z")


def test_reference_has_no_converter_dependency_and_fixtures_are_read_only(tmp_path):
    script = """
import builtins
original = builtins.__import__
def independent(name, *args, **kwargs):
    if name.startswith("logical_to_stim_converter") or name.startswith("tests"):
        raise AssertionError("Golden reference crossed independence boundary: " + name)
    return original(name, *args, **kwargs)
builtins.__import__ = independent
from validation.golden_memory.reference_same_schedule import build_reference
for d in (3, 5):
    for basis in "XZ":
        build_reference(d, basis).detector_error_model()
"""
    subprocess.run([sys.executable, "-c", script], check=True)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in FIXTURES.iterdir()}
    for d, b in CASES:
        verify_fixture(d, b)
    assert before == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in FIXTURES.iterdir()
    }
    for p in FIXTURES.iterdir():
        (tmp_path / p.name).write_bytes(p.read_bytes())
    with (tmp_path / "d3_z.stim").open("a") as out:
        out.write("\nX 0\n")
    with pytest.raises(Mismatch, match="Fixture checksum mismatch"):
        verify_fixture(3, "Z", directory=tmp_path)


def test_debug_CLI_and_explicit_fixture_maintenance(tmp_path):
    output = tmp_path / "report.json"
    command = [
        sys.executable,
        "-m",
        "validation.golden_memory.run",
        "--distance",
        "3",
        "--basis",
        "Z",
        "--level",
        "all",
        "--workers",
        "1",
        "--output",
        str(output),
    ]
    before = (FIXTURES / "manifest.json").read_bytes()
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert report == json.loads(output.read_text())
    assert [r["level"] for r in report["reports"]] == ["A", "B", "C1", "C2"]
    assert (FIXTURES / "manifest.json").read_bytes() == before
    # Maintenance is exercised in a private directory; no test writes repository fixtures.
    from validation.golden_memory.run import regenerate_fixtures

    regenerate_fixtures(tmp_path / "fixtures")
    assert verify_fixture(5, "X", directory=tmp_path / "fixtures") == build_reference(5, "X")
    assert Path(json.loads(before)["generation_source"]).name == "reference_same_schedule.py"


def test_B_rejects_extra_noncommon_noise():
    dut = compile_dut(3, "Z", ReferenceNoise(reset=0.01, measurement=0.01)).circuit
    common_noise_equivalence(dut, 3, "Z")
    bad = dut.copy()
    bad.append("DEPOLARIZE1", [0], 0.01)
    with pytest.raises(Mismatch, match="unsupported noise channel"):
        common_noise_equivalence(bad, 3, "Z")


def test_detector_metadata_anchor_is_independently_checked():
    dut = compile_dut(3, "Z")
    ideal_semantic_equivalence(dut, 3, "Z")
    first = dut.detectors[0]
    other = next(
        info
        for info in dut.detectors
        if info.basis == first.basis and info.check_id != first.check_id
    )
    corrupt = replace(first, check_id=other.check_id, physical_support=other.physical_support)
    bad = replace(dut, detectors=(corrupt, *dut.detectors[1:]))
    with pytest.raises(Mismatch, match="detector metadata mismatch"):
        ideal_semantic_equivalence(bad, 3, "Z")
