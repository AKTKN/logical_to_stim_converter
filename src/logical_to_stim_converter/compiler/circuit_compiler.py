"""Verified composition of explicit layers of independent memory operations."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import zip_longest
from types import MappingProxyType

import numpy as np
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
from ..core.module_fragment import ModuleFragment, OperationContext
from ..noise.injector import NoiseInjector
from ..noise.model import NoiseModel
from ..operations.base import OperationModule
from ._logical import LogicalFlowTracker, detector_metadata, prepare_part
from ._metadata import extract_metadata, finalize_observables
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
    orientations: Mapping[str, int]

    def __post_init__(self) -> None:
        for name in (
            "physical_qubit_map",
            "logical_to_block",
            "frames",
            "block_status",
            "orientations",
        ):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    @property
    def circuit(self) -> stim.Circuit:
        return self.noisy_circuit if self.noisy_circuit is not None else self.ideal_circuit

    def interpreted_measurements(self, measurements):
        samples = np.asarray(measurements, dtype=np.bool_)
        if samples.ndim != 2 or samples.shape[1] != self.ideal_circuit.num_measurements:
            raise ValueError("Expected a shot-by-raw-measurement matrix")
        key_to_index = {record.key: record.index for record in self.measurements}
        result = np.empty((len(samples), len(self.observables)), dtype=np.bool_)
        for observable in self.observables:
            value = np.zeros(len(samples), dtype=np.bool_)
            for index in observable.readout_measurement_indices:
                value ^= samples[:, index]
            value ^= observable.frame_correction.evaluate(samples, key_to_index)
            result[:, observable.index] = value
        return result


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
        compiler = sf.ChunkCompiler(metadata_func=detector_metadata)
        compiler.ensure_qubits_included(context.site_positions.values())
        readout_bases = {
            logical: op.basis
            for group in groups
            for op in group
            if op.operation_type == "LogicalMeasure"
            for logical in op.targets
        }
        compiler.ensure_observables_included([(q, readout_bases[q]) for q in sorted(readout_bases)])
        tracker = LogicalFlowTracker(self.backend, context)
        all_fragments = []
        seen_ids = set()
        operation_index = 0
        sequence = 0
        for group in groups:
            target_ids = [t for op in group for t in op.targets]
            target_blocks = [context.block_for(t).block_id for t in target_ids]
            if len(set(target_blocks)) != len(target_blocks):
                raise ValueError("A parallel layer operates on the same physical block twice")
            trial = context.copy()
            fragments = []
            for op in group:
                identity = op.operation_id or f"op{operation_index:04d}"
                operation_index += 1
                if identity in seen_ids:
                    raise ValueError("Operation IDs must be unique within a compilation")
                seen_ids.add(identity)
                operand_groups = [op.targets] if op.coupled else [(q,) for q in sorted(op.targets)]
                for logical_ids in operand_groups:
                    operands = {q: trial.block_for(q) for q in logical_ids}
                    module_id = f"module{len(all_fragments) + len(fragments):04d}"
                    build_context = OperationContext(module_id, trial.orientations)
                    fragment = replace(
                        op.build(self.backend, operands, build_context), operation_id=identity
                    )
                    trial = trial.advanced(op, fragment, self.backend)
                    fragments.append(fragment)
            context = trial
            tracker.context = context
            all_fragments.extend(fragments)
            streams = [[(step, f) for step in f.steps()] for f in fragments]
            for steps in zip_longest(*streams):
                present = [step for step in steps if step is not None]
                reflows = [(step, f) for step, f in present if isinstance(step, sf.ChunkReflow)]
                parts = [(step, f) for step, f in present if isinstance(step, sf.Chunk)]
                # Reflows have no duration and commute with the disjoint parts in this layer.
                for reflow, _ in reflows:
                    compiler.append(reflow)
                if not parts:
                    continue
                tracker.before_readout(compiler, [f for _, f in parts])
                extra, managed = tracker.through(parts)
                prepared = [
                    (prepare_part(chunk, f, self.backend, context.blocks, sequence), f)
                    for chunk, f in parts
                ]
                combined = parallel_chunk(
                    prepared, compiler.cur_end_interface(), extra_flows=extra, managed_ports=managed
                )
                compiler.append(combined)
                sequence += 1
        if any(status != BlockStatus.MEASURED for status in context.status.values()):
            raise ValueError("A complete memory circuit must initialize and measure every block")
        ideal = compiler.finish_circuit()
        # This checks deterministic detectors and observables independently of Chunk flows.
        ideal.detector_error_model()
        fragment_tuple = tuple(all_fragments)
        physical_map, observables = extract_metadata(ideal, context, fragment_tuple, self.backend)
        observables = finalize_observables(ideal, context, observables)
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
            context.orientations,
        )
