"""Shared memory-program construction, without hiding physics assertions."""

import pytest

from logical_to_stim_converter.compiler.circuit_compiler import CircuitCompiler
from logical_to_stim_converter.core.code_spec import CodeSpec
from logical_to_stim_converter.core.logical_block import LogicalBlock
from logical_to_stim_converter.operations.initialization import LogicalInit
from logical_to_stim_converter.operations.measurement import LogicalMeasure
from logical_to_stim_converter.operations.syndrome_extraction import SyndromeExtraction


@pytest.fixture
def memory():
    def make(*, d=3, bases=("Z",), rounds=1, noise_model=None, reverse=False):
        code = CodeSpec.rotated_surface(d)
        blocks = [
            LogicalBlock.placed(f"physical{i}", code, patch_index=i) for i in range(len(bases))
        ]
        logicals = tuple(f"logical{i}" for i in range(len(bases)))
        binding = {logical: block.block_id for logical, block in zip(logicals, blocks, strict=True)}
        compiler = CircuitCompiler(blocks[::-1] if reverse else blocks, logical_to_block=binding)
        operations = [
            [
                LogicalInit(logical, basis, 1)
                for logical, basis in zip(logicals, bases, strict=True)
            ],
            SyndromeExtraction(logicals, rounds),
            [
                LogicalMeasure(logical, basis)
                for logical, basis in zip(logicals, bases, strict=True)
            ],
        ]
        return compiler.compile(operations, noise_model=noise_model)

    return make
