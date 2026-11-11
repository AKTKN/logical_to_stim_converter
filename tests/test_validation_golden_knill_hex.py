"""Actual frozen pinned Hex, with independent signed/gauge/channel oracles."""

import builtins
import re
from copy import deepcopy

import numpy as np
import pytest
import stim

from validation.golden_knill import hex_semantics
from validation.golden_knill.fixtures import verify_hex_fixture
from validation.golden_knill.hex_adapter import bundle_from_dict, bundle_to_dict
from validation.golden_knill.hex_semantics import (
    check_full_hex_constraints,
    check_geometry,
    check_hex_semantics,
    check_preparation,
)
from validation.golden_memory.normalize import Mismatch


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
def test_actual_hex_signed_instruments_gauges_and_identity(distance, basis, bit):
    bundle = verify_hex_fixture(distance, basis, bit)
    result = check_hex_semantics(bundle)
    assert all(result[level]["passed"] for level in ("A0", "A1", "A2", "A3"))
    assert result["A1"]["surface_code"] is True
    full = result["A1"]["full_record_constraints"]
    m = distance**2 - 1
    assert full["open"]["complete_signed_constraint_rank"] == 2 * distance * m
    assert full["closed"]["complete_signed_constraint_rank"] == 2 * distance * m + m // 2 + 1
    assert full["open"]["free_record_bits"] == 2 * distance**2
    assert full["closed"]["free_record_bits"] == (5 * distance**2 - 1) // 2
    for output in ("open", "closed"):
        assert full[output]["native_detector_annotations"] == (2 * distance - 1) * m
        assert full[output]["native_detector_rank"] == (2 * distance - 1) * m
        assert full[output]["native_annotations_incomplete"]
        assert full[output]["native_observable_annotations"] == 0
    assert bool(full["closed"]["signed_basis_rows"]) == bool(bit)
    assert full["physical_counts"]["allocated_sites"] == 3 * (2 * distance**2 - 1)
    assert full["physical_counts"]["addressed_sites"] == 5 * distance**2 - 2
    assert result["A2"]["nonzero_preparation_trials"] > 0
    assert result["A2"]["exact_signed_resource_flows"] == 2 * (distance**2 - 1) + 2
    assert result["A3"]["two_axis_signed_channel_flows"] == 2
    assert result["A3"]["input_preparation_removed_for_channel_proof"]
    assert result["A3"]["exact_independent_Bell_bits"] == 2
    assert result["A3"]["native_correction_placement_validated"]
    assert result["A3"]["native_Bell_instruction_count"] == len(bundle.sections["bell_measure"])
    assert set(result["A3"]["observed_corrected_Bell_branches"]) == {"00", "01", "10", "11"}
    assert result["A3"]["open_state_trials"] == result["A3"]["closed_readout_trials"] == 64


