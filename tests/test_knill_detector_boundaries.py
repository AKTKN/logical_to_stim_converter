"""Verified physical relations are distinct from emitted decoder regions."""

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
)
from logical_to_stim_converter.compiler._metadata import validate_detector_regions
from tests.helpers.knill_physics import make_compiler


@pytest.mark.parametrize("d", [3, 5])
def test_knill_stage_boundaries_and_raw_bell_syndromes(d):
    result = make_compiler(d).compile([
        LogicalInit("D", "X", 1), KnillEC("D", "A", "B"),
        SyndromeExtraction("D", 2), LogicalMeasure("D", "X")],
        noise_model=NoiseModel.uniform_depolarizing(.001))
    result.ideal_circuit.detector_error_model()
    result.noisy_circuit.detector_error_model()
    raw = result.ideal_circuit.compile_sampler(seed=6).sample(100)
    assert len(result.detectors) == result.ideal_circuit.num_detectors
    validate_detector_regions(result.detectors, result.measurements)
    prep_modules = {p.module_id for p in result.preparations
                    if p.logical_id in ("A", "B")}
    prep_record_indices = {m.index for m in result.measurements if m.module_id in prep_modules}
    for detector in result.detectors:
        assert not np.bitwise_xor.reduce(raw[:, detector.measurement_indices], axis=1).any()
        records = [result.measurements[i] for i in detector.measurement_indices]
        assert {m.stage_id for m in records} == {detector.stage_id}
        if detector.stage_id and "resource_prep" in detector.stage_id:
            assert len({m.module_id for m in records}) == 1
            assert len(detector.supporting_block_ids) == 1
        if detector.stage_id and "teleportation" in detector.stage_id:
            assert not prep_record_indices.intersection(detector.measurement_indices)
    assert result.suppressed_detectors
    # The excluded global relations were valid physical flows. Put one back:
    # Stim accepts it, while the explicit decoder-boundary validator rejects it.
    suppressed = next(s for s in result.suppressed_detectors
                      if any(stage and "teleportation" in stage for stage in s.stage_ids))
    probe = result.ideal_circuit.copy()
    probe.append("DETECTOR", [stim.target_rec(i - probe.num_measurements)
                              for i in suppressed.measurement_indices])
    probe.detector_error_model()
    bad = replace(result.detectors[0], stage_id="teleportation",
                  measurement_indices=suppressed.measurement_indices)
    with pytest.raises(ValueError, match="boundary"):
        validate_detector_regions((bad,), result.measurements)
    bell, = result.bell_measurements
    keys = {m.key: m.index for m in result.measurements}
    for readout in (bell.x_readout, bell.z_readout):
        assert readout.mode == "random"
        assert len(readout.records) == d*d
        assert all(result.measurements[keys[k]].stage_id == readout.stage_id
                   for k in readout.records)
        samples = raw[:, [keys[k] for k in readout.records]]
        # All local parity-check mappings are exported, including sector-valued
        # one-shot readout syndromes that cannot be standalone detectors.
        syndrome = samples.astype(np.uint8) @ readout.check_matrix(readout.basis).T % 2
        assert syndrome.shape == (100, (d*d-1)//2)
        assert syndrome.any()
        assert len(set(readout.logical_parity.evaluate(raw, keys))) == 2
    assert result.ideal_circuit.num_measurements == result.noisy_circuit.num_measurements
    assert result.ideal_circuit.num_detectors == result.noisy_circuit.num_detectors
