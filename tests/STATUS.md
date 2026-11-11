# STATUS — Tests

## Independent golden memory (2026-11-11)

`test_validation_golden_memory.py` adds **49** tests covering all four d=3/5,
X/Z, three-round A/B/C1/C2 cases, exact complete signed record spaces, random
complementary first checks, data/check logical round flows, independent geometry
and CSS algebra, signed Bell-Y elimination, all shared elementary reset/readout
faults and inert terminal MR resets, frozen ideal fixtures, full causal noisy
schedules/counters/native DEMs and beginning/middle/end Pauli probes. Deliberate
gate/support/layer/logical/detector/reset/CX-noise/idle/result/TICK mutations,
metadata corruption, GF(2) multiplicity, source independence, read-only defaults
and private fixture maintenance have focused rejection checks. No runtime test
or existing validator was weakened.

The full eight-worker repository suite passes **1,446 in 472.92 s**, without
failures/skips/warnings. The final focused eight-worker run passes **49 in
27.72 s**; all four requested CLI runs and the complete eight-worker matrix
pass (24.045 s). Ruff src/tests/examples/validation passes. See the
[execution report](../validation/reports/golden_memory_2026-11-11/REPORT.md) for
final focused command and four per-case plus eight-worker matrix CLI evidence,
checksums and bounded certification limits.

## Research validation Phase 3 — M9 Knill faults (2026-11-09)

`test_validation_m9_knill.py` adds eight focused tests for exact d=3 18/54
M9 sites and 1,432/13,042 ranks, exclusive channel semantics, a hand-authored
Bell physical fault truth table, all single physical conditional maps and
selected pair GF(2) composition, stale/wrong-cut/duplicate-correction/omitted
byproduct negatives, source-bound causal stage inputs, synthetic low-noise
algebra including the `-(N-1)K1/3` term, binomial tail and fit behavior,
seed/worker rank invariance, and a capped quick CLI report. Focused tests pass
**8 in 34.93 s**. The selected eight-worker M9/frame/Knill regression passes
**275 in 317.58 s**. The full eight-worker repository suite passes
**1,397 in 722.79 s**; Ruff src/tests/validation passes.

## Research validation Phase 1 — code-capacity validator (2026-11-09)

`test_validation_code_capacity.py` adds eight focused tests: hand-authored d=3/5
supports and GF(2) parity; exact integer/polynomial/rational results; real
PyMatching versus independent minimum-syndrome classes and tie consistency;
exhaustive physical Stim response on 512/15,276 patterns; wrong-order/support/cut
negative controls, random preparation gauges, channel-component equivalence,
process task/worker seed identity, invalid and partial caps, zero-failure Wilson,
synthetic fits and quick CLI artifacts. Focused combined memory/layout/offline
decoding run: **97 passed in 67.62 s**. Full eight-worker suite: **1381 passed
in 602.93 s**, with two fork-in-multithread warnings from the initial validator
pool. Final explicit-spawn validator tests pass **8 in 9.30 s** under eight
workers, without warnings; this narrow pool change was not followed by another
full suite run. Ruff src/tests/validation passes.

## Phase 5 — Full integration verification (2026-11-09)

Fresh `.venv/bin/python -m pytest -n 8 --tb=short --durations=10`: **1373 passed
in 401.70 s**, eight workers, no failures/skips. This includes all M1–M9 signed
flow/physical/detector/noise/reuse/LSTIM/decoder-neutral regressions and the six
Phase 4 consumer cases plus extended shared-build wheel isolation path. No test
assertion, source file or dependency changes were needed. Ruff passes.

Separate fresh runtime-only built-wheel and uncached GitHub c45bf1f installations
validate all six ordinary/Knill/M9 CLI cases; metadata/direct-url/runtime-byte and
pip checks pass. The wheel also runs all 13 documented Python blocks, including
explicit context for specification fragments. Nine source workflow examples and
snapshot/CSV export reproduction pass. Exact remote CI SHA/jobs and final archive/
link audits are recorded separately in the Phase 5 ledger; no CI result for a
new local documentation commit is inferred. License selection remains pending.

## Phase 4 — Installed consumer contract (2026-11-09)

