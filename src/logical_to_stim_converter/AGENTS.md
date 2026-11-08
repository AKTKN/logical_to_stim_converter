# AGENTS.md — Python package root

The public memory/Clifford API is exported from `__init__.py`: code/layout/block models,
backend/context/fragment contracts, memory operations, H/CNOT/Pauli primitives, ordered operand contexts, affine frames,
compiler/artifact, and noise types. Stim/stimflow are pinned required dependencies. Surface-sim,
Hex, lomatching, and knill_bench must not be imported here. BellStatePrep, KnillEC, CompositeOperation, and PhysicalPauliFrame are public. Do not export future
placeholder operations until implemented with physics tests. Preserve the `src/`
layout and consult per-directory AGENTS/STATUS before changes.

M8-A adds language parse_ast/lex_source, frozen syntax nodes and located syntax
diagnostics. M8-B adds namespace-only LogicalProgram/parse_logical_circuit, static
validation, bounded unrolling and existing-operation/BindPatch lowering. compile
delegates with logical_to_block={} and returns the standard CompiledCircuit.
Syntax-only parsing still implies no semantic or physical validation. Physical
imports stay deferred until lowering/compilation. The root API stays unchanged;
the shipped Lark 1.3.1 grammar remains the syntax authority. M8-C owns root/file
API and formatter polish; M8-D owns full physical/noisy E2E certification.

M6-A exports global MeasurementInfo/MeasurementKey/DetectorInfo/ObservableInfo,
DetectorBoundaryCandidate, PreparationDependencyEvent, PreparationInfo,
LogicalReadout, BellMeasurementResult, and RelocationRecord at package level.
Keep principal compiled circuits complete and legacy stage separation explicit.

M6-B exports DecoderView, DetectorSelector, DEMOptions, GF2Map, RecordFlipMap,
make_decoder_view, observable_local_views and apply_record_flips. The decoding
namespace also exports input/mapping/audit/error types. Keep views independent of
private compiler state and physical correction selection.

M6-D adds CompiledCircuit.make_frame_plan and public decoding namespace types:
OfflineFramePlan/Batch, FrameBoundary, CorrectionBatch, StageInputs/Result/Decoder,
BoundaryRequest/ReadoutRequest/StageRequests, ConditionalReadoutModel/PauliFault,
and stage/conditional factories. Algorithms remain in examples; ideal boundary
probes remain model-only, and canonical raw records/noise stay unchanged.

M7-A exports BindPatch, BlockUseId, BlockUseInfo, PatchBindingEvent and UseOwnerEvent.
Bindings are compiler directives, separate from OperationModule. Physical-use
history and per-use measurement keys survive resource retirement/rebinding.
