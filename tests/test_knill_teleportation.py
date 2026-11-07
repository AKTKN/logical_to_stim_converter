"""State recovery, entanglement, continued computation, and relocation physics."""

from dataclasses import replace

import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)
from tests.helpers.knill_physics import (
    corrected_expectation,
    explicit_reference,
    make_compiler,
    pauli,
    simulate,
)
from tests.helpers.preparation_matching import preparation_corrections


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
def test_knill_four_input_states(d, basis, bit):
    compiler = make_compiler(d)
    program = [LogicalInit("D", basis, 1)]
    if bit:
        program.append(LogicalPauli("D", "Z" if basis == "X" else "X"))
    program.append(KnillEC("D", "A", "B"))
    result = compiler.compile(program, allow_open_outputs=True)
    assert result.logical_to_block == result.open_logical_outputs == {"D": "physical_B"}
    assert result.block_status == {"physical_D": "measured", "physical_A": "measured",
                                   "physical_B": "active"}
    assert len(result.relocation_history) == 1
    relocation, = result.relocation_history
    assert (relocation.logical_id, relocation.source_block_id, relocation.output_block_id) == (
        "D", "physical_D", "physical_B")
    assert result.ideal_circuit.num_observables == 0
    assert not any(i.name == "MPP" for i in result.ideal_circuit)
    # The only data measurements are exactly the requested D/A Bell readouts.
    assert {m.key.block_id for m in result.measurements if m.key.kind == "readout"} == {
        "physical_D", "physical_A"}
    assert [p.rounds for p in result.preparations] == [1, d, d]
    raw, sims = simulate(result, range(64))
    corrections = preparation_corrections(result, raw)
    evaluated = result.evaluate_frames(raw, corrections)
    bell, = evaluated.bell_measurements.values()
    branches = set(zip(bell.corrected_x, bell.corrected_z, strict=True))
    assert len(branches) == 4
    for shot, sim in enumerate(sims):
        assert corrected_expectation(sim, result, pauli(result, "D", basis),
                                     [evaluated.final_frames["D"][shot]]) == (-1)**bit
    for shot in (0, 1, 7):
        ref = explicit_reference(result, evaluated.corrected_measurements[shot],
                                 {k: v[shot:shot+1] for k, v in corrections.items()})
        assert ref.peek_observable_expectation(pauli(result, "D", basis)) == (-1)**bit
    with pytest.raises(ValueError, match="unresolved"):
        result.interpreted_measurements(raw)
    # Recompile the open artifact with SE and a real final readout.
    closed = result.append([SyndromeExtraction("D", 1), LogicalMeasure("D", basis)])
    raw = closed.ideal_circuit.compile_sampler(seed=83).sample(64)
    resolved = preparation_corrections(closed, raw)
    assert (closed.interpreted_measurements(raw, preparation_corrections=resolved) == bit).all()
    assert not closed.open_logical_outputs


@pytest.mark.parametrize("d", [3, 5])
def test_teleportation_preserves_encoded_reference_entanglement(d):
    result = make_compiler(d, "RDAB").compile([
        BellStatePrep("R", "D"), KnillEC("D", "A", "B")], allow_open_outputs=True)
    raw, sims = simulate(result, range(80, 96))
    corrections = preparation_corrections(result, raw)
    evaluated = result.evaluate_frames(raw, corrections)
    for shot, sim in enumerate(sims):
        frames = [evaluated.final_frames[q][shot] for q in ("R", "D")]
        for basis in "XZ":
            joint = pauli(result, "R", basis) * pauli(result, "D", basis)
            assert corrected_expectation(sim, result, joint, frames) == 1
            assert sim.peek_observable_expectation(pauli(result, "D", basis)) == 0
    ref = explicit_reference(result, evaluated.corrected_measurements[0],
                             {k: v[:1] for k, v in corrections.items()})
    for basis in "XZ":
        assert ref.peek_observable_expectation(
            pauli(result, "R", basis) * pauli(result, "D", basis)) == 1


@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("mode", ["physical", "frame"])
def test_h_paulis_and_unmeasured_spectator_after_teleportation(basis, mode):
    result = make_compiler(3, "DABC").compile([
        [LogicalInit("D", basis, 1), LogicalInit("C", "Z", 1)],
        LogicalPauli("D", "Z" if basis == "X" else "X", mode="frame"),
        TransversalH("D"), KnillEC("D", "A", "B"),
        [SyndromeExtraction("D", 2), LogicalPauli("C", "X", mode=mode)],
        TransversalH("D"), LogicalPauli("D", "Y", mode=mode),
        LogicalMeasure("D", basis), LogicalMeasure("C", "Z")])
    raw = result.ideal_circuit.compile_sampler(seed=41).sample(100)
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    assert (evaluated.logical_outputs == [1, 0]).all()  # sorted C,D
    assert result.readouts[-2].block_id == "physical_B"
    assert any(f.operation_type == "TransversalH" and f.block_ids == ("physical_B",)
               for f in result.fragments)


