"""Copied beside the standalone consumer, run only against an isolated built wheel.

This script intentionally imports no tests/examples modules or private converter
modules. Fault oracles belong to the separate source-tree physics regressions.
"""

import importlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import installed_consumer as consumer
import numpy as np
import stim

from logical_to_stim_converter import (
    BellStatePrep,
    BlockUseId,
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LSTIMCompileError,
    NoiseModel,
    ResourcePreparationNoise,
    SyndromeExtraction,
    parse_logical_circuit,
)
from logical_to_stim_converter.decoding import (
    DecoderViewError,
    DetectorSelector,
    SourceMismatchError,
    StageInputs,
    UnsupportedProjectionError,
    make_conditional_readout_model,
)


def raises(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"Expected {error.__name__}")


def assert_installed(installed):
    for name, module in tuple(sys.modules.items()):
        if name == 'logical_to_stim_converter' or name.startswith('logical_to_stim_converter.'):
            assert Path(module.__file__).is_relative_to(installed), (name, module.__file__)


def analyze_without_execution(callback):
    # Real physical sampling happened before this scope. No oracle/probe sampling.
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline replay attempted quantum execution')
    with patch.object(stim.Circuit, 'compile_sampler', forbidden), \
            patch.object(stim.Circuit, 'compile_detector_sampler', forbidden), \
            patch.object(stim, 'TableauSimulator', forbidden), \
            patch.object(stim, 'FlipSimulator', forbidden):
        return callback()


def check_m9(compiled, setup, probability, background):
    assert len(compiled.resource_preparation_boundaries) == 6
    uses = {u.use_id for u in compiled.block_uses}
    for boundary in compiled.resource_preparation_boundaries:
        assert boundary.block_use_id in uses
        inst = compiled.circuit[boundary.channel_instruction]
        assert inst.name == 'DEPOLARIZE1' and inst.tag == boundary.channel_tag
        assert inst.gate_args_copy() == [probability]
        prep = next(p for p in compiled.preparations
                    if p.module_id == boundary.preparation_module_id)
        assert boundary.data_sites == tuple((prep.block_id, q) for q in prep.data_ids)
        assert [t.value for t in inst.targets_copy()] == [
            compiled.physical_qubit_map[site] for site in boundary.data_sites]
        tick = max(i for i, inst in enumerate(compiled.circuit[:boundary.channel_instruction])
                   if inst.name == 'TICK')
        assert all(inst.tag.startswith('resource_post_se:')
                   for inst in compiled.circuit[tick + 1:boundary.channel_instruction])
        resource = next(i for i, instruction in enumerate(compiled.circuit)
                        if instruction.tag == boundary.resource_entangling_module_id)
        assert boundary.channel_instruction < resource
        request = next(r for r in setup.requests.boundaries
                       if r.module_id == boundary.preparation_module_id)
        # A later prefix legitimately retains channels from earlier cycles.
        assert not any(i.tag == boundary.channel_tag for i in request.model_circuit)
    for model in setup.conditional_models:
        assert 'before post-SE' in model.boundary_convention
        channels = {b.channel_instruction for b in compiled.resource_preparation_boundaries
                    if b.resource_entangling_module_id == model.resource_entangling_module_id}
        assert model.start_instruction == min(channels)
        atoms = [f for f in model.faults if f.instruction_index in channels]
        assert len(atoms) == 54
        assert len(model.faults) > 54 if background else len(model.faults) == 54
        groups = {}
        for fault in atoms:
            assert fault.probability == probability / 3
            groups.setdefault(fault.exclusive_group, []).append(fault)
        assert len(groups) == 18
        assert all({f.paulis[0][1] for f in group} == set('XYZ') for group in groups.values())
        for transform, width in [(model.raw_flip_map, len(model.readout_record_ids)),
                                 (model.output_x_map, len(model.output_data_ids)),
                                 (model.output_z_map, len(model.output_data_ids)),
                                 (model.logical_flip_map, 2)]:
            assert transform.input_size == len(model.faults)
            assert len(transform.supports) == width


