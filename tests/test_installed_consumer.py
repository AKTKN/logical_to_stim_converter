"""Independent physical checks for the public-only illustrative consumer.

Wheel isolation is exercised by test_lstim_packaging using one shared build.
These source-tree tests may use existing independent reference/fault utilities;
none of them is shipped into or imported by the standalone consumer.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import stim

from examples.installed_consumer import analyze_knill, analyze_memory, prepare_knill
from logical_to_stim_converter import (
    BindPatch,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    ResourcePreparationNoise,
    SyndromeExtraction,
)
from tests.helpers.lstim_equivalence import assert_experiment_equal, compile_pair
from tests.helpers.lstim_programs import knill_operations
from tests.test_patch_reuse_knill_e2e import assert_physical_conditional_atoms

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('workflow', ['memory', 'knill'])
def test_installed_consumer_source_matches_independent_public_operations(workflow):
    source = (ROOT / 'examples/lstim' / (
        'memory_d3.lstim' if workflow == 'memory' else 'three_patch_knill_d3.lstim'
    )).read_text(encoding='utf-8')
    operations = (
        (BindPatch('D', 'P0'), LogicalInit('D', 'Z', 3),
         SyndromeExtraction('D', 1), SyndromeExtraction('D', 1), LogicalMeasure('D', 'Z'))
        if workflow == 'memory' else knill_operations()
    )
    noise = NoiseModel(
        default=NoiseModel.uniform_depolarizing(.001).default,
        resource_preparation=ResourcePreparationNoise(workflow == 'knill', .003),
    )
    actual, reference = compile_pair(
        source, operations, count=1 if workflow == 'memory' else 3, noise=noise,
    )
    raw = assert_experiment_equal(actual, reference, shots=4, seed=903)
    setup = prepare_knill(actual) if workflow == 'knill' else None
    other = prepare_knill(reference) if workflow == 'knill' else None
    with patch.object(stim.Circuit, 'compile_sampler', side_effect=AssertionError('resampling')):
        first = analyze_knill(setup, raw) if setup else analyze_memory(actual, raw)
        second = analyze_knill(other, raw) if other else analyze_memory(reference, raw)
    np.testing.assert_array_equal(first['values'], second['values'])
    np.testing.assert_array_equal(first['failures'], second['failures'])
    if workflow == 'knill':
        # Existing Stim FlipSimulator oracle independently checks each physical
        # atom's raw/survivor actions; no oracle is passed into the consumer.
        for model in setup.conditional_models:
            assert_physical_conditional_atoms(actual, model)


def test_noiseless_consumer_frames_match_strict_physical_frame_replay():
    source = (ROOT / 'examples/lstim/three_patch_knill_d3.lstim').read_text(encoding='utf-8')
    compiled, _ = compile_pair(source, knill_operations(), count=3)
    setup = prepare_knill(compiled)
    raw = compiled.circuit.compile_sampler(seed=97).sample(32)
    before = raw.copy()
    result = analyze_knill(setup, raw)
    # Compare the sparse consumer path to the original independently exercised
    # per-shot physical-frame propagation and strict final-sector equations.
    corrections = {r.correction.boundary_id: r.correction.bits for _, r in result['results']}
    frames = {}
    for prep in compiled.preparations:
        bits = corrections[prep.module_id]
        n = len(prep.data_ids)
        frames[prep.module_id] = tuple(prep.resolve(row[:n], row[n:]) for row in bits)
    compiled.validate_noiseless_preparation_corrections(raw, frames)
    strict = compiled.evaluate_frames(raw, frames)
    np.testing.assert_array_equal(strict.logical_outputs, result['values'])
    np.testing.assert_array_equal(strict.corrected_measurements,
                                  result['batch'].interpreted_measurements)
    np.testing.assert_array_equal(raw, before)
    assert any(bits.any() for bits in corrections.values())
    assert not result['failures'].any()


def test_memory_consumer_signed_labels_and_nontrivial_observable_order():
    from logical_to_stim_converter import parse_logical_circuit

    compiled = parse_logical_circuit('''FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
PATCH P1 sc index=1
BIND A P0
BIND B P1
PARALLEL {
    INIT_Z(3) A
    INIT_X(3) B
}
X A mode=frame
PARALLEL {
    MZ A
    MX B
}
''').compile()
    raw = compiled.circuit.compile_sampler(seed=93).sample(8)
    result = analyze_memory(compiled, raw)
    assert result['local'].observable_map.local_to_global == (1, 0)
    assert result['local'].observable_map.global_to_local == {1: 0, 0: 1}
    np.testing.assert_array_equal(result['values'], [[False, True]] * 8)
    assert not result['failures'].any()
    # The external predictor sees only events, never observable truth labels.
    opposite = analyze_memory(
        compiled, raw, predictor=lambda v, e: np.ones((len(e), 2), dtype=bool))
    assert opposite['failures'].all()
    np.testing.assert_array_equal(opposite['values'], [[True, False]] * 8)


@pytest.mark.parametrize('workflow', ['memory', 'knill'])
def test_consumer_cli_samples_one_physical_batch(workflow, monkeypatch, capsys):
    import json
    import sys

    from examples import installed_consumer

    filename = 'memory_d3.lstim' if workflow == 'memory' else 'three_patch_knill_d3.lstim'
    monkeypatch.setattr(sys, 'argv', ['installed_consumer.py', workflow,
                                    str(ROOT / 'examples/lstim' / filename), '--shots', '4'])
    original = stim.Circuit.compile_sampler
    calls = []

    class CountedSampler:
        def __init__(self, sampler):
            self.sampler = sampler

        def sample(self, *, shots):
            calls.append(shots)
            return self.sampler.sample(shots=shots)

    def compile_once(circuit, **options):
        return CountedSampler(original(circuit, **options))

    monkeypatch.setattr(stim.Circuit, 'compile_sampler', compile_once)
    installed_consumer.main()
    report = json.loads(capsys.readouterr().out)
    assert calls == [4]
    assert report['errors'] == 0 and report['raw_shape'][0] == 4
