"""Signed physical-flow checks, including deliberately corrupted implementations."""

import pytest
import stim
import stimflow as sf

from logical_to_stim_converter.backends.surface_code import RotatedSurfaceCodeBackend
from logical_to_stim_converter.core.code_spec import CodeSpec
from logical_to_stim_converter.core.logical_block import LogicalBlock


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_memory_chunks(d, basis):
    block = LogicalBlock.placed("physical", CodeSpec.rotated_surface(d))
    backend = RotatedSurfaceCodeBackend()
    code = backend.stabilizer_code(block, "logical")
    code.verify()
    init = backend.initialization(block, "logical", basis)
    se = backend.syndrome_round(block, "logical")
    meas = backend.measurement(block, "logical", basis)
    for chunk in [init, se, meas]:
        chunk.verify()
        assert all(f.sign is False for f in chunk.flows)
    assert len(se.flows) == 2 * (d * d - 1) + 2
    assert len(init.flows) == (d * d - 1) // 2 + 1
    assert len(init.discarded_outputs) == (d * d - 1) // 2 + 1
    assert len(meas.discarded_inputs) == (d * d - 1) // 2 + 1
    assert sum(f.start.obs_name is not None for f in se.flows) == 2
    loop = sf.ChunkLoop([se], repetitions=d)
    loop.verify()
    compiler = sf.ChunkCompiler()
    for component in [init, loop, meas]:
        compiler.append(component)
    circuit = compiler.finish_circuit()
    assert circuit.num_detectors == d * (d * d - 1)
    assert circuit.num_observables == 1
    circuit.detector_error_model()
    dets, obs = circuit.compile_detector_sampler(seed=4).sample(50, separate_observables=True)
    assert not dets.any()
    assert not obs.any()


def test_corrupted_physical_gate_and_flow_fail():
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(3))
    se = RotatedSurfaceCodeBackend().syndrome_round(block, "q")
    bad_circuit = stim.Circuit()
    removed = False
    for instruction in se.circuit:
        if instruction.name == "CX" and not removed:
            removed = True
            continue
        bad_circuit.append(instruction)
    assert removed
    with pytest.raises(ValueError):
        se.with_edits(circuit=bad_circuit).verify()
    flow = se.flows[0]
    with pytest.raises(ValueError):
        se.with_edits(flows=[flow.with_edits(measurement_indices=[]), *se.flows[1:]]).verify()
    # An incorrect sign must fail even though the unsigned support is correct.
    with pytest.raises(ValueError):
        se.with_edits(flows=[flow.with_edits(sign=True), *se.flows[1:]]).verify()
