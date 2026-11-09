"""Physical and statistical controls for the research-only ordinary fault census."""

import csv
import gzip
from dataclasses import replace
from types import SimpleNamespace

import pytest
import stim

from logical_to_stim_converter import BlockUseId
from logical_to_stim_converter.core.compiler_context import TimeLayer
from validation.code_capacity import fit_points, wilson
from validation.ordinary_circuit import (
    UnsupportedMatchingModel,
    categorical_distribution,
    main,
    matching_for_dem,
    parallel_census,
    run_memory_point,
)
from validation.ordinary_faults import (
    Case,
    atoms_from_locations,
    audit_dem_marginal,
    audit_first_order,
    audit_pair_subset,
    audit_schedule,
    audit_signed_reference,
    build_case,
    dem_events,
    scan_noisy,
    simulate_atoms,
)


def hand_circuit():
    ideal = stim.Circuit("""
        R 0
        TICK
        H 0
        R 1
        TICK
        CX 0 1
        TICK
        M 0 1
        DETECTOR rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-2]
    """)
    noisy = stim.Circuit("""
        R 0
        X_ERROR(0.1) 0
        DEPOLARIZE1(0.05) 1
        TICK
        H 0
        DEPOLARIZE1(0.2) 0
        R 1
        X_ERROR(0.1) 1
        TICK
        CX 0 1
        DEPOLARIZE2(0.3) 0 1
        TICK
        M(0.4) 0 1
        DETECTOR rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-2]
    """)
    layers = tuple(TimeLayer(i, ("P0",), {}, frozenset(), (BlockUseId("P0"),)) for i in range(4))
    return SimpleNamespace(
        ideal_circuit=ideal,
        noisy_circuit=noisy,
        circuit=noisy,
        physical_qubit_map={("P0", "D1"): 0, ("P0", "D2"): 1},
        time_layers=layers,
    )


def test_hand_authored_batched_table_and_exclusive_probabilities():
    compiled = hand_circuit()
    locations = scan_noisy(compiled)
    assert len(locations) == 7
    assert [x.channel for x in locations] == [
        "X_ERROR",
        "DEPOLARIZE1",
        "DEPOLARIZE1",
        "X_ERROR",
        "DEPOLARIZE2",
        "RESULT_FLIP",
        "RESULT_FLIP",
    ]
    assert [x.target_position for x in locations[-2:]] == [0, 1]
    atoms = atoms_from_locations(locations)
    assert len(atoms) == 1 + 3 + 3 + 1 + 15 + 1 + 1
    pair = [a for a in atoms if a.location_id == 4]
    assert len({a.alternative for a in pair}) == 15
    assert all(a.probability == pytest.approx(0.3 / 15) for a in pair)
    assert locations[4].identity_probability == pytest.approx(0.7)
    assert sum(a.probability for a in pair) == pytest.approx(0.3)
    assert len({a.location_id for a in pair}) == 1
    assert all(a.record_index is not None for a in atoms[-2:])


def test_measurement_flip_is_before_result_not_after_measurement():
    ideal = stim.Circuit("R 0 1\nM 0 1\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-2]")
    noisy = stim.Circuit("R 0 1\nM(0.1) 0 1\nDETECTOR rec[-1]\nOBSERVABLE_INCLUDE(0) rec[-2]")
    layers = (TimeLayer(0, ("P0",), {}, frozenset(), (BlockUseId("P0"),)),)
    compiled = SimpleNamespace(
        ideal_circuit=ideal,
        noisy_circuit=noisy,
        circuit=noisy,
        physical_qubit_map={("P0", "D1"): 0, ("P0", "D2"): 1},
        time_layers=layers,
    )
    atom = atoms_from_locations(scan_noisy(compiled))[-1]
    observed = simulate_atoms(compiled, (atom,))[atom.atom_id]
    assert observed == (1, 0)
    late = stim.Circuit("R 0\nM 0\nX_ERROR(1) 0\nDETECTOR rec[-1]")
    early = stim.Circuit("R 0\nM(1) 0\nDETECTOR rec[-1]")
    assert not late.compile_detector_sampler(seed=5).sample(8).any()
    assert early.compile_detector_sampler(seed=5).sample(8).all()