Extended test_lstim_packaging.py's existing private wheel/sdist build rather than
adding another build. It copies the public-only consumer and installed checks to
an external directory; the same wheel serves ordinary ideal/noisy and three-patch
ideal/ordinary/M9-only/M9-background cases. installed_consumer_checks.py blocks
optional/checkout imports, verifies installed module paths (including negative
leakage checks), current raw/reference/view ordering, seven uses/relocations,
M9 tags/targets/cuts/exclusive atoms and same-raw causal correction replay. Wrong
bindings, fingerprints, shapes, epochs, column order, duplicate application and
unsupported intermediate operand SE cuts fail explicitly. A previous-cycle
channel legitimately survives in a later physical prefix; probes exclude their
own post-SE channel, not all historical noise.

test_installed_consumer.py adds six independent cases: ordinary/Knill exact source
versus separately authored public-operation references, reused-epoch conditional
atom propagation with the existing Stim oracle, strict noiseless physical-frame
comparison, signed two-observable remapping/labels and once-only memory/Knill CLI
sampling. No oracle enters consumer inputs. The zero-noise test demands nonzero
random-gauge corrections, not assumed positive stabilizers.

`.venv/bin/python -m pytest -n 8 tests/test_installed_consumer.py
tests/test_lstim_packaging.py tests/test_lstim_api.py tests/test_epoch_stages_frames.py
tests/test_record_frames.py tests/test_resource_preparation_models.py
tests/test_resource_preparation_e2e.py --tb=short --durations=8`:
**117 passed in 146.14 s**. Ruff src/tests/examples and whitespace pass. A separate
fresh runtime-only wheel environment passes six CLI and two tutorial snippets;
source inputs/consumer/tut sources are audited in sdist. Full suite/all examples
and new platform CI are left to Phase 5, without weakening any existing physics
assertion. No installed runtime or dependency changes. See the Phase 4 ledger.

## Authorized beta/export integration — 2026-11-09

The combined 0.0.1/inspection-export tree passes the full existing suite:
`python -m pytest -n 8 --tb=short --durations=10`: **1367 passed in 384.11 s**.
Ruff src/tests/examples, whitespace and a private-source isolated wheel/sdist
build pass. A fresh runtime-only installed wheel validates memory and three-patch
LSTIM circuits, native DEMs, physical sampling and all three M9 conditional Bell
models. Optional/example/test/reference imports are blocked; pip check passes.
Runtime source and dependency pins are unchanged. This is local Linux/WSL2
Python 3.12 evidence, not a new remote matrix result or later beta phase.

## Research beta 0.0.1 — Phase 1 (2026-11-09)

The existing private-tree wheel/sdist test now checks matching 0.0.1 metadata,
unchanged distribution name/runtime requirements, Python requirement and absent
license assertions. Its isolated consumer also verifies the installed distribution
version/location before exercising the unchanged public LSTIM and M9 paths with
optional/repository imports blocked. Actual commands/results are recorded in
[the phase record](../docs/research_beta_0.0.1_plan_and_verification.md).
`PYTHONPATH=src python -m pytest -n 8 tests/test_lstim_packaging.py
tests/test_lstim_api.py --tb=short --durations=5`: 26 passed in 8.68 s. Ruff,
wheel/sdist build and a separate runtime-only fresh-venv compile/DEM/sample smoke
pass. Full integration and remote Phase 1 CI are deferred, not reported as run.

## M9 follow-up — 2026-11-09

Expanded policy negatives to both enabled states, including .7500000001/.9/1,
NaN/infinity/bools/strings/complex/containers. Exact boundary tests accept 0,
interior probabilities and .75 with native DEM/view construction and unchanged
physical gate arguments. Other noise channels still accept their unit range and
native DEM errors propagate. Direct API tests cover omission/explicit None,
resource-free (), verified nonempty plans, disabled contradictions, duplicates and
malformed container/element types, including early failure before noise setup.
The old p=1 fixture is replaced by .75; historical results below remain intact.
M9 physical, conditional and three-cycle same-raw LSTIM tests stay in place.
Checkpoint and full-suite/installed-wheel/build/example evidence is in root STATUS.


## M9 initial update — 2026-11-09 (historical pre-restriction)

Added 97 cases while preserving all 1205 M1-M8 cases: 40 policy/structural/exact
noise tests, 17 independent physical/model/provenance tests and 40 three-cycle
same-raw E2E cases. test_lstim_packaging.py also certifies opt-in compilation in a
real isolated wheel consumer with optional/repository imports blocked.

