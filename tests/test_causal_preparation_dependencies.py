"""Causal ancestry is independent of chronology, registration, and frame values."""

from dataclasses import replace

import numpy as np
import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    CircuitCompiler,
    KnillEC,
    LogicalInit,
    LogicalPauli,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from tests.helpers.knill_physics import corrected_expectation, make_compiler, pauli, simulate
from tests.helpers.preparation_matching import preparation_corrections


def sources(result, dependencies):
    by_module = {p.module_id: p for p in result.preparations}
    return tuple(k for p in dependencies for k in by_module[p].unresolved_frame.source_syndromes)


def modules(result, logicals):
    return tuple(p.module_id for p in result.preparations if p.logical_id in logicals)


@pytest.fixture(scope="module")
def spectator_result():
    return make_compiler(3, "CDAB").compile([
        LogicalInit("C", "Z", 1), LogicalInit("D", "X", 1),
        TransversalH("D"), LogicalPauli("D", "X", mode="frame"),
        KnillEC("D", "A", "B"), SyndromeExtraction("D", 1)], allow_open_outputs=True)


def test_spectator_is_excluded_from_bell_and_open_frame_sources(spectator_result):
    result = spectator_result
    bell, = result.bell_measurements
    expected = modules(result, "DAB")
    assert bell.preparation_dependencies == result.preparation_dependencies["D"] == expected
    assert result.preparation_dependencies["C"] == modules(result, "C")
    assert set(result.preparation_dependencies) == {"C", "D"}  # retired identities are absent
    assert bell.physical_output_frame.source_syndromes == sources(result, expected)
    raw = result.ideal_circuit.compile_sampler(seed=90).sample(40)
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    for q in "CD":
        for frame in evaluated.final_frames[q]:
            assert frame.source_syndromes == sources(result, result.preparation_dependencies[q])
    assert not any(k.block_id == "physical_C" for k in bell.physical_output_frame.source_syndromes)
    result.validate_metadata()


def test_parallel_gadgets_and_registration_order_have_disjoint_ancestry():
    compiler = make_compiler(3, "DABEFC")
    program = [[LogicalInit("D", "Z", 1), LogicalInit("E", "X", 1)],
               [KnillEC("D", "A", "B"), KnillEC("E", "F", "C")]]
    first = compiler.compile(program, allow_open_outputs=True)
    second = CircuitCompiler(tuple(reversed(compiler.blocks)),
                             logical_to_block=compiler.logical_to_block).compile(
                                 program, allow_open_outputs=True)
    assert first.ideal_circuit == second.ideal_circuit
    assert first.ancestry_events == second.ancestry_events
    assert first.measurements == second.measurements and first.detectors == second.detectors
    raw = first.ideal_circuit.compile_sampler(seed=72).sample(16)
    evaluated = first.evaluate_frames(raw, preparation_corrections(first, raw))
    for result in (first, second):
        d, e = result.bell_measurements
        assert set(d.preparation_dependencies) == set(modules(result, "DAB"))
        assert set(e.preparation_dependencies) == set(modules(result, "EFC"))
        assert not set(d.preparation_dependencies) & set(e.preparation_dependencies)
        assert not set(d.physical_output_frame.source_syndromes) & set(
            e.physical_output_frame.source_syndromes)
        for bell in (d, e):
            assert evaluated.final_frames[bell.logical_id][0].source_syndromes == sources(
                result, bell.preparation_dependencies)


@pytest.mark.parametrize("d", [3, 5])
def test_real_interaction_preserves_reference_history_and_physical_entanglement(d):
    result = make_compiler(d, "RDABC").compile([
        LogicalInit("C", "Z", 1), BellStatePrep("R", "D"),
        SyndromeExtraction(("R", "D"), 1), KnillEC("D", "A", "B")],
        allow_open_outputs=True)
    bell, = result.bell_measurements
    assert set(bell.preparation_dependencies) == set(modules(result, "RDAB"))
    assert set(result.preparation_dependencies["R"]) == set(modules(result, "RD"))
    raw, sims = simulate(result, range(8))
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    for shot, sim in enumerate(sims):
        frames = [evaluated.final_frames[q][shot] for q in "RD"]
        for axis in "XZ":
            assert corrected_expectation(sim, result,
                                         pauli(result, "R", axis) * pauli(result, "D", axis),
                                         frames) == 1


def test_existing_resource_extra_se_and_repeated_relocation():
    result = make_compiler(3, "DABCEF").compile([
        LogicalInit("D", "X", 1), BellStatePrep("A", "B"),
        SyndromeExtraction(("A", "B"), 1),
        KnillEC("D", "A", "B", prepare_resource=False),
        LogicalInit("F", "Z", 1), KnillEC("D", "C", "E")], allow_open_outputs=True)
    first, second = result.bell_measurements
    assert set(first.preparation_dependencies) == set(modules(result, "DAB"))
    assert set(second.preparation_dependencies) == set(modules(result, "DABCE"))
    assert result.open_logical_outputs == {"D": "physical_E", "F": "physical_F"}
    raw, sims = simulate(result, range(8))
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    for shot, sim in enumerate(sims):
        assert corrected_expectation(sim, result, pauli(result, "D", "X"),
                                     [evaluated.final_frames["D"][shot]]) == 1
    assert evaluated.final_frames["D"][0].source_syndromes == sources(
        result, second.preparation_dependencies)


def test_cnot_joins_only_actual_operand_histories():
    result = make_compiler(3, "DABC").compile([
        LogicalInit(("D", "C"), "Z", 1), TransversalCNOT("D", "C"),
        KnillEC("D", "A", "B")], allow_open_outputs=True)
    assert set(result.preparation_dependencies["C"]) == set(modules(result, "DC"))
    assert set(result.preparation_dependencies["D"]) == set(modules(result, "DCAB"))


@pytest.mark.parametrize("corruption", ["edge", "dependencies", "bell", "final"])
def test_corrupt_ancestry_is_rejected(spectator_result, corruption):
    result = spectator_result
    if corruption in ("edge", "dependencies"):
        events = list(result.ancestry_events)
        i = next(i for i, e in enumerate(events) if e.operation_type == "TransversalCNOT")
        change = ({"input_block_ids": ("physical_C", "physical_B")} if corruption == "edge"
                  else {"preparation_dependencies": modules(result, "C")})
        events[i] = replace(events[i], **change)
        bad = replace(result, ancestry_events=tuple(events))
    elif corruption == "bell":
        bell, = result.bell_measurements
        bad = replace(result, bell_measurements=(replace(
            bell, preparation_dependencies=bell.preparation_dependencies + modules(result, "C")),))
    else:
        bad = replace(result, preparation_dependencies={"D": modules(result, "CDAB")})
    with pytest.raises(ValueError, match="[Aa]ncestry"):
        bad.validate_metadata()


def test_spectator_correction_value_does_not_change_teleported_frame(spectator_result):
    result = spectator_result
    raw = result.ideal_circuit.compile_sampler(seed=91).sample(10)
    corrections = preparation_corrections(result, raw)
    good = result.evaluate_frames(raw, corrections)
    p = next(p for p in result.preparations if p.logical_id == "C")
    # An arbitrary noisy hypothesis on the spectator must stay on that block.
    corrections[p.module_id] = p.resolve(np.ones(9), np.zeros(9))
    changed = result.evaluate_frames(raw, corrections, validation="hypothesis")
    assert changed.final_frames["D"] == good.final_frames["D"]
    identity = result.bell_measurements[0].composite_id
    assert np.array_equal(changed.bell_measurements[identity].corrected_x,
                          good.bell_measurements[identity].corrected_x)