def test_complete_d3_and_d5_physical_marginal_and_first_order():
    for case in (
        Case(3, "Z", 1, (0.001, 0.002, 0.003, 0.004, 0.005)),
        Case(3, "X", 3, (0.001,) * 5),
        Case(5, "Z", 1, (0.001,) * 5),
    ):
        compiled, model = build_case(case)
        locations = scan_noisy(compiled)
        assert audit_schedule(compiled, model, locations)["locations"] == len(locations)
        atoms = atoms_from_locations(locations)
        signatures = simulate_atoms(compiled, atoms)
        assert len(signatures) == len(atoms)
        assert (
            audit_dem_marginal(compiled, locations, atoms, signatures)[
                "view_max_fourier_difference"
            ]
            < 1e-10
        )
        assert (
            audit_first_order(case, atoms, signatures)["max_absolute_coefficient_difference"] < 1e-5
        )
        assert audit_signed_reference(compiled)["random_raw_columns"] > 0


def test_h_gate_signed_and_spectator_idling():
    h_case = Case(3, "X", 1, (0.001, 0.002, 0.003, 0.004, 0.005), "h")
    h, model = build_case(h_case)
    locations = scan_noisy(h)
    assert audit_schedule(h, model, locations)["kinds"]["after_1q"] == 9
    assert (
        len(
            [
                a
                for a in atoms_from_locations(locations)
                if locations[a.location_id].kind == "after_1q"
            ]
        )
        == 27
    )
    signed, _ = build_case(Case(3, "Z", 1, (0.001,) * 5, "signed"))
    assert audit_signed_reference(signed)["expected_values"] == [True]
    spectator, model = build_case(Case(3, "Z", 3, (0.001,) * 5, "spectator"))
    locations = scan_noisy(spectator)
    assert audit_schedule(spectator, model, locations)["locations"] == len(locations)
    assert all(location.source_module for location in locations if location.kind == "idle")
    assert {epoch for location in locations for epoch in location.epochs} == {0}
    # P0 retires while P1 continues. No P0 idle atom may appear afterward.
    p0_stop = next(u.time_layer_stop for u in spectator.block_uses if u.use_id.block_id == "P0")
    assert all(
        not (location.kind == "idle" and location.layer >= p0_stop and location.sites[0][0] == "P0")
        for location in locations
    )


def test_mutation_controls_catch_schedule_map_and_sign():
    case = Case(3, "Z", 1, (0.001, 0.002, 0.003, 0.004, 0.005))
    compiled, model = build_case(case)
    noisy = list(compiled.circuit)
    idle_index = next(i for i, gate in enumerate(noisy) if gate.name == "DEPOLARIZE1")
    missing = stim.Circuit()
    for i, gate in enumerate(noisy):
        if i != idle_index:
            missing.append(gate)
    altered = replace(compiled, noisy_circuit=missing)
    with pytest.raises(AssertionError, match="fault location mismatch"):
        audit_schedule(altered, model)
    extra = compiled.circuit.copy()
    extra.append("DEPOLARIZE1", [0], 0.005)
    with pytest.raises(AssertionError, match="fault location mismatch"):
        audit_schedule(replace(compiled, noisy_circuit=extra), model)
    wrong_reset = stim.Circuit()
    for gate in noisy:
        if gate.name == "X_ERROR" and gate.targets_copy()[0].value == 1:
            targets = gate.targets_copy()
            targets[0] = stim.GateTarget(0)
            wrong_reset.append("X_ERROR", targets, gate.gate_args_copy())
        else:
            wrong_reset.append(gate)
    with pytest.raises(AssertionError, match="fault location mismatch"):
        audit_schedule(replace(compiled, noisy_circuit=wrong_reset), model)
    wrong_cx = stim.Circuit()
    changed = False
    for gate in noisy:
        if gate.name == "CX" and not changed:
            targets = gate.targets_copy()
            targets[0], targets[1] = targets[1], targets[0]
            wrong_cx.append("CX", targets, tag=gate.tag)
            changed = True
        else:
            wrong_cx.append(gate)
    with pytest.raises(AssertionError, match="ideal physical instructions"):
        scan_noisy(replace(compiled, noisy_circuit=wrong_cx))
    cx_positions = [i for i, gate in enumerate(noisy) if gate.name == "CX"]
    wrong_order = stim.Circuit()
    for i, gate in enumerate(noisy):
        if i == cx_positions[0]:
            wrong_order.append("CX", noisy[cx_positions[1]].targets_copy(), tag=gate.tag)
        elif i == cx_positions[1]:
            wrong_order.append("CX", noisy[cx_positions[0]].targets_copy(), tag=gate.tag)
        else:
            wrong_order.append(gate)
    with pytest.raises(AssertionError, match="ideal physical instructions"):
        scan_noisy(replace(compiled, noisy_circuit=wrong_order))
    wrong_readout = stim.Circuit()
    changed = False
    for gate in noisy:
        if gate.name == "M" and not changed:
            targets = gate.targets_copy()
            targets[0], targets[1] = targets[1], targets[0]
            wrong_readout.append("M", targets, gate.gate_args_copy(), tag=gate.tag)
            changed = True
        else:
            wrong_readout.append(gate)
    with pytest.raises(AssertionError, match="ideal physical instructions"):
        scan_noisy(replace(compiled, noisy_circuit=wrong_readout))
    wrong_map = dict(compiled.physical_qubit_map)
    wrong_map["P0", "D1"], wrong_map["P0", "D2"] = (wrong_map["P0", "D2"], wrong_map["P0", "D1"])
    with pytest.raises(AssertionError, match="physical qubit map"):
        audit_schedule(replace(compiled, physical_qubit_map=wrong_map), model)
    obs = replace(compiled.observables[0], expected_value=True)
    with pytest.raises(AssertionError, match="signed noiseless"):
        audit_signed_reference(replace(compiled, observables=(obs,)))