The location oracle enumerates every ordinary/special gate/result/idle target,
probability and layer, including positive overrides, spectators, unequal waiting,
concurrent Bell preparations, d=3/5, X/Z, rounds1/d, historical pre-restriction
p=0/1 and bare-init exclusion. The current policy rejects p=1.
A direct-Stim original-rule reference compares exact disabled circuits and DEMs.
Independent primitive ideal references and Stim physical X/Y/Z injections verify
raw/check/logical/survivor maps, exclusive groups and full global signatures;
recycled-epoch atom propagation is also checked at d=3/5. Preparation probes exclude
new faults, exact views retain them and corrupted/stale provenance is rejected.
Three-cycle independent Python/LSTIM sources cover signed X/Z, p_st0/.003/.017,
ordinary background0/.001 and disabled mode. Baseline/replacement external decoders
receive one shared raw batch with quantum execution prohibited; stage inputs,
corrections, record/physical frames, final labels/failure vectors/LER and chunked
replay agree. No arbitrary LER target is asserted. Root STATUS records checkpoint
commands/counts, final full-suite/build/examples and remote CI status separately.


## M8-D certification — 2026-11-08

Added 164 tests while retaining every one of the 1041 prior cases:

- test_lstim_physical_equivalence.py (98): 48 signed memory, four unequal
  parallel, four ordered/oriented H/CX, four Bell default/order, 32 Knill
  d=3/5 X/Z bits0/1 T=1/3 post0/1, four reuse/spectator and two open-output.
  Independent public constructors, exact ideal/noisy Stim objects/DEMs/public
  metadata/flows/epochs/frames/source views and same-seed/shared-raw arrays.
  Existing physical instruction/reset oracle counts every noise site exactly.
- test_lstim_simulation_e2e.py (38): 18 ordinary-memory and two-observable
  global/local MWPM checks, 16 three-cycle Knill baseline/replacement decoder
  cases, two 257-shot chunk/once-only-sampling checks and two independent
  encoded-reference/Bell/reset/classical-feedback physical proofs. Causal stage
  inputs, models/targets/windows, predictions, correction bits/use/column IDs,
  interpreted records, physical frames, failures/counts/LER match. Quantum
  execution is prohibited during replay; canonical/raw sources remain unchanged.
- test_lstim_safeguards.py (28): syntax/semantic limits/repeated resources,
  matched direct lifecycle/resource/overlap/layout/backend failures, corrupted
  signed H flow and stale-use/source correction rejection.

helpers/lstim_equivalence.py performs test-only exact structural comparison,
including CSR maps and signed recursive ChunkLoops (no text serialization);
helpers/lstim_programs.py independently authors text and direct three-patch
programs. Neither direct reference uses AST/lowering or legacy helper authoring.

D1 focused: 48/13.65 s, 4/3.94 s, 40/50.67 s, 6/28.76 s plus Ruff after each.
D2: 16/5.51 s and two independent observables/2.90 s. Final D3 Knill matrix:
16/56.30 s; chunk replay 2/6.82 s; independent physical probes 2/5.88 s;
existing d=3/5 M7 encoded-reference regression 2/33.45 s; safeguards 28/3.85 s.
Full `python -m pytest -n 8 --durations=10 --tb=short`: 1205 passed in 260.96 s.
The final test-only setup-order change passes the 16-case Knill rerun. Root
STATUS records exact commands and staged/install/example evidence. Production
code and all old physics assertions are unchanged. Scope is the documented
matrix and finite seeded batches, with honest restricted-decoder limitations.

Exact staged frontend: 600 passed in 144.32 s; Ruff, wheel/sdist/isolated
installed API and all eight CI examples pass. Root STATUS records commands.

## M8-C update — 2026-11-08

Added 83 cases while retaining all 958 previous regressions: 57 formatter, 25
public API/files and one combined wheel/sdist isolation check. Exact typed AST
signatures exclude only spans; independently authored operation/directive tuples
check all fields/control order/defaults/labels and nested logical barriers.
Malformed raw ASTs fail. API tests cover UTF-8/CRLF/Unicode paths, OS/encoding
causes/locations, readonly order/labels, budgets and independent repeated physical
compilation. The installed root consumer compiles both frozen sample files with
valid metadata/DEMs, labelled Knill composites/children, views/frame/stage APIs
and independent noise; all package modules must come from the wheel. Optional
and repository imports are actively blocked. Both packaging tests build privately
so pytest-xdist cannot race on setuptools artifacts; no physics assertion changes.