@pytest.mark.parametrize("orientations", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_existing_bell_resource_in_all_code_frames(orientations):
    a, b = orientations
    program = [LogicalInit("D", "Z", 1), TransversalH("D"),
               [LogicalInit("A", "Z" if a else "X", 3),
                LogicalInit("B", "X" if b else "Z", 3)]]
    for q, orientation in zip("AB", orientations, strict=True):
        if orientation:
            program.append(TransversalH(q))
    program += [TransversalCNOT("A", "B"),
                KnillEC("D", "A", "B", prepare_resource=False),
                TransversalH("D"), LogicalMeasure("D", "Z")]
    result = make_compiler().compile(program)
    assert len(result.preparations) == 3
    raw = result.ideal_circuit.compile_sampler(seed=52).sample(100)
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    assert not evaluated.logical_outputs.any()


def test_missing_byproduct_and_wrong_output_orientation_break_physics():
    result = make_compiler().compile([LogicalInit("D", "X", 1), KnillEC("D", "A", "B")],
                                     allow_open_outputs=True)
    raw, sims = simulate(result, range(50))
    corrections = preparation_corrections(result, raw)
    bad = replace(result, _evaluation_steps=tuple(
        step for step in result._evaluation_steps if step[0] != "teleport"))
    evaluated = bad.evaluate_frames(raw, corrections)
    recovered = [corrected_expectation(sim, result, pauli(result, "D", "X"),
                 [evaluated.final_frames["D"][shot]]) for shot, sim in enumerate(sims)]
    assert set(recovered) == {-1, 1}
    good = result.evaluate_frames(raw, corrections)
    wrong = pauli(result, "D", "X", orientation=1)
    assert any(corrected_expectation(sim, result, wrong, [good.final_frames["D"][shot]]) != 1
               for shot, sim in enumerate(sims))


def test_random_readout_and_open_continuation_without_knill():
    result = make_compiler(3, "AB").compile([
        BellStatePrep("A", "B"), LogicalMeasure("A", "X", mode="random")],
        allow_open_outputs=True)
    assert result.open_logical_outputs == {"B": "physical_B"}
    assert len(result.readouts) == 1 and not result.observables
    raw = result.ideal_circuit.compile_sampler(seed=91).sample(50)
    parity = result.readouts[0].logical_parity.evaluate(raw, {m.key: m.index
                                                          for m in result.measurements})
    assert set(parity) == {False, True}
    # A further random destructive readout needs no deterministic observable.
    closed = result.append([TransversalH("B"), LogicalMeasure("B", "Z", mode="random")])
    assert not closed.open_logical_outputs and not closed.observables
    closed.ideal_circuit.detector_error_model()


def test_existing_resource_validation_and_retired_identity_rejection():
    compiler = make_compiler()
    with pytest.raises(ValueError, match="Bell"):
        compiler.compile([LogicalInit(("D", "A", "B"), "Z", 1),
                          KnillEC("D", "A", "B", prepare_resource=False)],
                         allow_open_outputs=True)
    with pytest.raises(ValueError, match="Unknown"):
        compiler.compile([LogicalInit("D", "Z", 1), KnillEC("D", "A", "B"),
                          SyndromeExtraction("B", 1)], allow_open_outputs=True)


def test_cnot_after_relocation_and_parallel_spectator_computation():
    result = make_compiler(3, "DABC").compile([
        [LogicalInit("D", "X", 1), LogicalInit("C", "Z", 1)],
        [KnillEC("D", "A", "B"), TransversalH("C")],
        TransversalCNOT("D", "C"), TransversalCNOT("D", "C"),
        [LogicalMeasure("D", "X"), LogicalMeasure("C", "X")]])
    raw = result.ideal_circuit.compile_sampler(seed=32).sample(100)
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    assert not evaluated.logical_outputs.any()
    post = [f for f in result.fragments if f.operation_type == "TransversalCNOT"
            and not f.composite_ids]
    assert all(f.block_ids == ("physical_B", "physical_C") for f in post)


def test_parallel_independent_composites_and_location_histories():
    result = make_compiler(3, "DABEFC").compile([
        [LogicalInit("D", "Z", 1), LogicalInit("E", "X", 1)],
        [KnillEC("D", "A", "B"), KnillEC("E", "F", "C")],
        [LogicalMeasure("D", "Z"), LogicalMeasure("E", "X")]])
    assert result.logical_to_block == {"D": "physical_B", "E": "physical_C"}
    assert len(result.relocation_history) == len(result.bell_measurements) == 2
    raw = result.ideal_circuit.compile_sampler(seed=77).sample(100)
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    assert not evaluated.logical_outputs.any()


def test_random_partial_readout_parallel_to_h_preserves_conditional_flow():
    result = make_compiler(3, "AB").compile([BellStatePrep("A", "B"),
        [LogicalMeasure("A", "X", mode="random"), TransversalH("B")]],
        allow_open_outputs=True)
    raw, sims = simulate(result, range(16))
    evaluated = result.evaluate_frames(raw, preparation_corrections(result, raw))
    readout = evaluated.readout_values[result.readouts[0].module_id]
    for s, sim in enumerate(sims):
        assert corrected_expectation(sim, result, pauli(result, "B", "Z"),
                                     [evaluated.final_frames["B"][s]]) == (-1)**int(readout[s])
