"""M9 three-cycle direct/LSTIM equality and same-raw external decoder replay."""

import numpy as np
import pytest

from examples.knill_memory_offline_decoding import analyze_knill, prepare_compiled
from logical_to_stim_converter import NoiseModel, NoiseParameters, ResourcePreparationNoise
from logical_to_stim_converter.decoding import CorrectionBatch, SourceMismatchError
from tests.helpers.lstim_equivalence import assert_exact, assert_experiment_equal, compile_pair
from tests.helpers.lstim_programs import knill_operations, knill_source
from tests.test_lstim_simulation_e2e import (
    assert_chunked_analysis,
    assert_knill_analysis_equal,
    audited_adapters,
    prohibit_quantum_execution,
)


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis,bit", [("X", 0), ("X", 1), ("Z", 0), ("Z", 1)])
@pytest.mark.parametrize("enabled,p,background", [
    (True, 0, 0), (True, 0, .001), (True, .003, .001), (True, .017, 0),
    (False, .003, .001),
])
def test_three_cycles_exact_source_and_same_raw_decoders(
    monkeypatch, distance, basis, bit, enabled, p, background,
):
    parameters = dict(distance=distance, basis=basis, bit=bit)
    noise = NoiseModel(NoiseParameters(*(background for _ in range(5))),
                       resource_preparation=ResourcePreparationNoise(enabled, p))
    c, reference = compile_pair(knill_source(**parameters), knill_operations(**parameters),
                                distance=distance, count=3, noise=noise)
    bs = c.resource_preparation_boundaries
    assert len(bs) == (6 if enabled else 0)
    assert len({b.block_use_id for b in bs}) == (6 if enabled else 0)
    assert len(c.block_uses) == 7 and len(c.relocation_history) == 3
    assert c.circuit.num_qubits == 3 * (2 * distance**2 - 1)
    assert sum(len(c.circuit[b.channel_instruction].targets_copy())
               for b in bs if b.channel_instruction is not None) == (
                   6 * distance**2 if enabled and p else 0)
    experiments = prepare_compiled(c), prepare_compiled(reference)
    a, b = experiments
    assert_exact(a.frame_plan, b.frame_plan)
    assert_exact(a.requests, b.requests)
    assert_exact(a.conditional_models, b.conditional_models)
    for model in a.conditional_models:
        own = [boundary for boundary in bs
               if boundary.resource_entangling_module_id == model.resource_entangling_module_id]
        if enabled and p:
            assert model.start_instruction == min(boundary.channel_instruction for boundary in own)
            for boundary in own:
                atoms = [f for f in model.faults
                         if f.instruction_index == boundary.channel_instruction]
                assert len(atoms) == 3 * distance**2
                assert boundary.block_use_id in (model.first_resource_use_id, model.output_use_id)
    raw = assert_experiment_equal(c, reference, shots=33, seed=927)
    before, dem = raw.copy(), c.circuit.detector_error_model()
    prohibit_quantum_execution(monkeypatch)
    for replacement in (False, True):
        aa, acalls = audited_adapters(a, replacement=replacement)
        ba, bcalls = audited_adapters(b, replacement=replacement)
        result = analyze_knill(a, raw, **aa)
        paired = analyze_knill(b, raw, **ba)
        assert_knill_analysis_equal(result, paired)
        assert_exact(acalls, bcalls)
        expected = np.column_stack([
            np.bitwise_xor.reduce(result.interpreted_measurements[:, o.readout_measurement_indices],
                                  axis=1) ^ o.expected_value for o in c.observables
        ])
        np.testing.assert_array_equal(result.failures, expected)
        if enabled and p == background == 0:
            assert not result.errors and (result.logical_values == bit).all()
        if (distance, basis, bit, enabled, p) == (3, "Z", 0, True, .003):
            chunks = [analyze_knill(a, raw[start:stop], **aa)
                      for start, stop in ((0, 13), (13, 29), (29, 33))]
            assert_chunked_analysis(result, chunks)
    np.testing.assert_array_equal(raw, before)
    assert c.circuit.detector_error_model() == dem == a.global_dem == b.global_dem
    boundary = a.frame_plan.boundaries[0]
    state = a.frame_plan.start(raw, source_fingerprint=a.frame_plan.source_fingerprint)
    with pytest.raises(SourceMismatchError):
        state.apply(CorrectionBatch("stale", boundary.boundary_id,
                                    np.zeros((len(raw), len(boundary.input_ids)), dtype=bool)))
