"""Noisy correction hypotheses are well formed without being noiseless truth."""

from dataclasses import replace

import numpy as np
import pytest

from logical_to_stim_converter import (
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    PauliFrame,
)
from tests.helpers.knill_physics import make_compiler
from tests.helpers.preparation_matching import preparation_corrections


@pytest.fixture(scope="module")
def result():
    return make_compiler().compile([LogicalInit("D", "X", 1), KnillEC("D", "A", "B"),
                                    LogicalMeasure("D", "X")],
                                   noise_model=NoiseModel.uniform_depolarizing(.002))


def test_faulty_final_check_does_not_reject_a_well_formed_hypothesis(result):
    raw = result.ideal_circuit.compile_sampler(seed=63).sample(32)
    corrections = preparation_corrections(result, raw)
    result.validate_noiseless_preparation_corrections(raw, corrections)
    baseline = result.evaluate_frames(raw, corrections)
    # A classical measurement-result fault leaves the underlying sector intact.
    prep = result.preparations[0]
    i = result.measurement_index_by_key[prep.checks[0].measurements[-1]]
    faulty = raw.copy()
    faulty[:, i] ^= True
    before = faulty.copy()
    circuit_before = result.noisy_circuit.copy()
    with pytest.raises(ValueError, match="check equations"):
        result.validate_noiseless_preparation_corrections(faulty, corrections)
    with pytest.raises(ValueError, match="check equations"):
        result.evaluate_frames(faulty, corrections)  # M5 strict default remains
    evaluated = result.evaluate_frames(faulty, corrections, validation="hypothesis")
    assert np.array_equal(evaluated.logical_outputs, baseline.logical_outputs)
    expected_records = baseline.corrected_measurements.copy()
    expected_records[:, i] ^= True
    assert np.array_equal(evaluated.corrected_measurements, expected_records)
    assert np.array_equal(result.interpreted_measurements(
        faulty, preparation_corrections=corrections, validation="hypothesis"),
        evaluated.logical_outputs)
    assert np.array_equal(before, faulty) and result.noisy_circuit == circuit_before
    again = result.evaluate_frames(faulty, corrections, validation="hypothesis")
    assert np.array_equal(again.corrected_measurements, evaluated.corrected_measurements)


def test_actual_noisy_samples_accept_external_hypotheses_without_oracle(result):
    raw = result.noisy_circuit.compile_sampler(seed=64).sample(64)
    hypotheses = {p.module_id: p.resolve(np.zeros(len(p.data_ids)), np.zeros(len(p.data_ids)))
                  for p in result.preparations}
    evaluated = result.evaluate_frames(raw, hypotheses, validation="hypothesis")
    assert evaluated.logical_outputs.shape == (64, 1)
    with pytest.raises(ValueError, match="check equations"):
        result.validate_noiseless_preparation_corrections(raw, hypotheses)


def test_wrong_logical_eigenvalue_is_a_hypothesis_not_a_noiseless_proof(result):
    raw = result.ideal_circuit.compile_sampler(seed=65).sample(16)
    corrections = preparation_corrections(result, raw)
    baseline = result.evaluate_frames(raw, corrections)
    p = result.preparations[0]
    # Multiply the input correction by logical Z, preserving every check sector.
    changed = []
    for frame in corrections[p.module_id]:
        z_support = set(frame.z_support) ^ set(p.logical_z)
        changed.append(p.resolve([q in frame.x_support for q in p.data_ids],
                                 [q in z_support for q in p.data_ids]))
    corrections[p.module_id] = tuple(changed)
    with pytest.raises(ValueError, match="logical eigenvalue"):
        result.validate_noiseless_preparation_corrections(raw, corrections)
    hypothesis = result.evaluate_frames(raw, corrections, validation="hypothesis")
    assert np.array_equal(hypothesis.logical_outputs, ~baseline.logical_outputs)


@pytest.mark.parametrize("corruption", ["missing", "unresolved", "orientation", "source",
                                         "support", "sign", "shot_count", "mode"])
def test_malformed_hypotheses_still_fail(result, corruption):
    raw = result.ideal_circuit.compile_sampler(seed=66).sample(8)
    corrections = preparation_corrections(result, raw)
    p = result.preparations[0]
    frame = corrections[p.module_id][0]
    mode = "hypothesis"
    if corruption == "missing":
        del corrections[p.module_id]
    elif corruption == "shot_count":
        corrections[p.module_id] = corrections[p.module_id][:-1]
    elif corruption == "mode":
        mode = "oracle"
    else:
        changes = {
            "unresolved": {"x_support": None, "z_support": None},
            "orientation": {"orientation": 1},
            "source": {"source_syndromes": ()},
            "support": {"x_support": ("nonexistent",)},
            "sign": {"logical_contribution": PauliFrame(
                x_constant=not frame.logical_contribution.x_constant,
                z_constant=frame.logical_contribution.z_constant)},
        }
        corrections[p.module_id] = replace(frame, **changes[corruption])
    with pytest.raises(ValueError):
        result.evaluate_frames(raw, corrections, validation=mode)