C1 57/1.47 s; C2 API+formatter 82/2.07 s; full API checkpoint 1040/125.01 s;
C3 packaging+lexer 53/6.87 s. Final `python -m pytest -n 8 --durations=10`:
1041 passed in 119.24 s. Exact staged frontend 436 passed in 14.87 s; staged
Ruff/build pass. pytest-xdist 3.8.0 supplies eight workers locally and in the
Ubuntu/Windows Python 3.11/3.12 matrix; actual local execution is Linux Python
3.12.7. Root STATUS records full commands and staged/archive/example evidence.
M8-D full noisy sample/decoder equivalence remains deferred.

## M8-B update — 2026-11-08

Added 190 tests while preserving all 768 M1–M8-A cases unchanged:

- test_lstim_semantics.py (117): declaration/version/distance/name/order checks,
  exact opcode arity/rounds, bool/int/enum option types and duplicates, labels,
  loop restrictions, budgets/depth/exact cost, manual AST defensive validation,
  source-aware diagnostics and no static geometry allocation/lifecycle copying.
- test_lstim_lowering.py (47): independently authored existing Python operation
  types/fields/defaults/labels, fixed patch/site definitions, explicit ordered
  BINDs, the three-cycle reuse schedule, distinct repeated objects, parallel/SE
  barriers, immutable source/operations and budget-before-allocation ordering.
- test_lstim_compile.py (26): real d=3/5 X/Z signed memory, unequal parallel
  rounds/H, Bell defaults, Knill default/pre-existing resources and full d=3
  three-cycle explicit bindings; exact ideal/noisy circuits, DEMs, canonical
  record/detector/observable/use/stage/ancestry metadata and actual signed flows
  against independently authored empty-mapping Python references. Tests retain
  compiler lifecycle/resource/overlap/geometry failure causes, standard open
  outputs/continuation and independent noise artifacts, including existing views
  and frame-plan APIs. No runtime decoder or physics assertions are altered.

B1: 117 passed in 0.20 s; B2: 47 passed in 0.22 s; B3: 26 passed in 11.76 s.
Combined focused command: `python -m pytest -q tests/test_lstim_semantics.py
tests/test_lstim_lowering.py tests/test_lstim_compile.py --durations=5`:
190 passed in 11.92 s. M8-A syntax plus semantics: 280 passed in 4.51 s, retaining
the isolated wheel grammar/import guard. Ruff src/tests/examples passes. Root
STATUS records actual full regression/build and final staged-source evidence.
Final `python -m pytest --durations=10`: **958 passed in 670.19 s**. The exact
staged export independently passes all **353 M8-A/B frontend cases in 16.41 s**,
lint and sdist/wheel builds. An isolated internal-namespace wheel consumer passes
physical Knill compilation with optional/example/reference imports blocked.
M8-C formatter/file/public-root APIs and M8-D complete noisy sample/decoder E2E
certification remain deferred.

## M8-A update — 2026-11-08

Added 163 syntax-only tests, preserving all 605 M1–M7-C tests unchanged:

- test_lstim_lexer.py: 52 cases cover contextual token types/values/positions,
  reserved words and prefixes, whitespace/comments/CRLF/EOF, malformed lexical
  boundaries and delimiters, conflict-free LALR construction, and isolated-wheel
  grammar loading with source paths removed and physical imports blocked.
- test_lstim_parser.py: 87 cases cover every primitive/composite, optional labels/
  rounds, typed ordered options, header/declarations/bindings, both exact contract
  programs, nested groups/repeats, immutable LF/CRLF-equal trees, exact source
  slices, structural errors and physical-opcode/expression rejection. Explicit
  syntax-only cases demonstrate that semantic checks are still deferred.
- test_lstim_diagnostics.py: 24 cases cover typed file/line/column/caret errors,
  CRLF/EOF and tab behavior, bounded long-line excerpts, source/token/integer/depth
  budgets including exact boundaries, iterative wide/deep ASTs without expansion,
  and deterministic syntax values under different Python hash seeds.

