# STATUS — Package root

## Parallel/deep Clifford API — 2026-11-11

Root exports signed logical product/probe types and PostInitializationNoise.
Existing public compilation/decoder/stage/frame APIs are reused. New artifact
fields expose intended active stabilizers and explicit init-noise cuts; methods
produce independent terminal sampling experiments and JSON metadata exports.
Focused 261-test eight-worker checkpoint passed; final evidence in root STATUS.


Final complete local gate: **1,664 passed in 1,035.32 s** with eight workers,
no failures/skips. Ruff and pip checks pass; exact packaging and CI attribution
are in docs/parallel_knill_deep_clifford.md and root STATUS. All eight runtime
CI jobs (Ubuntu/Windows, Python 3.11/3.12, Stim 1.15/1.16) pass tests, builds and
all eleven examples at b74df32; this final follow-up changes documentation only.

## Dependency guidance (2026-11-11)

Package AGENTS now distinguishes minimum Stim/Lark versions from the exact
stimflow source pin. No production Python, parser, circuit/noise/decoder/frame
algorithm or public API changes. See [the compatibility record](../../docs/dependency_compatibility.md).


## M9 follow-up — 2026-11-09

ResourcePreparationNoise now rejects p_st_transversal outside [0,.75] even when
disabled. Public NoiseInjector.apply requires an explicit boundary tuple when
enabled; None/omitted fails and () declares a resource-free plan. The compiler
continues supplying verified tuples, retains append policy inheritance, and
validates actual noisy circuits without a capped fallback. No public quantum,
LSTIM, scheduling, source schema or decoder model changed. See root STATUS for
checkpoints and final exact regression/build/example evidence.


## M9 update — 2026-11-09

Root and noise now export the frozen ResourcePreparationNoise policy. Default
compilation retains M1-M8 behavior; opt-in Bell resource initialization alone is
ideal and receives distinctly tagged data-only noise after SE. Compiled artifacts
retain immutable boundary/use/site/index provenance and append preserves the full
noise model. No language, physical gate/flow, code-family or decoder API is added.
Installed-wheel consumers compile the unchanged LSTIM source with the new option
while optional/repository imports are blocked. Exact local checkpoint, full-suite,
build, example and remote CI evidence is in root STATUS. The documented supported
matrix is d=3/5 signed X/Z, three-cycle P0/P1/P2 memory. See
../../docs/resource_preparation_noise.md for the full contract and explicit limits.


## M8-D certification — 2026-11-08

No installed Python/runtime APIs changed. Independent public-operation references
now certify the documented d=3/5 memory/Clifford/Bell/reuse/Knill physical matrix
and same-raw decoding through unchanged external adapters. Exact signed circuits,
DEMs/double probabilities, all public metadata, source identity, views, epochs,
causal models/frames and failure labels match. Replay cannot resample and commutes
with batch slicing. Physical tableaux/executed corrections and deterministic
fault/reset probes remain independent of decoder agreement. Root STATUS records
1205 tests in 260.96 s with eight workers (164 new), focused checkpoints, pins,
platforms and distribution/example evidence. Tests/adapter examples stay outside
the installed package; no new decoder/simulator/backend or quantum generator.

Exact staged frontend: 600 passed in 144.32 s; Ruff, wheel/sdist/isolated
installed API and all eight CI examples pass. Root STATUS records commands.

## M8-C update — 2026-11-08

Root/language expose LogicalProgram, text/file parsing, canonical formatting and
typed errors. UTF-8 errors retain causes/locations; readonly source/blocks/ops and
explicit source labels are preserved. Formatting validates and grammar-roundtrips
nested ASTs, comparing every typed semantic field except spans without unrolling
or physical allocation. Compiler/noise/decoder behavior and Python signatures are
unchanged. Private wheel/sdist builds and isolated root consumers verify packaged
grammar and both source samples with repository/optional imports blocked.
83 new tests plus all 958 old cases pass: 1041 in 119.24 s with pytest-xdist 3.8.0
and eight workers. Exact staged frontend: 436 in 14.87 s; Ruff and build pass.
Root STATUS records exact commands/platforms and deferred M8-D certification.

## M8-B update — 2026-11-08

The language namespace now exports immutable LogicalProgram/parse_logical_circuit
with static declaration/signature/option/name validation, pre-allocation repeat
budgets and exact existing-operation/BindPatch lowering. compile delegates once
with an empty initial mapping to the unchanged CircuitCompiler and returns its
standard artifact. Physical imports are deferred until lowering/compilation;
parse_ast/lex_source remain syntax-only and physically independent. Semantic
errors are located; compiler errors preserve cause/file without guessed lines.
190 focused checks pass, with independent Python-object and real physical/DEM/
metadata equivalence. Root/language/test ledgers record full-run evidence.
Full regression: 958 passed in 670.19 s, retaining all 768 previous checks.
Clean staged frontend: 353 passed in 16.41 s; lint, sdist/wheel build and an
isolated internal-namespace physical compile with optional imports blocked pass.
Root public exports and physical/core/operation/noise/decoding code are unchanged.
M8-C root/file APIs/formatter and M8-D full noisy E2E certification remain separate.

## M8-A update — 2026-11-08