def run(installed, samples, artifacts):
    assert Path(consumer.__file__).parent == Path.cwd()
    assert_installed(installed)
    for name in ('examples', 'tests', 'external_lib', 'pymatching', 'matplotlib',
                 'knill_bench', 'lomatching', 'surface_sim', 'hex'):
        raises(AssertionError, lambda: importlib.import_module(name))
    fake = 'logical_to_stim_converter.accidental_checkout_leak'
    sys.modules[fake] = SimpleNamespace(__file__=str(Path.cwd() / 'src/leak.py'))
    try:
        raises(AssertionError, lambda: assert_installed(installed))
    finally:
        del sys.modules[fake]

    for workflow, filename, measurements, detectors in (
        ('memory', 'memory_d3.lstim', 49, 40),
        ('knill', 'three_patch_knill_d3.lstim', 255, 192),
    ):
        program, standard, other, special = artifacts[filename]
        ideal = program.compile(noise_model=NoiseModel())
        cases = [('ideal', ideal), ('ordinary', standard)]
        if workflow == 'knill':
            mixed = program.compile(noise_model=NoiseModel(
                default=NoiseModel.uniform_depolarizing(.001).default,
                resource_preparation=ResourcePreparationNoise(True, .003)))
            cases += [('m9_only', special), ('m9_background', mixed)]
            assert tuple(program.label_spans) == ('cycle0', 'cycle1', 'cycle2')
        for mode, compiled in cases:
            compiled.validate_metadata()
            canonical = compiled.circuit.copy()
            dem = compiled.circuit.detector_error_model()
            raw = compiled.circuit.compile_sampler(seed=41).sample(32)  # One batch per case.
            raw.flags.writeable = False
            before = raw.copy()
            assert raw.dtype == np.bool_ and raw.shape == (32, measurements)
            full = compiled.make_decoder_view()
            inputs = full.inputs_from_raw(raw)
            events, labels = compiled.circuit.compile_m2d_converter().convert(
                measurements=raw, separate_observables=True)
            assert inputs.detection_events.shape == (32, detectors)
            np.testing.assert_array_equal(inputs.detection_events, events)
            np.testing.assert_array_equal(inputs.observable_flips, labels)
            if workflow == 'memory':
                result = analyze_without_execution(lambda: consumer.analyze_memory(compiled, raw))
                view = result['local']
                assert view.measurement_map.global_ids == (48, 47, 46, 45)
                assert view.detector_map.global_ids == tuple(range(39, -1, -2))
                assert view.observable_map.global_ids == (0,)
                assert view.detector_map.global_to_local[39] == 0
                np.testing.assert_array_equal(
                    view.project_raw_measurements(raw), raw[:, [48, 47, 46, 45]])
                assert result['values'].shape == (32, 1)
                raises(ValueError, lambda: consumer.analyze_memory(
                    compiled, raw, predictor=lambda v, e: np.zeros((1, 1), dtype=bool)))
                raises(ValueError, lambda: consumer.analyze_memory(
                    compiled, raw, predictor=lambda v, e: np.zeros((32, 1), dtype=float)))
            else:
                setup = consumer.prepare_knill(compiled)
                assert len(compiled.block_uses) == 7
                assert compiled.block_uses[-1].use_id == BlockUseId('P0', 2)
                assert [r.output_use_id for r in compiled.relocation_history] == [
                    BlockUseId('P2', 0), BlockUseId('P1', 1), BlockUseId('P0', 2)]
                assert compiled.logical_to_block == {'D': 'P0'}
                assert len(compiled.bell_measurements) == 3
                assert len(setup.requests.boundaries) == 10
                assert len(setup.requests.readouts) == 7
                for request in setup.requests.boundaries:
                    assert request.source_preparation.block_use_id == request.block_use_id
                view = compiled.make_decoder_view(
                    detector_selector=DetectorSelector(
                        use_ids=(BlockUseId('P0', 2),), use_membership='strict'),
                    observable_selector=('D',))
                assert view.audit.region_use_ids == (BlockUseId('P0', 2),)
                if mode.startswith('m9'):
                    check_m9(compiled, setup, .003, mode == 'm9_background')
                result = analyze_without_execution(lambda: consumer.analyze_knill(setup, raw))
                replay = analyze_without_execution(lambda: consumer.analyze_knill(setup, raw))
                np.testing.assert_array_equal(replay['values'], result['values'])
                np.testing.assert_array_equal(result['batch'].raw_measurements, raw)
                assert result['batch'].final_x.shape == (32, 51)
                # Noiseless random gauge sectors must produce actual nonidentity corrections.
                if mode == 'ideal':
                    assert any(r.correction.bits.any() for _, r in result['results'])
                    assert not result['failures'].any()
                boundary = setup.plan.boundaries[0]
                first = result['results'][0][1].correction
                def fresh():
                    return setup.plan.start(raw, source_fingerprint=setup.plan.source_fingerprint)
                raises(DecoderViewError, lambda: fresh().apply(replace(
                    first, block_use_id=BlockUseId(first.block_use_id.block_id, 99))))
                raises(DecoderViewError, lambda: fresh().apply(replace(
                    first, bits=first.bits[:, :-1], input_ids=None)))
                raises(DecoderViewError, lambda: fresh().apply(replace(
                    first, input_ids=tuple(reversed(boundary.input_ids)))))
                raises(SourceMismatchError, lambda: fresh().apply(replace(
                    first, source_fingerprint='stale')))
                raises(DecoderViewError, lambda: result['batch'].apply(first))
                raises(DecoderViewError, lambda: setup.plan.start(
                    raw[:, :-1], source_fingerprint=setup.plan.source_fingerprint))
                raises(SourceMismatchError, lambda: consumer.analyze_knill(
                    replace(setup, compiled=other), raw))
                foreign = consumer.make_conditional_readout_model(other, other.bell_measurements[0])
                raises(SourceMismatchError, lambda: consumer.analyze_knill(
                    replace(setup, conditional_models=(foreign,)), raw))
                stage = result['results'][0][0]
                adapter = consumer.ObservedSectorAdapter(setup.plan)
                raises(SourceMismatchError, lambda: adapter.decode_batch(
                    setup.requests.boundaries[0], replace(stage, source_fingerprint='stale')))
                raises(DecoderViewError, lambda: adapter.decode_batch(
                    setup.requests.boundaries[0], replace(stage, records=stage.records[:, :-1])))
            raises(DecoderViewError, lambda: full.events_from_raw(raw[:, :-1]))
            raises(SourceMismatchError, lambda: full.assert_source(other))
            np.testing.assert_array_equal(before, raw)
            assert compiled.circuit == canonical and compiled.circuit.detector_error_model() == dem
            assert result['failures'].dtype == np.bool_ and result['failures'].shape == (32, 1)
            if mode == 'ideal':
                assert not inputs.detection_events.any() and not inputs.observable_flips.any()
                assert not result['failures'].any()
            print('consumer case passed:', workflow, mode, raw.shape, inputs.detection_events.shape,
                  'errors', int(result['failures'].sum()))

    bad = (samples / 'three_patch_knill_d3.lstim').read_text().replace('BIND A1 P0', 'BIND A1 P2')
    raises(LSTIMCompileError, lambda: parse_logical_circuit(bad).compile())
    for probability in (True, -.1, .7500000001, float('nan')):
        raises(ValueError, lambda: ResourcePreparationNoise(True, probability))
    raises(DecoderViewError, lambda: StageInputs('source', np.zeros((2, 1)), np.zeros((3, 1))))
    blocks = [LogicalBlock.placed(q, CodeSpec.rotated_surface(3), patch_index=i)
              for i, q in enumerate('DAB')]
    unsupported = CircuitCompiler(blocks).compile([
        LogicalInit('D', 'Z', 1), BellStatePrep('A', 'B', 1), SyndromeExtraction('D', 1),
        KnillEC('D', 'A', 'B', prepare_resource=False), LogicalMeasure('D', 'Z'),
    ], noise_model=NoiseModel(resource_preparation=ResourcePreparationNoise(True, .003)))
    unsupported.circuit.detector_error_model()
    raises(UnsupportedProjectionError, lambda: make_conditional_readout_model(
        unsupported, unsupported.bell_measurements[0]))
    assert_installed(installed)
    print('installed consumer workflows, source/use/shape/model/import negatives passed')