Checkpoint evidence: lexer **52 passed in 1.44 s**, parser **87 passed in 0.18 s**,
diagnostics **24 passed in 3.44 s**; combined **163 passed in 5.05 s**. Full
regression: **768 passed in 713.70 s**, including all 605 previous checks. The
exact staged-source syntax run passes **163 tests in 4.66 s**, with lint and
sdist/wheel builds also passing. Root STATUS records archive/import evidence.
No existing physics assertion is changed or weakened. M8-B/D
will test lowered operations against independently authored physical programs.

## M7-C update — 2026-11-08

Added 61 tests in test_patch_reuse_knill_e2e.py and
test_patch_reuse_offline_replay.py, retaining all 544 M1–M7-B checks, including
the 440 historic M6 tests. No runtime package or pre-existing test is modified.
The baseline is main 8fc65a9b808d31308878f8bd22d8d32ffa359a5d,
verified by all four Ubuntu/Windows Python 3.11/3.12 CI jobs (42470273846).

The new cases cover T=1..5 d=3 and T=1..3 d=5 X/Z physical occupancy, explicit
manual bindings, constant physical width and advancing uses; d=3/5 both input
signs under random gauges/all Bell branches, M5 replay, actual physical tableaux
and explicit Pauli execution; three-cycle untouched encoded-reference XX/ZZ;
exact global source parities/coordinates, all P0 epochs/local marginals and record
edits, use-aware temporal probes, exact gate/idle/reset/result noise and every
conditional Bell atom/exclusive group/survivor action against FlipSimulator;
fresh-use unfolded gate/noise sites and six selected deterministic fault locations
at both distances; independent noisy-stream 99.99% Wilson consistency; causal
boundary/readout use histories, decoder replacement with public inputs only,
immutable raw/DEM replay, exact chunk equivalence including stage predictions,
one sampler/one sample per batch and once-only corrections; wrong epoch/prep/
record/reset and missing-later-Bell negatives; honest nonzero noisy failure labels,
and ten-cycle bounded-batch/noiseless/report smoke. Exact commands/counts and
final lint/build/platform evidence are in root STATUS.
Focused command: `python -m pytest -q tests/test_patch_reuse_knill_e2e.py
tests/test_patch_reuse_offline_replay.py` -> **61 passed in 300.29 s**.
The temporal-only checkpoint passes four cases at d=3/5; first and last records
coincide for a one-round SE, unlike d-round preparations. The corrected test
derives this from actual record IDs. Historic physics assertions and runtime
source remain unchanged; root STATUS distinguishes the initial harness failures
from the final verified result.
Final `python -m pytest`: **605 passed in 669.37 s**, including all 544 prior
regressions and the 61 new cases. Full lint, seven examples, build and isolated
public-API wheel checks pass; remote CI results are reported after push.

## M7-B update — 2026-11-08

Added 51 tests across test_epoch_views_noise.py and test_epoch_stages_frames.py.
All 493 M1–M7-A checks remain. The schema assertion migrates from v2 to v3;
the missing-byproduct negative test now first rejects stale v3 requests, then
rebinds all models to the corrupted source and retains its original physical
failure assertion. No physics assertion is weakened.
Baseline: 493 passed in 474.32 s. New focused suite: 50 passed in 53.63 s.

At d=3/5 the tests independently verify three-use mixed X/Z signed memories,
global raw/annotation parity and use provenance; exact physical noise locations
through available/reserved gaps and re-entry, parallel operations/composites,
explicit zero/inheritance and no reinjection; strict/touching/anchor use views,
physical-block unions, isolated default locality and explicit order; physical
X/Y/Z/CX/reset/result fault marginals, excluded-region output effects, exact DEM
characteristic functions, hyperedges/correlated separators and precision/repeat/
SHIFT_COORDS snapshots; temporal early/late result targets for both P0 uses and
SE; source prep/orientation histories and actual H/CNOT signed sector transfer;
all Bell atoms/exclusive groups/survivor actions against Stim FlipSimulator in
two gadgets with recycled roles and an existing resource; reset extinction plus
surviving Bell feedback; bounded-batch M5 replay and actual physical corrections,
open outputs, H after relocation, two spectators and stale use/key/order/source/
support/shot rejection. Reference probes/fault truth remain test/model-only.

Retained checkpoints: view/ancestry 110 passed in 49.05 s; stage/strict-frame
33 passed in 39.77 s; final frame/record 27 passed in 26.08 s. Root STATUS records
the final full suite, lint/build/examples, isolated wheel and CI matrix.
Final `python -m pytest`: **544 passed in 568.60 s**. Final new tests plus the
retained missing-byproduct physical test: **52 passed in 57.19 s**.