Internal language/ now provides grammar-backed parse_ast/lex_source with frozen
source-aware syntax trees and typed bounded-input errors. Lark 1.3.1 is a pinned
runtime dependency; grammar.lark ships in wheel and sdist. Root physical exports
and all compiler/noise/decoder source remain unchanged. The syntax layer has no
physical/compiler imports. 163 focused syntax cases, lint, archive/resource and
isolated-wheel checks pass; root/language/test ledgers retain full-run evidence.
Full regression: 768 passed in 713.70 s, retaining all 605 M1–M7-C checks.
Semantic analysis/lowering/compile bridge remain M8-B; public API/formatter M8-C;
independent physical/DEM/sample equivalence M8-D. Parsing alone validates no
quantum state, resource lifecycle or executable operation sequence.

## M7-B update — 2026-11-08

Decoder-neutral reuse now carries explicit use provenance through detectors,
physical-time layers, causal preparation histories, views, temporal/readout/Bell
requests and software frames. DetectorSelector accepts use_ids/use_membership;
physical-block selection still spans all epochs. Observable locality connects
interacting uses rather than shared physical coordinates. Fingerprints migrate
intentionally to decoder-view-v3; regenerate v1/v2 cached views/plans. Existing
class exports remain valid; CorrectionBatch adds optional use/column labels.
Root/compiler/core/decoding/noise ledgers record exact independent verification.
M7-C LER demonstration, automatic allocation and production decoding remain separate.

## M7-A update — 2026-11-08

Public exports add BindPatch, BlockUseId, BlockUseInfo, PatchBindingEvent and
UseOwnerEvent. CompiledCircuit exports block_uses, binding_history and available
blocks alongside historical readouts/preparations/observables. Epoch-aware raw
keys and explicit use IDs distinguish repeated physical occupancies without new
physical qubits. See core/compiler ledgers and root STATUS for exact verification.
No automatic allocator, dependency change, runtime decoder or M7-B/C claim.

## M6-D update — 2026-11-08

CompiledCircuit.make_frame_plan now exports verified sparse batch physical-frame
propagation. The public decoding namespace adds typed stage requests, correction
hypotheses, model-only temporal boundary targets and conditional Bell fault actions.
No PyMatching/Matplotlib imports or mandatory dependencies enter runtime code.
The fixed-round Knill consumer, modular baseline, LER and exclusive phase wall
reports live in examples/. Strict noiseless frame proof remains separate from
noisy hypotheses. Root STATUS and decoding/compiler ledgers record limitations
and full verification. No upstream edit, block reuse or experiment framework.

## M6-C update — 2026-11-08

The public converter remains decoder-neutral. The ordinary-memory MWPM consumer
lives under examples/ with integration tests, aggregate reports and figures.
No PyMatching/Matplotlib imports or mandatory dependencies enter the package.
DecoderView schema v2 replaces lossy circuit/DEM text snapshots with exact
immutable public instruction tuples and full-precision source fingerprints.
See decoding/STATUS.md and root STATUS for precision regression and evidence.

## M6-B update — 2026-11-08

Public DecoderView/DetectorSelector/DEMOptions, GF2Map/RecordFlipMap, factories,
observable-local selections and record XOR transforms now expose decoder-neutral
offline inputs. Mapping/input/audit/error types and source_fingerprint are public
in decoding. Principal circuits remain complete and unchanged; every local DEM
is re-extracted from the same physical instructions/noise. Actual detector basis
and full underlying data support are public. No runtime decoder or runner added.
See README/architecture and root STATUS for tested contracts and limitations.

## M6-A update — 2026-11-08

Public exports now include global measurement/detector/observable metadata,
DetectorBoundaryCandidate, PreparationDependencyEvent, PreparationInfo,
LogicalReadout, BellMeasurementResult and RelocationRecord. Compiled artifacts
retain canonical full circuits, immutable semantic record mappings, causal
preparation histories, explicit legacy stage views and their global detector IDs.
Strict noiseless frame proof is separate from well-formed noisy hypothesis replay.
The read-only suppressed_detectors alias now identifies present boundary candidates.
Migration and exact verification are documented in README and root STATUS.
No runtime decoder or knill_bench dependency was added.

## M5 update — 2026-11-07

Public exports now include CompositeOperation, BellStatePrep, KnillEC, and
PhysicalPauliFrame. Existing memory/Clifford APIs are preserved. CompiledCircuit
exports preparations/readouts/Bell results, detector stages and excluded relations,
relocation history, current/open mappings, and open flow interfaces. External
physical corrections enter evaluate_frames; no production decoder is imported.
PyMatching 2.3.1 belongs only to the development extra and required CI tests.
See root STATUS for exact executed verification and remaining limits.

**2026-11-07:** The top-level public memory/Clifford API exports CodeSpec, PhysicalLayout,
LogicalBlock, CodeBackend, CompilerContext, ModuleFragment,
RotatedSurfaceCodeBackend, OperationModule, LogicalInit, SyndromeExtraction,
LogicalMeasure, CircuitCompiler, CompiledCircuit, NoiseModel, NoiseParameters,
NoiseOverride, NoiseInjector, TransversalH, TransversalCNOT, LogicalPauli,
OperationContext, PauliFrame, and ParityExpression.

Required pinned dependencies are Stim 1.15.0 and stimflow at Stim commit
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. There are no machine-specific paths
or imports from external source copies. Surface-sim, Hex, lomatching, and
knill_bench are not runtime dependencies.

Evidence and limitations are recorded in root STATUS and per-component ledgers.
Dedicated Bell/Knill, other code-family, and decoder modules remain placeholders. History:
initially a docstring-only scaffold on 2026-11-07; memory-core task introduces the
first physics API and its tests. No general-purpose logical compiler is claimed.

M3 validation: 173-test extended suite plus Ruff/build/example checks recorded in
root STATUS. Logical Cliffords are H/CNOT/Pauli only; no broader API is claimed.
