"""Full deterministic detector annotations, exact global indices, and legacy views."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    TransversalH,
)
from logical_to_stim_converter.compiler._metadata import separate_detector_regions
from tests.helpers.knill_physics import make_compiler
from tests.test_clifford_noise import fault_counter


@pytest.fixture(scope="module", params=[3, 5])
def artifacts(request):
    d = request.param
    opened = make_compiler(d).compile([
        LogicalInit("D", "X", 1), KnillEC("D", "A", "B")],
        allow_open_outputs=True, noise_model=NoiseModel.uniform_depolarizing(.001))
    closed = opened.append([SyndromeExtraction("D", 2), TransversalH("D"),
                            LogicalMeasure("D", "Z")])
    return d, opened, closed


def annotation_parities(circuit):
    """Read Stim rec targets independently of converter metadata."""
    cursor = 0
    result = []
    for instruction in circuit:
        cursor += instruction.num_measurements
        if instruction.name == "DETECTOR":
            result.append(tuple(sorted(cursor + t.value for t in instruction.targets_copy())))
    return tuple(result)


def without_detectors(circuit):
    result = stim.Circuit()
    for instruction in circuit:
        if instruction.name != "DETECTOR":
            result.append(instruction)
    return result


def test_global_recovery_and_explicit_stage_view(artifacts):
    d, opened, closed = artifacts
    n = d*d - 1
    assert opened.ideal_circuit.num_detectors == n * (4*d + 1) // 2
    assert len(opened.detector_boundary_candidates) == n
    for result in (opened, closed):
        result.validate_metadata()
        full = result.ideal_circuit
        view = result.stage_separated_circuit()
        retained = result.stage_separated_detector_indices
        assert full.num_detectors == view.num_detectors + len(result.detector_boundary_candidates)
        legacy, excluded = separate_detector_regions(full, result.fragments)
        assert legacy == view and excluded == result.detector_boundary_candidates
        assert annotation_parities(view) == tuple(annotation_parities(full)[i] for i in retained)
        assert without_detectors(full) == without_detectors(view)
        full.detector_error_model()
        view.detector_error_model()
        noisy_view = result.stage_separated_circuit(noisy=True)
        result.noisy_circuit.detector_error_model()
        noisy_view.detector_error_model()
        assert without_detectors(result.noisy_circuit) == without_detectors(noisy_view)
        assert fault_counter(result.noisy_circuit) == fault_counter(noisy_view)
        assert full.get_final_qubit_coordinates() == view.get_final_qubit_coordinates()
        assert all(len(c) == 3 for c in full.get_detector_coordinates().values())
        assert np.array_equal(full.compile_sampler(seed=31).sample(32),
                              view.compile_sampler(seed=31).sample(32))
        assert np.array_equal(result.noisy_circuit.compile_sampler(seed=32).sample(32),
                              noisy_view.compile_sampler(seed=32).sample(32))
        # Returning and mutating a view cannot change the canonical circuit.
        count = full.num_detectors
        view.append("DETECTOR")
        assert full.num_detectors == count


def test_exact_global_order_and_raw_parity_reconstruction(artifacts):
    _, opened, closed = artifacts
    for result in (opened, closed):
        raw = result.ideal_circuit.compile_sampler(seed=76).sample(256)
        parities = annotation_parities(result.ideal_circuit)
        reconstructed = np.column_stack([
            np.bitwise_xor.reduce(raw[:, d.measurement_indices], axis=1) for d in result.detectors])
        converted, _ = result.ideal_circuit.compile_m2d_converter().convert(
            measurements=raw, separate_observables=True)
        assert np.array_equal(converted, reconstructed)
        assert not reconstructed.any()
        assert not result.ideal_circuit.compile_detector_sampler(seed=77).sample(256).any()
        by_module = {f.module_id: f for f in result.fragments}
        for d, parity in zip(result.detectors, parities, strict=True):
            assert d.measurement_indices == parity
            assert all(0 <= i < raw.shape[1] for i in parity)
            records = [result.measurements[i] for i in parity]
            assert d.measurement_keys == tuple(m.key for m in records)
            assert {m.key.block_id for m in records} == set(d.supporting_block_ids)
            assert {m.stage_id for m in records} == set(d.source_stage_ids)
            assert d.stage_id == by_module[d.anchor_module_id].stage
            assert d.crosses_decoder_boundary == (len(d.source_stage_ids) > 1)
        for candidate in result.detector_boundary_candidates:
            d = result.detectors[candidate.global_index]
            assert candidate.measurement_indices == d.measurement_indices
            assert candidate.source_stage_ids == d.source_stage_ids
        assert dict(result.measurement_index_by_key) == {
            m.key: m.index for m in result.measurements}


def test_random_bell_bits_and_open_continuation(artifacts):
    d, opened, closed = artifacts
    raw = opened.ideal_circuit.compile_sampler(seed=81).sample(256)
    bell, = opened.bell_measurements
    keys = opened.measurement_index_by_key
    mx, mz = (r.logical_parity.evaluate(raw, keys) for r in (bell.x_readout, bell.z_readout))
    assert len(set(zip(mx, mz, strict=True))) == 4
    assert not opened.observables and opened.ideal_circuit.num_observables == 0
    assert opened.ideal_circuit.num_measurements == (1 + 2*d)*(d*d - 1) + 2*d*d
    assert not any(i.name == "MPP" for i in opened.ideal_circuit)
    for r in (bell.x_readout, bell.z_readout):
        logical_parity = tuple(sorted(keys[k] for k in r.logical_parity.terms))
        assert logical_parity not in annotation_parities(opened.ideal_circuit)
    # Append preserves the full physical prefix, record identities and detector IDs.
    assert closed.measurements[:len(opened.measurements)] == opened.measurements
    assert closed.detectors[:len(opened.detectors)] == opened.detectors
    assert closed.ideal_circuit.num_measurements == (
        opened.ideal_circuit.num_measurements + 2*(d*d-1)+d*d)
    assert len(closed.observables) == 1 and not closed.open_logical_outputs
    assert closed.observables[0].block_id == "physical_B"
    assert closed.observables[0].measurement_indices


@pytest.mark.parametrize("corruption", ["stage", "sources", "boundary", "index", "record",
                                         "measurement_stage", "measurement_key"])
def test_corrupt_global_metadata_is_rejected(artifacts, corruption):
    _, result, _ = artifacts
    if corruption.startswith("measurement"):
        m = result.measurements[0]
        change = ({"stage_id": "wrong"} if corruption == "measurement_stage" else
                  {"key": replace(m.key, local_id="wrong")})
        bad = replace(result, measurements=(replace(m, **change), *result.measurements[1:]))
    else:
        d = result.detectors[0]
        changes = {"stage": {"stage_id": "wrong"},
                   "sources": {"source_stage_ids": ("wrong",)},
                   "boundary": {"crosses_decoder_boundary": not d.crosses_decoder_boundary},
                   "index": {"index": 10000},
                   "record": {"measurement_indices": (result.ideal_circuit.num_measurements,)}}
        bad = replace(result, detectors=(replace(d, **changes[corruption]), *result.detectors[1:]))
    with pytest.raises(ValueError, match="[Ii]ndices|[Aa]ttribution|[Pp]arity"):
        bad.validate_metadata()