## M7-A update — 2026-11-08

Added 53 tests in test_patch_reuse.py; all 440 prior tests are retained unchanged.
32 replay cases cover d=3/5, X/Z, both intended bits independently in each use,
and physical/virtual logical Paulis. They verify fixed qubit/site mappings, actual
data resets, per-use syndrome counters, all raw/global rec positions, independent
signed observables, exact noiseless parities, global ideal/noisy DEMs and repeat
determinism. Other cases cover immutable strict epoch identities, binding-only
zero time/noise, uninitialized/active/reserved/retired/unknown/conflicting aliases,
rejected cross-reset stabilizer flows, spectators/registration order, Knill owner
history plus fresh preparations/late-bound resources, 13 uses in one logical slot,
continued H/CNOT/random readout and corrupted measurement-key rejection.

Focused reuse plus prior Knill suite: 77 passed in 122.94 s. Incremental lifecycle
checkpoint: 21 passed in 5.62 s (32 replay cases separately passed). Baseline:
440 passed in 374.81 s. Root STATUS records final full tests, lint, build, examples
and supported platform matrix. No test oracle or decoder entered runtime code.
Final `python -m pytest`: **493 passed in 430.94 s**.

## M6-D update — 2026-11-08

Added 46 integration/physics tests (24 memory and 22 decoder-view tests), retaining
all 394 M1–M6-C tests. The memory suite covers d=3/5 X/Z, both input bits, T=1/2,
all four Bell branches, actual physical encoded-reference tableaux, open residual
frames against M5 replay, omitted byproduct failure, noisy replay/alternate
capacity weights/chunking, one sampling call, no oracle input and report timing.

Decoder-view tests cover strict stage/gauge partitions, shot-specific conditional
Bell sectors without preparation normalization, early/late measurement-noise
targets, every conditional Pauli atom against vectorized Stim FlipSimulator at
both distances, independent physical correction execution/current-event updates,
source/batch/double-application failures, actual H/CNOT/orientation and physical/
virtual Paulis, parallel independent gadgets/spectator isolation and immutable
stage contracts. Ten separately injected data/SE/resource-CX/Bell-CX/readout/post-SE/
logical faults compare actual physical global signatures with Stim's linear oracle;
an undetectable logical fault honestly yields failures.

The normal path never imports the M5 noiseless preparation helper or receives
hidden faults/tableaux. Full pytest, all six examples, isolated wheel and wall
results are recorded in root STATUS and e2etest/m6d_knill; no timing/LER threshold
is asserted and no raw samples/profiler binaries are committed.

## M6-C update — 2026-11-08

Added 24 tests in test_memory_offline_decoding.py plus two exact snapshot/source
identity regressions in test_decoder_views.py. All 368 prior tests are retained.
The memory tests cover d=3/5 X/Z R=d noiseless gauges and repeated seeds; signed
-1 inputs and physical/virtual Pauli interpretation; raw detector and observable
truth reconstruction independent of the adapter; noisy exact XOR failure counts
with independent d/R; one sampling call; immutable raw reuse; nontrivial mixed X/Z
patch/global observable order; chunk-independent decoding; registration-order
reproducibility; deterministic data/result fault signatures; hyperedge rejection
and supported correlated graphlike models; custom noise and report generation.

No stochastic LER target is asserted. Bounded integration tests use 64–512 shots
per batch; the separate requested figure uses 20,000 shots for each of five cases.
The precision tests emulate Windows DEM formatting, preserve tagged repeats,
shifts and ^ components, and catch source-fingerprint collisions caused by circuit
text rounding. Full-precision equality assertions remain unchanged. PyMatching
2.3.1 and Matplotlib are dev/example dependencies, never runtime decoder imports.
Root STATUS records final full pytest/lint/build/examples and platform evidence.

## M6-B update — 2026-11-08

Added 105 tests; all 263 M1–M6-A tests remain unchanged. test_decoder_views checks
d=3/5 memory and open/closed Knill identity DEMs, permuted/sparse/global-to-local
indices, one-batch semantic selections, strict/touching/anchor regions, cross-stage
policy/audit, signed reference conversion and record updates. It compares exact
DEM marginal parity expectations, physically enumerates selected faults, preserves
hyperedges/correlated ^ components, and checks independently seeded statistical
marginals. Public metadata hand circuits deliberately have no private compiler or
frame state. Negative indices, sources, missing metadata, check basis/support,
random observables, sample shapes and unsupported exact noise modes fail clearly.

