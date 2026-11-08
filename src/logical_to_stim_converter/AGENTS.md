# AGENTS.md — Python package root

The public memory/Clifford API is exported from `__init__.py`: code/layout/block models,
backend/context/fragment contracts, memory operations, H/CNOT/Pauli primitives, ordered operand contexts, affine frames,
compiler/artifact, and noise types. Stim/stimflow are pinned required dependencies. Surface-sim,
Hex, lomatching, and knill_bench must not be imported here. BellStatePrep, KnillEC, CompositeOperation, and PhysicalPauliFrame are public. Do not export future
placeholder operations until implemented with physics tests. Preserve the `src/`
layout and consult per-directory AGENTS/STATUS before changes.

M8-A adds language parse_ast/lex_source, frozen syntax nodes and located syntax
diagnostics. M8-B adds LogicalProgram/parse_logical_circuit, static
validation, bounded unrolling and existing-operation/BindPatch lowering. compile
delegates with logical_to_block={} and returns the standard CompiledCircuit.
Syntax-only parsing still implies no semantic or physical validation. Physical
imports stay deferred until lowering/compilation. M8-C exports LogicalProgram,
parse_logical_circuit/parse_logical_file/format_logical_circuit and typed errors
from root and language. The formatter statically validates and grammar-roundtrips
the unexpanded AST with exact typed semantic signatures. UTF-8 reads preserve
path/CRLF offsets and original file/encoding causes. The shipped Lark 1.3.1
grammar remains the syntax authority; installed wheel checks block optional and
repository imports. M8-D certifies the documented d=3/5 physical/noisy E2E matrix
against independent public-operation references and unchanged external decoder
adapters. No decoder or simulator enters the installed runtime. Match authored
bindings/labels for exact metadata/source identity; raw replay never resamples.

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
