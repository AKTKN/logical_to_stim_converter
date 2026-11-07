"""Bell resources verified on physical tableaux across random gauge sectors."""

import numpy as np
import pytest
import stim

from logical_to_stim_converter import BellStatePrep, LogicalInit, TransversalCNOT
from tests.helpers.knill_physics import (
    corrected_expectation,
    explicit_reference,
    make_compiler,
    pauli,
    simulate,
)
from tests.helpers.preparation_matching import preparation_corrections


def physical_circuit(circuit):
    result = stim.Circuit()
    for i in circuit:
        if i.name not in ("QUBIT_COORDS", "SHIFT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE"):
            result.append(i.name, i.targets_copy(), i.gate_args_copy())
    return result


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("rounds", [None, 1])
def test_bell_composite_physical_correlations(d, rounds):
    compiler = make_compiler(d, "AB")
    result = compiler.compile([BellStatePrep("A", "B", rounds)], allow_open_outputs=True)
    r = d if rounds is None else rounds
    primitive = compiler.compile([[LogicalInit("A", "X", r), LogicalInit("B", "Z", r)],
                                  TransversalCNOT("A", "B")], allow_open_outputs=True)
    assert physical_circuit(result.ideal_circuit) == physical_circuit(primitive.ideal_circuit)
    assert [p.rounds for p in result.preparations] == [r, r]
    assert result.orientations == {"A": 0, "B": 0}
    assert len(result.time_layers) == 1 + 6*r + 1
    cnot, = [f for f in result.fragments if f.operation_type == "TransversalCNOT"]
    assert len(cnot.components[0].circuit[0].targets_copy()) == 2*d*d
    assert len(result.composites) == 1
    assert len(result.composites[0].child_operation_ids) == 3
    assert all(f.composite_ids for f in result.fragments)
    assert len({p.stage_id for p in result.preparations}) == 2
    assert result.ideal_circuit.num_observables == 0
    raw, simulators = simulate(result, range(30, 42))
    corrections = preparation_corrections(result, raw)
    evaluated = result.evaluate_frames(raw, corrections)
    xx = pauli(result, "A", "X") * pauli(result, "B", "X")
    zz = pauli(result, "A", "Z") * pauli(result, "B", "Z")
    for shot, sim in enumerate(simulators):
        frames = [evaluated.final_frames[q][shot] for q in "AB"]
        assert corrected_expectation(sim, result, xx, frames) == 1
        assert corrected_expectation(sim, result, zz, frames) == 1
        for q in "AB":
            for axis in "XZ":
                assert sim.peek_observable_expectation(pauli(result, q, axis)) == 0
    ref = explicit_reference(result, evaluated.corrected_measurements[0],
                             {k: v[:1] for k, v in corrections.items()})
    assert ref.peek_observable_expectation(xx) == ref.peek_observable_expectation(zz) == 1
    assert np.any(raw)
