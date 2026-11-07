"""Verified physical composition, partial outputs, and composite logical contracts."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
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
from ..core.protocol import (
    BellMeasurementResult,
    CompositeInfo,
    LogicalReadout,
    PreparationInfo,
    RelocationRecord,
    SuppressedDetector,
)
from ..noise.injector import NoiseInjector
from ..noise.model import NoiseModel
from ..operations.base import OperationModule
from ._logical import LogicalFlowTracker, detector_metadata, prepare_part
from ._metadata import (
    extract_metadata,
    finalize_observables,
    protocol_metadata,
    separate_detector_regions,
    validate_detector_regions,
)
from ._parallel import parallel_chunk
from ._plan import plan_program
from ._teleport import ProtocolAssembly


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
    preparations: tuple[PreparationInfo, ...] = ()
    readouts: tuple[LogicalReadout, ...] = ()
    bell_measurements: tuple[BellMeasurementResult, ...] = ()
    relocation_history: tuple[RelocationRecord, ...] = ()
    composites: tuple[CompositeInfo, ...] = ()
    suppressed_detectors: tuple[SuppressedDetector, ...] = ()
    open_logical_outputs: Mapping[str, str] = field(default_factory=dict)
    open_interface: sf.ChunkInterface | None = None
    _evaluation_steps: tuple = field(default=(), repr=False, compare=False)
    _compiler: object = field(default=None, repr=False, compare=False)
    _program: tuple = field(default=(), repr=False, compare=False)
    _noise_model: NoiseModel | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "physical_qubit_map",
            "logical_to_block",
            "frames",
            "block_status",
            "orientations",
            "open_logical_outputs",
        ):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    @property
    def circuit(self) -> stim.Circuit:
        return self.noisy_circuit if self.noisy_circuit is not None else self.ideal_circuit

    def interpreted_measurements(self, measurements, *, preparation_corrections=None):
        if preparation_corrections is not None:
            return self.evaluate_frames(measurements, preparation_corrections).logical_outputs
        if self.bell_measurements:
            raise ValueError("Preparation corrections are unresolved; supply physical frames")
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

    def evaluate_frames(self, measurements, preparation_corrections):
        from ._frames import evaluate_frames

        return evaluate_frames(self, measurements, preparation_corrections)

    def append(self, operations, *, noise_model=None):
        """Recompile a continuation with the same verified physical prefix.

        This intentionally favors reproducible full verification over an
        incremental-cache API. No artificial physical readout closes the prefix.
        """
        return self._compiler.compile(
            (*self._program, *operations), allow_open_outputs=True,
            noise_model=self._noise_model if noise_model is None else noise_model)


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
        allow_open_outputs: bool = False,
    ) -> CompiledCircuit:
        context = CompilerContext(self.blocks, self.logical_to_block)
        program = tuple(entry if isinstance(entry, OperationModule) else tuple(entry)
                        for entry in operations)
        plan = plan_program(program, context)
        compiler = sf.ChunkCompiler(metadata_func=detector_metadata)
        compiler.ensure_qubits_included(context.site_positions.values())
        readout_bases = {
            logical: planned.operation.basis
            for step in plan for planned in step.operations
            if planned.operation.operation_type == "LogicalMeasure"
            and planned.operation.mode == "deterministic"
            for logical in planned.operation.targets
        }
        context.output_ids = {q: i for i, q in enumerate(sorted(readout_bases))}
        compiler.ensure_observables_included([(q, readout_bases[q]) for q in sorted(readout_bases)])
        tracker = LogicalFlowTracker(self.backend, context)
        protocol = ProtocolAssembly(self.backend)
        all_fragments = []
        evaluation_steps = []
        sequence = 0
        for step in plan:
            for boundary in step.before:
                protocol.begin(boundary, context)
            target_ids = [t for planned in step.operations for t in planned.operation.targets]
            target_blocks = [context.block_for(t).block_id for t in target_ids]
            if len(set(target_blocks)) != len(target_blocks):
                raise ValueError("A parallel layer operates on the same physical block twice")
            trial = context.copy()
            fragments = []
            for planned in step.operations:
                op, identity = planned.operation, planned.identity
                operand_groups = [op.targets] if op.coupled else [(q,) for q in sorted(op.targets)]
                for logical_ids in operand_groups:
                    operands = {q: trial.block_for(q) for q in logical_ids}
                    module_id = f"module{len(all_fragments) + len(fragments):04d}"
                    build_context = OperationContext(module_id, trial.orientations)
                    fragment = replace(
                        op.build(self.backend, operands, build_context), operation_id=identity,
                        composite_ids=planned.parents,
                        stage=planned.stage or ("post_teleportation" if protocol.bells else None),
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
                    prepared, compiler.cur_end_interface(), extra_flows=extra,
                    managed_ports=managed, measurement_flows=tracker.measurement_flows,
                    discarded_readout_ports=tracker.discarded_readout_ports,
                )
                tracker.discarded_readout_ports = set()
                compiler.append(combined)
                evaluation_steps.append(("physical", combined))
                sequence += 1
            for f in fragments:
                if f.operation_type == "LogicalInit":
                    evaluation_steps.append(("preparation", f.module_id))
                elif f.frame_transition == "frame":
                    block = context.blocks[f.block_id]
                    p = self.backend.logical_pauli(
                        block, f.logical_id, f.logical_action, f.orientations_before[0])
                    evaluation_steps.append(("virtual", p))
            for boundary in step.after:
                bell = protocol.end(boundary, context, tracker, all_fragments)
                if bell is not None:
                    evaluation_steps.append(("teleport", bell))
        if not allow_open_outputs and any(
            status != BlockStatus.MEASURED for status in context.status.values()
        ):
            raise ValueError("A complete memory circuit must initialize and measure every block")
        frontier = compiler.cur_end_interface()
        # Export a partial artifact through public APIs. Its original verified
        # frontier is retained; this zero-operation export projection is never
        # used as a physical termination or as the start of a continuation.
        exporter = compiler.copy()
        if frontier.ports or frontier.discards:
            exporter.append(sf.Chunk(stim.Circuit(), flows=(),
                q2i={q: i for i, q in enumerate(sf.sorted_complex(frontier.used_set))},
                discarded_inputs=frontier.ports | frontier.discards))
        ideal = exporter.finish_circuit()
        # This checks deterministic detectors and observables independently of Chunk flows.
        ideal.detector_error_model()
        fragment_tuple = tuple(all_fragments)
        ideal, suppressed = separate_detector_regions(ideal, fragment_tuple)
        physical_map, observables = extract_metadata(ideal, context, fragment_tuple, self.backend)
        observables = finalize_observables(ideal, context, observables)
        validate_detector_regions(context.detectors, context.measurements)
        preparations, readouts = protocol_metadata(context, fragment_tuple, self.backend)
        bells = protocol.finalize(preparations, readouts)
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
            preparations, readouts, bells, tuple(protocol.relocations),
            tuple(protocol.composites), suppressed,
            {q: b for q, b in context.logical_to_block.items()
             if context.status[b] == BlockStatus.ACTIVE},
            frontier, tuple(evaluation_steps), self, program, noise_model,
        )