test_record_frames checks immutable sparse/dense GF(2) maps (including uint8
overflow), empty dimensions, external correction maps against explicit physical
Pauli execution, once-only copy-based record updates, and malformed/source/shape
rejection. helpers/decoder_view_physics contains independent metadata/fault/parity
checks. The fourth example samples once for global/patch/observable-local views.
Root STATUS records final full test/lint/build/example and pinned API evidence.

## M6-A update — 2026-11-08

Added 42 tests; all 221 M1–M5 regressions are retained. Only the two explicit
Knill annotation-policy cases change their contract to canonical global detectors
and an explicit stage-separated derived view. Original M3 tests remain unchanged.

- test_causal_preparation_dependencies.py: spectator exclusion, parallel-gadget
  isolation and registration-order invariance, actual CNOT dependencies, d=3/5
  reference entanglement on physical tableaux, pre-existing resources, extra SE,
  repeated relocation, corrupted ancestry edges/snapshots, and correction-value
  isolation independently from metadata sources.
- test_global_detector_provenance.py: d=3/5 full detector recovery, independent
  Stim instruction parity/order reading, 256-shot raw parity reconstruction and
  m2d agreement, all random Bell branches, full ideal/noisy DEMs, unchanged physical
  instructions/noise locations/coordinates/records in the legacy view, explicit
  global/view detector mapping, open continuation, and negative index/stage tests.
- test_frame_validation_modes.py: strict noiseless equations/eigenvalue proof,
  a final check-result fault accepted as a hypothesis, actual noisy raw samples,
  deliberately wrong logical hypotheses, immutable samples/circuits, repeatable
  once-only replay, and malformed/unresolved/source/support/sign rejection.

Focused suite: 44 passed (including the two migrated boundary cases). Full final
test/lint/build/example evidence is recorded in root STATUS. No stochastic LER or
production decoding result is asserted.

## M5 update — 2026-11-07

Added 48 physics/metadata/noise tests; all 173 original tests are retained.
- test_knill_state_preparation.py: d=3/5 X/Z d-round preparation sectors across
  seeds; actual semantic histories/check order; gauge/temporal detectors; CSS
  equations and explicit corrected tableau checks; seven vector/matrix/order/
  mapping/orientation/omission failures.
- test_bell_state_preparation.py: d=3/5 default/overridden rounds, parallel timing,
  primitive-equivalent circuits, child/stage identity, physical corrected XX/ZZ,
  random singles, and separate explicit-correction simulation.
- test_knill_teleportation.py: four input states at both distances, all four Bell
  branches, explicit physical correction references, encoded reference-data
  entanglement, open export/continuation, H/SE/physical and virtual Paulis, all
  resource orientations, CNOT after relocation, other live patches, parallel
  composites, random readout/H timing, and wrong byproduct/orientation failures.
- test_knill_detector_boundaries.py: stage-local detector records, retained raw
  Bell checks, valid excluded global relations, boundary rejection, and ideal/
  noisy DEM construction.
- test_knill_noise.py: exact physical reset/result/gate/idle faults, two shared
  CNOTs, no duplicate/virtual faults, primitive equivalence, and seeded sampling.

helpers/preparation_matching.py imports PyMatching 2.3.1 unconditionally and
resolves final noiseless sectors only. helpers/knill_physics.py independently
probes physical tableaux and actually executes selected corrections on a separate
simulator. There is no temporal/circuit-level decoder or noisy recovery claim.
Root STATUS records exact final test/lint/build/example and CI evidence.

## M3 update — 2026-11-07

Final suite: **173 passed in 144.89 s**, including all 79 original memory tests.
Ruff, source/wheel build, both examples, and an isolated built-wheel Bell/frame/DEM
check passed. See root STATUS for commands and platform evidence.

- `test_clifford_backend.py`: all four CNOT orientation pairs at d=3/5; independent
  physical pair/support conventions; full check/logical flows; H-conjugated SE;
  H²/CNOT²; physical X/Y/Z action; wrong direction/pair/missing gate/orientation,
  required reflow, and corrupted generator-product failures.