def test_dem_components_hyperedge_guard_and_aliased_signatures():
    decomposed = stim.DetectorErrorModel("error(0.1) D0 D1 ^ D2 L0")
    (event,) = dem_events(decomposed)
    assert event[1:3] == (0b111, 1) and len(event[3]) == 2
    matching_for_dem(decomposed)
    with pytest.raises(UnsupportedMatchingModel, match="hyperedge"):
        matching_for_dem(stim.DetectorErrorModel("error(0.1) D0 D1 D2 L0"))
    compiled, _ = build_case(Case(3, "Z", 1, (0.001,) * 5))
    atoms = atoms_from_locations(scan_noisy(compiled))
    signatures = simulate_atoms(compiled, atoms)
    assert len({signatures[a.atom_id][:2] for a in atoms}) < len(atoms)


def test_parallel_census_memory_seed_and_categorical_model():
    case = Case(3, "Z", 1, (0.001, 0.002, 0.003, 0.004, 0.005))
    compiled, locations, atoms, one, _ = parallel_census(case, workers=1, batch_size=128)
    _, _, _, two, _ = parallel_census(case, workers=2, batch_size=128)
    assert one == two
    pair_audit = audit_pair_subset(compiled, atoms, one, count=32, seed=902)
    assert pair_audit["sampled_cross_location_pairs"] == 32
    assert not pair_audit["complete"]
    with pytest.raises(AssertionError, match="physical fault pair disagrees"):
        audit_pair_subset(compiled, atoms, dict.fromkeys(one, (0, 0)), count=32, seed=902)
    distribution = categorical_distribution(
        locations, atoms, one, (0, 1, 2), (0,), shots=20000, seed=902
    )
    assert sum(distribution["counts"]) == 20000
    assert distribution["max_binomial_z_when_expected_ge_5"] < 5
    point = Case(3, "Z", 1, (0.008,) * 5)
    a = run_memory_point(
        point, workers=1, batch_size=128, seed=91, max_shots=512, target_failures=0, max_seconds=30
    )
    b = run_memory_point(
        point, workers=2, batch_size=128, seed=91, max_shots=512, target_failures=0, max_seconds=30
    )
    assert (a["shots"], a["failures"]) == (b["shots"], b["failures"])
    assert a["shots"] == 512


def test_zero_noise_invalid_settings_and_quick_cli(tmp_path):
    zero = Case(3, "Z", 1, (0,) * 5)
    compiled, model = build_case(zero)
    assert compiled.circuit == compiled.ideal_circuit
    assert scan_noisy(compiled) == ()
    assert audit_schedule(compiled, model)["locations"] == 0
    with pytest.raises(ValueError):
        Case(3, "Z", 0, (0.001,) * 5)
    with pytest.raises(ValueError):
        Case(3, "Z", 1, (True,) * 5)
    with pytest.raises(ValueError):
        run_memory_point(
            Case(3, "Z", 1, (0.001,) * 5),
            workers=1,
            batch_size=0,
            seed=1,
            max_shots=10,
            target_failures=0,
            max_seconds=2,
        )
    assert wilson(0, 10)[0] == 0 < wilson(0, 10)[1]
    synthetic = [
        dict(q=q, shots=100000, failures=round(100000 * 2 * q**2)) for q in (0.02, 0.04, 0.06, 0.08)
    ]
    assert abs(fit_points(synthetic)["beta"] - 2) < 0.2
    assert (
        main(
            [
                "--quick",
                "--workers",
                "2",
                "--batch-size",
                "128",
                "--max-shots",
                "512",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (tmp_path / "report.json").exists()
    table = next(tmp_path.glob("atoms_*.csv.gz"))
    with gzip.open(table, "rt", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 556
    assert all(row["source_fingerprint"] for row in rows)