def test_hex_fixture_load_and_oracle_need_no_upstream_or_decoder_import(monkeypatch):
    original = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.split(".")[0] in {"hex_qec", "ldpc", "stimbposd"}:
            raise AssertionError(f"Normal golden validation imported {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    bundle = verify_hex_fixture(3, "X")
    restored = bundle_from_dict(bundle_to_dict(bundle))
    assert restored.closed_circuit == bundle.closed_circuit
    assert restored.open_circuit == bundle.open_circuit
    assert check_hex_semantics(restored)["A3"]["passed"]


@pytest.mark.parametrize(
    "mutation",
    [
        "resource_direction",
        "bell_direction",
        "bell_basis",
        "byproduct_order",
        "byproduct_placement",
        "signed_input",
    ],
)
def test_hex_conditional_channel_rejects_physical_and_frame_mutations(mutation):
    bundle = deepcopy(verify_hex_fixture(3, "X", 0))
    baseline = check_hex_semantics(bundle)
    assert all(baseline[level]["passed"] for level in ("A0", "A1", "A2", "A3"))
    diagnostics = {
        "resource_direction": (
            "Hex full closed signed record constraints differ: actual_rank=53, expected_rank=53"
        ),
        "bell_direction": (
            "Hex full open signed record constraints differ: actual_rank=49, expected_rank=48"
        ),
        "bell_basis": "Bell D readout basis differs",
        "byproduct_order": "Hex correction order must be Z^(m_X), X^(m_Z)",
        "byproduct_placement": (
            "Hex correction placement must follow the complete native Bell module: "
            "expected_instruction_cut=23, actual=22"
        ),
        "signed_input": (
            "Hex full closed signed record constraints differ: actual_rank=53, expected_rank=53"
        ),
    }
    if mutation in ("resource_direction", "bell_direction"):
        name = "entangle" if mutation == "resource_direction" else "bell_measure"
        changed = stim.Circuit()
        for inst in bundle.sections[name]:
            if inst.name == "CX":
                targets = inst.targets_copy()
                targets = [
                    target
                    for i in range(0, len(targets), 2)
                    for target in (targets[i + 1], targets[i])
                ]
                changed.append("CX", targets)
            else:
                changed.append(inst)
        bundle.sections[name] = changed
    elif mutation == "bell_basis":
        changed = stim.Circuit()
        for inst in bundle.sections["bell_measure"]:
            changed.append(
                "MR" if inst.name == "MRX" else inst.name,
                inst.targets_copy(),
                inst.gate_args_copy(),
            )
        bundle.sections["bell_measure"] = changed
    elif mutation == "byproduct_order":
        bundle.correction_array.reverse()
    elif mutation == "byproduct_placement":
        text, placement = bundle.correction_array[0]
        bundle.correction_array[0] = (text, placement - 1)
    else:
        # A real physical logical sign error must be seen in the corrected state.
        bundle.sections["input"].append("Z", bundle.blocks["D"]["data_qubits"])
    with pytest.raises(Mismatch, match=re.escape(diagnostics[mutation])):
        check_hex_semantics(bundle)


@pytest.mark.parametrize("mutation", ["check_support", "logical_representative"])
def test_hex_geometry_rejects_altered_matrix_sources(mutation):
    bundle = deepcopy(verify_hex_fixture(3, "X"))
    assert check_geometry(bundle)["passed"]
    key = "X" if mutation == "check_support" else "LX"
    bundle.matrices[key][0, 0] ^= 1
    diagnostic = (
        "A0 Hex checks anticommute"
        if mutation == "check_support"
        else "A0 logical/check commutation"
    )
    with pytest.raises(Mismatch, match=re.escape(diagnostic)):
        check_geometry(bundle)


def test_hex_rejects_removed_physical_gauge_recovery(monkeypatch):
    bundle = verify_hex_fixture(3, "Z")
    baseline = check_hex_semantics(bundle)
    assert all(baseline[level]["passed"] for level in ("A0", "A1", "A2", "A3"))
    monkeypatch.setattr(
        hex_semantics,
        "recovery_map",
        lambda matrices, basis: [np.zeros(9, dtype=np.uint8) for _ in matrices[basis]],
    )
    diagnostic = "Hex full open signed record constraints differ: actual_rank=48, expected_rank=48"
    with pytest.raises(Mismatch, match=re.escape(diagnostic)):
        check_hex_semantics(bundle)


@pytest.mark.parametrize("mutation", ["missing_CX", "reversed_CX"])
def test_hex_signed_round_instrument_rejects_interaction_faults(mutation):
    bundle = verify_hex_fixture(3, "X")
    baseline = check_preparation(
        bundle.sections["prep_A"], bundle.matrices, bundle.data_supports["A"], "Z", 3, "Hex A"
    )
    assert baseline["rounds"] == 3 and baseline["signed_flows"] == 78
    changed, done = stim.Circuit(), False
    for inst in bundle.sections["prep_A"]:
        if inst.name == "CX" and not done:
            targets = inst.targets_copy()
            if mutation == "missing_CX":
                targets = targets[2:]
            else:
                targets[:2] = targets[1::-1]
            if targets:
                changed.append("CX", targets)
            done = True
        else:
            changed.append(inst)
    diagnostic = (
        "Hex A round 1 signed X check 0 instrument failed"
        if mutation == "missing_CX"
        else "Check ancilla basis changed"
    )
    with pytest.raises(Mismatch, match=re.escape(diagnostic)):
        check_preparation(changed, bundle.matrices, bundle.data_supports["A"], "Z", 3, "Hex A")


def test_hex_native_detector_requires_valid_signed_flow():
    bundle = verify_hex_fixture(3, "X")
    baseline = check_full_hex_constraints(bundle)
    assert baseline["open"]["complete_signed_constraint_rank"] == 48
    assert baseline["open"]["native_detector_rank"] == 40
    changed, done = stim.Circuit(), False
    for inst in bundle.sections["prep_A"]:
        if inst.name == "DETECTOR" and not done:
            # A is Z prepared. Its first complementary X outcome is random.
            changed.append("DETECTOR", [stim.target_rec(-8)])
            done = True
        else:
            changed.append(inst)
    bundle.sections["prep_A"] = changed
    diagnostic = "Hex native open declared detector has invalid signed flow: [0]"
    with pytest.raises(Mismatch, match=re.escape(diagnostic)):
        check_full_hex_constraints(bundle)