- `test_clifford_compiler.py`: all CNOT logical basis truth-table inputs at d=3/5
  and every orientation pair, raw/affine readout signs, H then SE/H², virtual and
  physical Paulis, affine measurement-key rules, independent logical-tableau oracle
  comparisons for twelve random deterministic-output circuits, partial-readout/H
  concurrency, ordered/shared fragment identity, atomic failure, overlap/inactive
  rejection, and corrupted frame propagation caught by signed physical proof.
- `test_bell_roundtrip.py`: (d,R)=(3,1),(3,3),(5,1),(5,5), ideal/noisy DEMs, physical
  intermediate XX=ZZ=+1 and zero local X/Z expectation, raw final Z outcomes (0,0),
  exact correlated detector parities/provenance, reproducible noisy samples,
  CNOT-only correlated faults, and a syntactically valid corrupted record parity.
- `test_clifford_noise.py`: exact layer/channel/probability/target counts for mixed
  concurrent H/CNOT/Pauli operations, one shared CNOT provenance, once-only gate
  noise, idle on both participants, virtual zero time/noise, and zero-noise equality.

No decoder/LER, Knill, parser, or general Clifford/teleportation tests are claimed.
The Ubuntu/Windows Python 3.11/3.12 CI matrix is preserved and runs both examples.

## Prior memory test record

**2026-11-07: 79 tests passed in the local Python 3.12.7 environment.**

- `test_code_layout.py`: d=3/5 CSS ranks/commutation/logical pairing and immutability,
  invalid specifications, GF(2)-versus-real rank, N/Z direction/control/target,
  local mappings, counts, and explicit pinned-reference d=3 support fixture.
- `test_flows.py`: full signed check/both-logical flow counts, init/readout discarded
  boundaries, ChunkLoop composition, ideal DEM/sampling, and deliberately corrupted
  gate/record/sign verification failures.
- `test_memory.py`: d=3/5, one/two/three patches and X/Z/mixed bases, SE rounds 1/3/5,
  exact detector/observable raw parity, first/intermediate/terminal records, physical
  distance 3/5 in both bases (compared with Stim's built-in memory distance),
  lifecycle/frame/preparation syndrome, registration-order invariance, final-index
  reordering, collisions, unequal rounds, waiting and mixed-phase operation layers.
  Adding a random preparation-sector outcome as a detector is rejected by Stim.
- `test_noise.py`: exact fault channels/targets/probabilities, concurrent idle,
  reset/result errors, one-qubit upstream rule, type/instance replacement, waiting
  and retired blocks, zero-noise equality, no reinjection, metadata preservation,
  and seeded noisy smoke sampling without statistical thresholds.
- `test_scaffold.py`: retained package import smoke test, renamed to reflect the
  now-functional public memory API.

Executed: `python -m pytest` -> **79 passed in 33.48 s**;
`python -m ruff check src tests` -> **all checks passed**. Build and the two-patch
example also pass; see root STATUS for versions and complete evidence.

No decoder/LER benchmark, Clifford/teleportation-frame test, or other code-family
physics is implemented. CI is configured for Ubuntu/Windows Python 3.11/3.12;
remote jobs have not run during this task. No upstream tests or sources were edited.

History: initial import-only scaffold -> full memory-core physics suite on 2026-11-07.

# Phase 2 ordinary circuit research validator — 2026-11-09

`test_validation_ordinary_circuit.py` adds eight focused tests for exact
physical noise-location inventory, 3+15 categorical alternatives, batched
targets, measurement-result timing, complete selected d3/d5 single faults,
signed global parity, H/virtual/spectator controls, active/retired idles,
mutated gate/order/map/channel/sign controls, DEM `^` components and hyperedge
rejection, cross-location pair propagation, one-versus-two-worker determinism,
separate categorical sampling, zero noise, invalid settings, a quick CLI run,
Wilson intervals and a synthetic fit. Final eight-worker full-suite and Ruff
evidence: **1,389 passed in 553.55 s** for the full suite, and **191 passed
in 32.14 s** for the final targeted run including this test and the requested
noise, Clifford noise, memory, decoder-view and detector-provenance tests.
Ruff src/tests/validation and formatting pass. The full suite started before
the narrow spectator label, throughput and idle provenance edits; the final targeted
run exercised those edits.
