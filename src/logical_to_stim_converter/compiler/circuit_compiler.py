"""Verified composition of explicit layers of independent memory operations."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import zip_longest
from types import MappingProxyType

import stim
import stimflow as sf

from ..backends.surface_code import RotatedSurfaceCodeBackend
from ..core.code_backend import CodeBackend
from ..core.compiler_context import (
    BlockStatus,
    CompilerContext,
    DetectorInfo,
    MeasurementInfo,
    ObservableInfo,
    PauliFrame,
    TimeLayer,
)
from ..core.logical_block import GlobalSiteId, LogicalBlock
from ..core.module_fragment import ModuleFragment
from ..noise.injector import NoiseInjector
from ..noise.model import NoiseModel
from ..operations.base import OperationModule
from ._metadata import extract_metadata
from ._parallel import parallel_chunk


@dataclass(frozen=True)
class CompiledCircuit:
    ideal_circuit: stim.Circuit
    noisy_circuit: stim.Circuit | None
    physical_qubit_map: Mapping[GlobalSiteId, int]
    logical_to_block: Mapping[str, str]
    measurements: tuple[MeasurementInfo, ...]
    detectors: tuple[DetectorInfo, ...]
    observables: tuple[ObservableInfo, ...]
    frames: Mapping[str, PauliFrame]
    block_status: Mapping[str, BlockStatus]
    time_layers: tuple[TimeLayer, ...]
    fragments: tuple[ModuleFragment, ...]

    def __post_init__(self) -> None:
        for name in ("physical_qubit_map", "logical_to_block", "frames", "block_status"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    @property
    def circuit(self) -> stim.Circuit:
        return self.noisy_circuit if self.noisy_circuit is not None else self.ideal_circuit


class CircuitCompiler:
    """Each list/tuple of operations is a parallel logical layer and a barrier.

    A single operation may target multiple patches concurrently. Separate entries
    are sequential; no implicit optimizer moves work across these barriers.
    """

    def __init__(
        self,
        blocks: Sequence[LogicalBlock],
        *,
        logical_to_block: Mapping[str, str] | None = None,
        backend: CodeBackend | None = None,
    ):
        self.blocks = tuple(blocks)
        context = CompilerContext(self.blocks, logical_to_block)
        self.logical_to_block = dict(context.logical_to_block)
        self.backend = backend if backend is not None else RotatedSurfaceCodeBackend()

    def compile(
        self,
        operations: Sequence[OperationModule | Sequence[OperationModule]],
        *,
        noise_model: NoiseModel | None = None,
    ) -> CompiledCircuit:
        context = CompilerContext(self.blocks, self.logical_to_block)
        groups = [
            [entry] if isinstance(entry, OperationModule) else list(entry) for entry in operations
        ]
        if any(
            not group or any(not isinstance(op, OperationModule) for op in group)
            for group in groups
        ):
            raise ValueError("Each logical layer requires operation objects")
        compiler = sf.ChunkCompiler()
        compiler.ensure_qubits_included(context.site_positions.values())
        # Only matched-basis observables survive. This explicit order is independent
        # of block registration and physical coordinate sorting.
        prepared = {}
        for group in groups:
            for op in group:
                if op.operation_type == "LogicalInit":
                    prepared.update({logical: op.basis for logical in op.targets})
        compiler.ensure_observables_included(
            [(logical, prepared[logical]) for logical in sorted(prepared)]
        )
        all_fragments = []
        seen_ids = set()
        operation_index = 0
        for group in groups:
            target_ids = [t for op in group for t in op.targets]
            if len(target_ids) != len(set(target_ids)):
                raise ValueError("A parallel layer operates on the same logical block twice")
            fragments = []
            for op in group:
                identity = op.operation_id or f"op{operation_index:04d}"
                operation_index += 1
                if identity in seen_ids:
                    raise ValueError("Operation IDs must be unique within a compilation")
                seen_ids.add(identity)
                for logical in sorted(op.targets):
                    context.transition(op.operation_type, logical, getattr(op, "basis", None))
                    block = context.block_for(logical)
                    module_id = f"module{len(all_fragments) + len(fragments):04d}"
                    fragment = replace(
                        op.build(self.backend, block, logical, module_id), operation_id=identity
                    )
                    fragment.verify()
                    fragments.append(fragment)
            all_fragments.extend(fragments)
            streams = [[(chunk, f) for chunk in f.chunks()] for f in fragments]
            for parts in zip_longest(*streams):
                combined = parallel_chunk(
                    [part for part in parts if part is not None], compiler.cur_end_interface()
                )
                compiler.append(combined)
        if any(status != BlockStatus.MEASURED for status in context.status.values()):
            raise ValueError("A complete memory circuit must initialize and measure every block")
        ideal = compiler.finish_circuit()
        # This checks deterministic detectors and observables independently of Chunk flows.
        ideal.detector_error_model()
        fragment_tuple = tuple(all_fragments)
        physical_map, observables = extract_metadata(ideal, context, fragment_tuple)
        fragment_tuple = tuple(
            replace(
                f,
                measurement_records=tuple(
                    m for m in context.measurements if m.module_id == f.module_id
                ),
            )
            for f in fragment_tuple
        )
        noisy = None
        if noise_model is not None:
            noisy = NoiseInjector().apply(
                ideal,
                model=noise_model,
                physical_map=physical_map,
                layers=context.layers,
                fragments=fragment_tuple,
            )
            noisy.detector_error_model()
        return CompiledCircuit(
            ideal,
            noisy,
            physical_map,
            context.logical_to_block,
            context.measurements,
            context.detectors,
            observables,
            context.frames,
            context.status,
            context.layers,
            fragment_tuple,
        )
