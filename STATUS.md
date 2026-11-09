# STATUS — Repository-wide development ledger

**As of:** 2026-11-09
**Package:** `logical_to_stim_converter`  
**Overall state:** `M9_CERTIFIED` (bounded opt-in physical and same-raw matrix)

## M9 Bell-resource preparation noise — 2026-11-09

Baseline main d2f88ca4b13b3dfecee05f6cc7642f5ac4bc00bb. Existing uncommitted
inspection/export documentation, examples, snapshots and report deletions are
preserved outside this change. Pinned Stim 1.15.0/stimflow 1.17.dev0 at ffe0d043
remain unchanged; inspected installed tagged CircuitInstruction, NoiseModel/
NoiseRule, physical TICK/measurement and FlipSimulator APIs before integration.
Local environment is Linux/WSL2 Python 3.12.7, pytest 9.2.0/xdist 3.8.0, Ruff
0.17.4, NumPy 2.5.4, SciPy 1.18.1, Lark 1.3.1, PyMatching 2.3.1, build 1.6.1.

Implemented ResourcePreparationNoise(enabled=False, p_st_transversal=0) with
strict bool/probability/type validation, exported at root/noise. An enabled policy
suppresses every ordinary gate/result/idle channel only on the two structurally
owned BellStatePrep LogicalInit modules and their actual inclusive reset/final-SE
use intervals, overriding inherited positive settings. D and spectators remain
noisy. Outside these intervals all original rules and waiting idles resume.
Each resource then receives independent physical DEPOLARIZE1(p) on its layout
data sites once, after final idle accounting/existing TICK and before resource
CNOT. Zero probability still suppresses prep noise. Ideal circuits, signed flows,
random sectors, records/annotations/TICKs, frames and physical indices are unchanged.

noise/resource_preparation.py resolves explicit composite/fragment/preparation/use
relationships into immutable per-patch boundaries; detects missing/ambiguous uses,
duplicate sites/epochs and unsafe cuts; and validates distinct stochastic tags and
exact noisy instruction indices. CompiledCircuit retains these cuts and the noise
policy on append. No stage/name/geometry heuristics or new LSTIM syntax. Both nested
and explicit/separately consumed Bell resources work; bare init pairs are excluded.
Three-cycle d=3 memory has 54 stochastic targets (d=5:150) over six distinct uses.

ConditionalReadoutModel starts at its two exact post-SE channels and retains the
old readout end, categorical exclusive atoms and joint raw/check/logical/survivor
actions. Preparation model-only probes remain before the channels, so they are not
counted twice. Views preserve all physical instructions and exact marginal DEMs.
Enabled source metadata includes resource_preparation_v1 boundaries; disabled v3
fingerprints/circuits/models remain compatible. Public validation rejects damaged
cut/site/index/use metadata and stale source corrections.

Verified limitations: pinned Stim samples the full [0,1] probability range but
cannot exactly factor over-mixing DEPOLARIZE1(p>3/4) into a DEM. Such compilation
retains the actual circuit for sampling, checks remaining channels with only the
specific post-SE channels capped at .75 in a temporary copy, and leaves native
DEM/view failures explicit. No approximate canonical model. Enabled nonzero
conditional windows crossing an intermediate SE/preparation measurement on a Bell
operand fail explicitly: an additional temporal-sector hypothesis is required.
Delays containing gates/idles work and their faults are retained. Canonical
circuits/global DEMs remain available for unsupported conditional intervals.
General cross-boundary inference and production decoder algorithms stay deferred.

### Checkpoint evidence

All pytest commands below use eight pytest-xdist workers. Initial test-harness
path/API mistakes were corrected; no tests were skipped or physics assertions
weakened. The p=1 test exposed the documented pinned DEM limitation; a delayed
operand-SE fault test exposed the need for explicit unsupported-window rejection.

- A: `.venv/bin/python -m pytest -q -n 8 tests/test_resource_preparation_noise.py
  tests/test_noise.py tests/test_knill_noise.py tests/test_patch_reuse.py
  tests/test_global_detector_provenance.py --tb=short`: **109 passed, 27.55 s**.
  `.venv/bin/python -m ruff check src tests` passes.
- B: `.venv/bin/python -m pytest -q -n 8 tests/test_resource_preparation_noise.py
  tests/test_noise.py tests/test_knill_noise.py tests/test_epoch_views_noise.py
  --tb=short`: **80 passed, 22.39 s**. Exact nonuniform gate/result/idle/channel
  counts at d=3/5, X/Z, rounds1/d, positive overrides, waiting D/spectators,
  unequal parallel work, simultaneous Bell preparations, zero and p=1 sampling.
- C: `.venv/bin/python -m pytest -q -n 8 tests/test_resource_preparation_models.py
  tests/test_resource_preparation_noise.py tests/test_epoch_stages_frames.py
  --tb=short`: **73 passed, 24.87 s**. Every new X/Y/Z atom at every d=3/5 data
  site is injected into independently authored ideal physical primitives and
  checked with Stim FlipSimulator. Raw/check/logical/survivor maps and exclusive
  groups match; independent deterministic physical faults match full canonical
  detector/observable signatures. Exact full-precision view marginals, prep-probe
  exclusion, reversed/delayed explicit resources and corrupt boundary rejection.
- D: `.venv/bin/python -m pytest -q -n 8 tests/test_resource_preparation_e2e.py
  --tb=short --durations=5 --maxfail=1`: **40 passed, 128.28 s**. Three P0/P1/P2
  cycles, d=3/5, X/Z, bits0/1, p_st=0/.003/.017, zero/.001 background and disabled
  mode. Exact independently authored direct/source circuits, DEMs, metadata,
  histories, channel locations, views/plans/requests/source identity and same-seed
  raw batches match. Shared-raw baseline/replacement adapters match causal events,
  predictions, CorrectionBatch identities, record/physical frames, logical bits,
  failure vectors/counts/LER and chunked replay; quantum execution is prohibited
  during replay. No numerical LER target or decoder optimality claim.
- E focused: `.venv/bin/python -m pytest -q -n 8
  tests/test_resource_preparation_noise.py tests/test_resource_preparation_models.py
  tests/test_lstim_packaging.py --tb=short`: **56 passed, 13.18 s**. This includes
  independent direct-Stim original-rule exact disabled circuit/DEM references and
  a real isolated wheel consumer compiling M9 with optional/repository imports
  blocked. `.venv/bin/python -m ruff check src tests examples` passes. New paired
  example --shots8 --p.001 --p-st.003 passes (51 wires/255 records/192 detectors,
  54 new target locations); finite eight-shot zero failures are not an LER target.

### Final staged verification

An exact index export (tree 92fcf4e64b95eaa71142f9a67b2ca27a71aa9f34) excludes
all pre-existing user changes. `PYTHONPATH=src python -m pytest -n 8 --tb=short
--durations=10` there passes **1302 tests in 417.77 s**, retaining all 1205 M1-M8
cases and adding 97 M9 cases. The final runtime/test bytes match this export;
subsequent changes only complete these documentation ledgers. The additional
recycled-epoch fault checkpoint (`test_resource_preparation_models.py -k recycled
-n 8 --tb=short`) passes **2 tests in 19.85 s** at d=3/5.

The export's `python -m ruff check src tests examples` passes, and `python -m build
--outdir /tmp/m9-dist` builds wheel and sdist. The full suite includes the genuine
isolated-wheel M9 consumer and private parallel-safe builds. `python -m pip check`,
working/index whitespace checks and exact final code-byte comparison pass.
All nine workflow example commands pass from the export:

- `python examples/two_patch_memory.py`
- `python examples/two_patch_bell_roundtrip.py`
- `python examples/knill_ec_single_round.py`
- `python examples/offline_dem_views.py`
- `python examples/memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731`
- `python examples/knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732`
- `python examples/knill_memory_three_patch_reuse.py --suite --shots 32 --batch-size 13
  --p 0.001 --seed 733`
- `python examples/lstim_equivalence.py --shots 32 --p 0.001 --seed 826`
- `python examples/knill_resource_preparation_noise.py --shots 32 --p 0.001 --p-st 0.003`

The new seed929 finite batch reports two restricted-baseline failures / 32 shots
(LER .0625), 54 post-SE target locations and exact direct/source equality. This
observation is not a numerical target or decoder optimality statement.
Verified behavior is the documented bounded physical/simulation matrix. There is
no claimed unverified runtime feature; the explicit unsupported intervals and
sampling-only over-mixing case above are limitations, not silently implemented
capabilities. General intermediate-sector conditional inference remains deferred.

Ubuntu/Windows Python 3.11/3.12 CI includes the same full suite, build, existing
eight examples and new opt-in example. Remote CI runs on push; its observed result is reported separately from local
Linux evidence. No local Windows or Python 3.11 execution is claimed.

## M8-D independent physical and simulation certification — 2026-11-08

Baseline main f1c33428855860811d80d59d8cafd93586f361da (M8-C, 1041 tests).
All four baseline Ubuntu/Windows Python 3.11/3.12 jobs passed in run 42487453839.
Pre-existing physical-inspection/export changes and report deletions are preserved
outside this commit. No production Python, grammar, compiler/backend/operations,
noise, decoder or external_lib code changed. This milestone adds certification,
an external paired-source example and documentation; it adds no simulator,
sampler, scheduling/allocation logic, runtime decoder or language CLI.

Test-only helpers/lstim_equivalence.py compares exact Stim ideal/noisy circuits,
canonical DEMs/double probabilities, every public CompiledCircuit field, signed
chunk/reflow/loop content, physical/record/detector/observable/time/use mappings,
reset/terminal/binding/relocation histories, preparation ancestry and composite
children. Both artifacts validate metadata and flows. Independent samplers with
identical explicit seeds match raw records/m2d arrays. Shared-raw DecoderViews
match snapshots, source fingerprints, parities and global/local maps. Only exact
ordinary-memory models request graphlike DEM decomposition. No approximate text
serialization is used for equality or identity.

Reference objects use independent public constructors and placed CodeSpecs with
explicit initial/later BindPatch directives and logical_to_block={}. They never
inspect AST/lowering output or call the parser/legacy runner to author operations.
helpers/lstim_programs.py separately writes the fixed three-cycle text and direct
operation sequences. Source comments/filenames are absent from physical identity;
labels/bindings are intentionally matched metadata. Legacy M7 implicit-reservation
helpers remain separate physical/statistical regression references, with no forced
fingerprint or seeded-record equality across different experiments.

New physical cases cover d=3/5 X/Z memory, initialization 1/d rounds, additional
SE and two separate repeated SE(1) barriers, physical/frame/absent Paulis, ideal/
nonuniform noise, unequal parallel SE/H/readout and exact independently counted
idle/gate noise. H/CNOT orientation/order and Bell resource defaults are checked.
Knill covers d=3/5, X/Z, bits 0/1, T=1/3, post-SE=0/1; width is exactly 51/147
qubits with 3/7 uses, ending at P0/epoch2 after three teleports. Independent
Z/X patch epochs, an active spectator, epoch-local observables and open outputs
retain historical records without fake termination or stale physical frames.

E2E uses unchanged external analyze_memory and prepare_compiled/analyze_knill.
Noiseless/nonzero-noise shared batches yield identical local/canonical models,
ordered stage inputs, temporal/sector predictions, CorrectionBatch bits/use/
column IDs, interpreted records, physical X/Z frames, logical outputs, failure
vectors, counts and LER. Both baseline and existing M7 replacement adapters run.
257 shots as one batch or 13/134/110 slices give exactly equal results and causal
stage inputs. A spy asserts one static sampler/sample call; replay prohibits
samplers/TableauSimulator/FlipSimulator. Raw samples and canonical DEMs remain
unchanged. Model/conditional-fault setup precedes batch sampling.

Independent tableau/actual-Pauli proofs preserve an untouched encoded reference
through all Bell branches. Injected physical faults before/after a real reset
prove support extinction; changing historical Bell feedback changes the surviving
logical state after later reuse. Existing d=3/5 M7 encoded-reference proofs are
mandatory regressions. Safeguards compare direct/source lifecycle/resource/overlap/
layout/mixed-distance CX errors and deliberately corrupted signed H flows, plus
stale-use/source correction rejection. No runtime failure was found or bypassed.

### M8-D checkpoints

Actual local environment: Linux/WSL2 Python 3.12.7, Stim 1.15.0, stimflow 1.17.dev0
at ffe0d043, Lark 1.3.1, PyMatching 2.3.1, NumPy 2.5.4, SciPy 1.18.1, pytest 9.2.0,
pytest-xdist 3.8.0, Ruff 0.17.4 and build 1.6.1. Pinned APIs were inspected before
integration, including Chunk/ChunkLoop/Reflow equality, actual compiler fields,
views/stage/frame/conditional interfaces and external adapters. ChunkLoop lacks
structural equality and is compared recursively; CSR maps compare exactly rather
than using ambiguous array truth. That initial comparison-harness failure was
fixed without changing production code or weakening a physics assertion.

- D1: `python -m pytest -q -n 8 tests/test_lstim_physical_equivalence.py
  -k single_patch --durations=3 --tb=short`: **48 passed in 13.65 s**.
  `-k parallel`: **4 passed in 3.94 s**. `-k 'cnot or bell or knill'`:
  **40 passed in 50.67 s**. `-k 'reuse_independent or open_knill'`:
  **6 passed in 28.76 s**. Ruff src/tests/examples passes at each checkpoint.
- D2: `python -m pytest -q -n 8 tests/test_lstim_simulation_e2e.py
  -k ordinary_memory --tb=short --durations=3`: **16 passed in 5.51 s**.
  Additional `-k independent_observables`: **2 passed in 2.90 s**, including
  alphabetical logical-output ordering different from physical/source order.
- D3: targeted X-basis Knill family: **8 passed in 40.99 s**. All basis/distance/
  sign/noise Knill cases pass after final model-before-sampling ordering:
  `python -m pytest -q -n 8 tests/test_lstim_simulation_e2e.py -k three_patch
  --tb=short --durations=3`: **16 passed in 56.30 s**.
  `-k 257`: **2 passed in 6.82 s**. `-k 'encoded_reference or reset_extinguishes'`:
  **2 passed in 5.88 s**. The existing M7-C `test_patch_reuse_knill_e2e.py
  -k encoded_reference` checkpoint: **2 passed in 33.45 s** (d=3/5).
  `test_lstim_safeguards.py`: **28 passed in 3.85 s**. All use -n 8.
- Full regression: `python -m pytest -n 8 --durations=10 --tb=short`:
  **1205 passed in 260.96 s**, preserving all 1041 M1–M8-C tests and adding 164
  (98 physical, 38 simulation E2E, 28 safeguard). The final ordering-only test
  change was independently rerun as the 16-case Knill checkpoint above. The
  slowest paired noisy d=5 Knill cases took 45.54 s under parallel load; model/
  compile setup dominates these small-shot experiments. No timing threshold.

- D4 exact staged export: `PYTHONPATH=src python -m pytest -q -n 8
  --durations=5 tests/test_lstim_*.py`: **600 passed in 144.32 s**, including
  every M8-A/B/C test and the final M8-D test/adapter setup. Its `python -m ruff
  check src tests examples` and `python -m build --outdir
  /tmp/lstim-m8d-verification/dist` pass. The existing genuine isolated-wheel test
  builds wheel from sdist, removes source paths and blocks tests/examples/
  reference/optional decoder/plot imports; both frozen sources parse/compile
  through installed root APIs with valid metadata/DEMs, views/frame/stage APIs,
  exact use/label history and independent noise. All runtime .py/.lark bytes,
  both archives' grammar and sdist sample files match staged source.
- All eight CI example commands pass from that clean staged export:
  `python examples/two_patch_memory.py`,
  `python examples/two_patch_bell_roundtrip.py`,
  `python examples/knill_ec_single_round.py`,
  `python examples/offline_dem_views.py`,
  `python examples/memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731`,
  `python examples/knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732`,
  `python examples/knill_memory_three_patch_reuse.py --suite --shots 32
  --batch-size 13 --p 0.001 --seed 733`, and
  `python examples/lstim_equivalence.py --shots 32 --p 0.001 --seed 826`.
  The seven old Python examples match HEAD, excluding unrelated user edits.
  `python -m pip check`, Ruff and diff whitespace checks pass. No sampled data,
  build products or reference source enter the commit. Final ledger-only changes
  preserve the exact tested code/test bytes.

The new examples/lstim_equivalence.py pairs both unchanged frozen sample files
with fully written direct references and unchanged external decoders. Local
`python examples/lstim_equivalence.py --shots 32 --p 0.001 --seed 826` passes:
ordinary memory = 17 wires/49 records/40 detectors/1 observable/492 DEM errors,
zero failures across global/observable/strict views; three-cycle Knill = 51 wires/
255 records/192 detectors/1 observable/2698 DEM errors, seven uses, four restricted
baseline failures (LER .125). These are finite observations, not asserted LER
targets or threshold/optimality claims. docs/lstim_certification.md contains paired
source/reference links, the full matrix and honest restrictions. The new example
is the eighth command in the Ubuntu/Windows Python 3.11/3.12 CI matrix.

Verified scope: exact physical/provenance and same-raw offline equivalence for the
explicit matrix, with independent physical branch/reset/fault evidence. No new
unverified runtime functionality. Remaining: resource-creating/labelled REPEAT,
automatic patch allocation, runtime conditionals, arbitrary backend/code plugins,
non-Clifford support, text-defined noise/decoders and a language CLI. Physical width
is bounded; circuit/record/history/model size and setup time grow with cycles.

## M8-C public LSTIM API, canonical formatting and packaging — 2026-11-08

Baseline: main b4fd36263812259ae7201c7aef47975d5535b2d2 (M8-B, 958 tests).
Pre-existing inspection/export edits and report deletions are preserved outside
this commit. Physical compiler/core/operations/noise/decoder and external_lib
sources are unchanged; direct Python operation APIs retain their signatures.

Root and language now export LogicalProgram, parse_logical_circuit,
parse_logical_file, format_logical_circuit and five typed error classes.
Strict UTF-8 file parsing retains path, original CRLF/code-point offsets and
source-label spans without compiling/sampling. LSTIMFileError retains OS/encoding
exceptions as original_error and __cause__; invalid UTF-8 locates the first bad
byte and corresponding line/character column after the valid prefix. Existing
syntax/semantic/compiler error categories and compiler cause behavior remain.

The formatter consumes LogicalProgram/FileNode and preserves source declarations,
indices, ordered bindings/targets/options, explicit rounds/labels/defaults and
nested REPEAT/PARALLEL. It uses four spaces, lowercase booleans, LF and one final
newline, dropping comments/blank lines. Raw ASTs undergo static validation; a
same-grammar reparse and exact immutable typed signature compare every field
except SourceSpan, rejecting malformed names/containers or semantic mutation.
There is no physical allocation/compile or repeat expansion in formatting.
Programs retain caller-validated larger operation budgets; raw ASTs use the
normal default. Explicit labels remain source lookups and real composite/child
IDs; no implicit-module-ID planner was added.

Both exact contract samples now live under examples/lstim/ and ship in sdist;
.lstim Git attributes enforce LF across platforms. grammar.lark remains runtime
package data in wheel/sdist, loaded through importlib.resources with Lark 1.3.1.
The new packaging test builds wheel from sdist in a private source tree, extracts
it and runs an isolated subprocess away from checkout. It blocks tests/examples/
reference clones/PyMatching/Matplotlib/knill_bench imports and checks every loaded
converter module came from the wheel. Both source samples compile through root
APIs (17/51 physical qubits), with valid canonical metadata/DEMs, explicit Knill
labels, standard views/frame/stage requests and independent noise artifacts.
The prior syntax-only wheel regression retains its physical-import blocker and
now also builds privately, avoiding shared setuptools output under xdist.

pytest-xdist 3.8.0 is a pinned dev dependency (inspected installed plugin CLI and
Python >=3.9 metadata). Local/CI test commands use eight workers. Stim 1.15.0,
stimflow 1.17.dev0 at ffe0d043 and runtime Lark 1.3.1 remain unchanged. No upstream
code was copied or changed. README, language guide/contract, architecture,
future-feature/development notes and affected instructions describe current APIs,
physical identities/epochs/stages/rounds/resources and deferred features.

### M8-C verification

Local environment: Linux/WSL2 Python 3.12.7, pytest 9.2.0, pytest-xdist 3.8.0,
Ruff 0.17.4, build 1.6.1, setuptools 84.2.1, wheel 0.48.0. These are actual local
versions, not evidence of a Windows/Python 3.11 execution. The existing Actions
Ubuntu/Windows x Python 3.11/3.12 matrix runs the same installed-wheel regression
and all examples with eight workers; remote results are separate from local ones.

- C1: `python -m pytest -q -n 8 tests/test_lstim_formatter.py`:
  **57 passed in 1.47 s**, then Ruff src/tests passes. Every opcode, explicit
  labels/options/defaults/control order, declarations, comments/CRLF, nested
  groups, source binding barriers and negative manually built ASTs are covered.
  Round trips compare all typed AST fields and independently authored exact
  existing OperationModule/BindPatch tuples. No physical compilation is used.
- C2: `python -m pytest -q -n 8 tests/test_lstim_api.py
  tests/test_lstim_formatter.py`: **82 passed in 2.07 s**. Root/subpackage exports,
  UTF-8 Unicode paths/CRLF, missing/directory/denied/encoding files, located syntax/
  semantic diagnostics, original causes, operation budgets, source-order/read-only
  views and independent repeated physical/noise compilation are checked.
  Full API checkpoint: **1040 passed in 125.01 s** with eight workers.
- C3: `python -m pytest -q -n 8 tests/test_lstim_packaging.py
  tests/test_lstim_lexer.py`: **53 passed in 6.87 s**, including both isolated
  wheel regressions. Early harness failures were corrected: expected labelled
  operations use the existing custom constructors; the wheel consumer retains
  installed dependency paths and checks the actual third teleport destination
  P0. No physics assertions or runtime compiler were weakened.
- C4: `python -m pytest -n 8 --durations=10`:
  **1041 passed in 119.24 s**, retaining all 958 previous tests and adding 83.
  The slowest d=5 encoded-reference three-teleport regression took 42.12 s under
  parallel load. Previous M8-B sequential full run was 670.19 s (958 tests);
  timings are observations, not performance thresholds.
- Exact staged export: all nine frontend modules pass **436 tests in 14.87 s**
  with `python -m pytest -q -n 8 --durations=5 tests/test_lstim_*.py`.
  Its `python -m ruff check src tests examples` and `python -m build` pass;
  the latter independently produces wheel and sdist. Packaging tests compare
  every runtime .py/.lark byte against the staged source, exact grammar bytes
  in both archives, Lark runtime metadata, and both source samples in sdist.
- Working-tree `python -m ruff check src tests examples`, `python -m build
  --outdir /tmp/lstim-m8c-dist`, `python -m pip check` and `git diff --check`
  pass. README/guide snippets compile to 17 qubits/40 detectors.

- All seven GitHub CI example commands pass from the exact staged export:
  `python examples/two_patch_memory.py`,
  `python examples/two_patch_bell_roundtrip.py`,
  `python examples/knill_ec_single_round.py`,
  `python examples/offline_dem_views.py`,
  `python examples/memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731`,
  `python examples/knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732`,
  `python examples/knill_memory_three_patch_reuse.py --suite --shots 32
  --batch-size 13 --p 0.001 --seed 733`. The Python example source matches HEAD;
  unrelated inspection/export edits are excluded. No stored raw samples/artifacts
  enter the commit. Final ledger-only changes leave the tested runtime/tests exact.

Verified: the public installed text/file/format/compile interface, semantic
formatting, source diagnostics/labels, distribution resources and existing physics
regressions. No new unverified physical implementation is introduced. Full noisy
sample/decoder E2E equivalence remains M8-D; CLI, automatic allocation, runtime
branching, text noise/decoder DSL and additional code families remain deferred.

## M8-B static semantics, lowering and compiler bridge — 2026-11-08

Baseline: main `0370baf7623791bbf473ac31aec71b5174e86d7e` (M8-A, 768 tests).
Pre-existing inspection/export changes and report deletions are preserved and
excluded from this commit. No physical compiler/core/operation/noise/decoder or
external_lib source changes. Dependencies and the M8-A grammar remain unchanged.

New language/semantics.py validates FORMAT(1), declaration order, odd distance
>=3, unique code/patch/index names, preceding aliases and BIND-introduced handles,
exact opcode signatures, rounds, typed/legal/unique options and source labels.
It tracks name existence only, without a physical occupancy or tableau model.
Repeated bodies allow unlabelled SE/H/CX/X/Y/Z, nested repeats and primitive
parallel groups. PARALLEL requires >=2 primitives and REPEAT a nonempty body.
Static cost counts each existing operation/BindPatch and parallel member, guards
repeat multiplication/sums before materialization, and defaults to 100,000
occurrences (configurable positive max_operations), within M8-A's 64-block bound.
All checks finish before code/patch construction or repeat expansion.

language/lowering.py uses the actual CodeSpec.rotated_surface/LogicalBlock.placed
factories and existing frozen LogicalInit, SyndromeExtraction, TransversalH/CNOT,
LogicalPauli, LogicalMeasure, BellStatePrep, KnillEC and BindPatch constructors.
Target/control order, defaults, source labels and zero-duration reservations are
preserved. Each repeated occurrence is a fresh object/barrier; parallel groups
remain ordered tuples and separate SE(1)s never become SE(N).

language/program.py exports namespace-only LogicalProgram/parse_logical_circuit.
Source/AST, declared blocks, operations, aligned operation_spans and label_spans
are immutable and inspectable without physical compilation. compile delegates
once to CircuitCompiler(blocks, logical_to_block={}), then its existing compile
method with the requested noise/open-output flags. Return type is unchanged
CompiledCircuit. Physical imports are deferred so the M8-A syntax-only wheel
regression remains valid. The package-root API remains unchanged.

LSTIMError unifies source errors while preserving every M8-A syntax class and
diagnostic. LSTIMSemanticError has precise statement/option spans and excerpts;
LSTIMCompileError preserves original_error and __cause__. Existing compiler
exceptions expose no reliable source statement marker; the bridge reports the
known file with span/line/column=None instead of guessing implicit module IDs.
Explicit labels survive in existing fragment operation_id/composite_ids and
CompositeInfo, with source spans retained separately on the LogicalProgram.

### M8-B verification

Local commands use `.venv/bin/python` on Linux/WSL2 Python 3.12.7. Inspected actual
CircuitCompiler/plan_program, CompilerContext/lifecycle, operation constructors,
code/layout factories and the three-patch example before integration. Inspected
the pinned public stimflow Chunk.verify implementation; all physical fragments
continue through it. Pins remain Stim 1.15.0, stimflow 1.17.dev0 at ffe0d043 and
Lark 1.3.1. No upstream source was changed.

- B1: `python -m pytest -q tests/test_lstim_semantics.py`: **117 passed in 0.20 s**;
  Ruff src/tests passes. Includes semantic vs earlier syntax failures, located
  option diagnostics, type/arity/default rules, loop cost/depth/exact budget,
  forbidden repeated resources/labels and no physical allocation/lifecycle copy.
- B2: `python -m pytest -q tests/test_lstim_lowering.py`: **47 passed in 0.22 s**;
  Ruff src/tests passes. Independently authored Python objects/fields, placement/
  site maps, explicit labels/bindings, nested barriers and fresh repeated object
  identities match; inspection cannot invoke CircuitCompiler.
- B3: `python -m pytest -q tests/test_lstim_compile.py --durations=5`:
  **26 passed in 11.76 s**; Ruff src/tests/examples passes. Signed d=3/5 X/Z
  memory, mixed-round parallel H/SE, Bell defaults/overrides, Knill default and
  pre-existing resources, and the full three-cycle P0/P1/P2 contract compare exact
  ideal/noisy Stim circuits, DEMs, detector coordinates, global record/observable
  metadata, stages/ancestry, use histories and source-labelled children against
  independently authored Python programs with the same explicit bindings and
  empty mapping. Chunk/fragment verification, Stim DEM/noiseless detector checks
  and independent compilation/noise/open-output continuation are exercised.
  Lifecycle, occupied/stale aliases, parallel overlap, wrong resource state,
  nondeterministic readout, implicit-ID collision and mixed-distance coordinate
  collision still fail in the existing compiler with their original cause.
- Combined: `python -m pytest -q tests/test_lstim_semantics.py
  tests/test_lstim_lowering.py tests/test_lstim_compile.py --durations=5`:
  **190 passed in 11.92 s**. The first B1 run exposed two harness cases sending
  composites into grammar-forbidden PARALLEL; the first B3 run used a nonexistent
  DecoderView.dem test attribute. Both harnesses were corrected without changing
  existing tests or weakening a physics assertion; final checkpoints above pass.
- M8-A compatibility checkpoint (syntax plus semantics): **280 passed in 4.51 s**,
  including isolated-wheel syntax loading with physical imports blocked.
- B4: `python -m pytest --durations=10`: **958 passed in 670.19 s (0:11:10)**,
  retaining all 768 previous cases. The slowest existing test is the d=5 reused/
  fresh encoded-reference teleportation check at 32.81 s; no physics test changes.
- `python -m ruff check src tests examples`: **all checks passed**, including
  an independent clean export of the exact staged files.
- That staged export passes all six frontend modules (M8-A and M8-B):
  **353 passed in 16.41 s**, using `PYTHONPATH=src` and `--durations=5`.
  Its sdist/wheel build passes. A separate isolated-wheel namespace consumer
  compiles a labelled three-patch Knill cycle, verifies bindings/relocation,
  51 wires, labels, independent noise, metadata/DEM/views/frame plans, and checks
  every package module came from the wheel. PyMatching/Matplotlib/examples/
  external_lib/knill_bench imports are actively blocked. This is internal
  namespace compatibility evidence, not M8-C public-root/file/formatter polish.
- `python -m build --outdir /tmp/lstim-m8b-dist` and the clean staged export's
  build: **sdist/wheel built successfully**. Archive checks verify identical
  grammar bytes, new runtime modules matching the Git index, unchanged exact
  Lark pin and the canonical contract in sdist; no examples/tests/external code
  enter the wheel. Final ledger changes do not alter tested code/test files.
- The README source snippet compiles to **17 qubits / 40 detectors**, with valid
  metadata and DEM. `python -m pip check`: **no broken requirements**.
  `git diff --check` and `git diff --cached --check`: **pass**. Staged runtime
  changes are confined to language/ and package instruction/status documents.

Implemented/verified: static semantics, exact existing-object lowering and focused
physical/DEM/metadata equivalence. No implemented-but-unverified physical behavior
is introduced. Remaining M8-C: package-root/file APIs, canonical formatter and
installed public-interface polish. Remaining M8-D: complete raw-sample/decoder/
LER equivalence certification. No CLI, allocator, decoder, physical scheduler,
adaptive operation or alternate compiler is introduced. Remote platform evidence
is separate from local Linux verification.

## M8-A LSTIM lexer, parser, AST and diagnostics — 2026-11-08

Baseline: main `06cdc4fd61486cb4e0d138feff10c685bc1a0858` (M7-C, 605 tests).
Existing inspection/export edits and report deletions are preserved and excluded
from this milestone's commit. No external_lib or physical/compiler/decoder source
is modified. The root public Python operation API remains unchanged.

The new language/ package ships one grammar.lark, loaded via importlib.resources,
with LALR/contextual lexing, positional metadata and iterative AST transformation.
Internal parse_ast/lex_source expose immutable syntax data and typed located
lex/parse/limit errors. Frozen header/code/patch/bind/operation/option/parallel/
repeat/file nodes retain order, labels, scalar types and half-open source spans.
Character offsets retain original CRLF and are excluded from span equality/hash.
The tracked docs/lstim_v1.md adapts the companion contract and freezes lexical
decisions, grammar restrictions, physical terminology and later milestone duties.

Grammar decisions: one instruction per line, brace-delimited multiline blocks,
ASCII case-sensitive names with explicit reserved keywords and keyword boundaries,
unsigned decimal integers, optional [label] before (rounds), then targets/options.
A grammar lookahead distinguishes option keys from targets without LALR conflicts.
PARALLEL contains primitives; REPEAT retains operations/groups/nested repeats.
No loop expansion or quantum-state validation occurs. Unsupported versions,
unknown/duplicate option keys, wrong signatures/values, declaration ordering,
empty groups and resource-changing repeat operations await M8-B semantic checks.
Physical Stim opcodes, record syntax, strings and expressions are rejected.

Budgets: 1,000,000 source code points, 100,000 tokens including newlines,
64 brace levels and 128 decimal digits per integer. Oversized inputs fail with
source name, position, bounded excerpt and caret. These are syntactic limits,
separate from M8-B's future static expanded-operation budget.

Selected/tested runtime is Lark 1.3.1 (current lark distribution, not lark-parser).
Inspected [release metadata](https://pypi.org/project/lark/1.3.1/) and
[official APIs](https://lark-parser.readthedocs.io/en/stable/classes.html), then
the installed interactive parser/Transformer_NonRecursive implementation. Runtime
dependency and package data are explicit in pyproject.toml. Setuptools/wheel are
dev dependencies so the isolated-wheel regression builds offline without build
isolation. Existing Stim 1.15.0/stimflow ffe0d043 pins are unchanged.

### M8-A verification

Commands below use `.venv/bin/python` on Linux/WSL2, Python 3.12.7.

- A1: `python -m pytest -q tests/test_lstim_lexer.py`: **52 passed in 1.44 s**;
  `python -m ruff check src tests`: **all checks passed**.
- A2: `python -m pytest -q tests/test_lstim_parser.py`: **87 passed in 0.18 s**.
- A3: `python -m pytest -q tests/test_lstim_diagnostics.py`: **24 passed in 3.44 s**.
- Combined syntax checkpoint: `python -m pytest -q tests/test_lstim_lexer.py
  tests/test_lstim_parser.py tests/test_lstim_diagnostics.py`:
  **163 passed in 5.05 s**; `python -m ruff check src tests examples` passes.
- The wheel regression builds an isolated wheel, extracts it outside the repo,
  removes source import paths, proves syntax works with physical imports blocked,
  then verifies normal installed-root imports. grammar.lark loads and token/AST
  APIs run from the wheel. Wheel/sdist archive inspection verifies identical
  grammar bytes, exact Lark dependency metadata and the canonical contract in
  sdist; no examples/tests/external code enter the wheel.
- `python -m build --outdir /tmp/lstim-m8a-dist`: **sdist/wheel built successfully**.
  `python -m pip check`: **no broken requirements**.
- A seeded 3,000-source mutation check gives 92 valid syntax trees and 2,908
  typed located errors, with no untyped failures.
- A4: `python -m pytest`: **768 passed in 713.70 s (0:11:53)**, including all
  605 unchanged M1–M7-C regressions and the 163 new syntax cases.
- `python -m ruff check src tests examples`: **all checks passed** in both the
  working tree and a clean export of exactly the staged files.
- The exact staged export independently passes the combined syntax command:
  **163 passed in 4.66 s** with `PYTHONPATH=src`. Its sdist/wheel build succeeds;
  archive checks match grammar bytes and README to the Git index, retain the
  exact Lark pin, and exclude unrelated inspection exports/reports. Final ledger
  updates change no tested implementation/test source.
- `git diff --check` / `git diff --cached --check`: **pass**. The staged runtime
  diff contains only language/ and instruction/status documents; top-level
  syntax interfaces/modules have English docstrings. No physics tests change.

Implemented and verified here: syntax, AST, diagnostics and grammar packaging.
No implemented-but-unverified physical behavior is introduced. Remaining M8-B:
semantic version/declaration/signature/option checks, bounded repeat validation/
unrolling, source-aware existing-operation/BindPatch lowering and compile bridge.
M8-C public API/formatter and M8-D independent physical/DEM/sample equivalence
remain deferred. This milestone does not claim a runnable text circuit, decoder
or CLI. Remote platform results are separate from local Linux evidence.

## M7-C three-patch Knill memory — 2026-11-08

Baseline: main `8fc65a9b808d31308878f8bd22d8d32ffa359a5d` (M7-B), with
544 passing tests and all Ubuntu/Windows Python 3.11/3.12 jobs successful in
CI run 42470273846. Existing uncommitted inspection/export/report work is
preserved and excluded from this implementation's commit.

Added a separate source example, examples/knill_memory_three_patch_reuse.py,
with explicit caller-authored triples, fresh A_t/B_t BindPatch reservations and
existing KnillEC primitives. The compiler/package public API needs no change.
build_explicit_three_patch_knill, explicit_three_patch_program,
prepare_three_patch, run_three_patch, describe_experiment and save_report expose
canonical artifacts, replaceable M6-D external adapters and bounded aggregate
reports. M6-D fresh-resource behavior and its result format remain unchanged.

Cycle uses (input D, A, B/output D):

| Cycle | Input use | A use | B/output use |
| --- | --- | --- | --- |
| 0 | P0/0 | P1/0 | P2/0 |
| 1 | P2/0 | P0/1 | P1/1 |
| 2 | P1/1 | P2/1 | P0/2 |
| 3 | P0/2 | P1/2 | P2/2 |
| 4 | P2/2 | P0/3 | P1/3 |

Exactly 3(2d²-1) physical wires are retained: 51 at d=3, 147 at d=5.
Input/resource preparation defaults to d full SE rounds; ordinary post-SE is
independently configured. Open outputs remain available. Canonical detectors,
all physical noise, source/use histories and exact v3 views/models are preserved.
One compiled sampler samples once per bounded batch; decoder hypotheses edit
only offline records/frames. Aggregate runs retain no raw shot matrices. Reports
include use/stage/global-local identities and a full-precision flattened DEM hash,
honest corrected-readout XOR input labels, algorithm limitations and wall phases.

The 61 new focused cases retain all 544 regressions and independently check
occupancy, signed physical tableaux/correction execution and untouched encoded
reference entanglement through three teleports, all Bell branches/random gauges,
epoch-local exact fault marginals and all categorical Bell atoms, physical noise,
fresh-resource gate/fault unfolding, temporal targets, stale-state/byproduct
negatives, public-only decoder replacement, unchanged raw/DEM replay, exact
chunk-independent predictions, causal once-only corrections and T=10 smoke.
README, architecture, root/test policies, local ledgers and a detailed experiment
guide document the physical identities and verified boundaries. Every significant
function/class in the new example has an English physical/order/API docstring.

### M7-C verification

Commands use `.venv/bin/python` on Linux/WSL2 Python 3.12.7. Inspected actual
Stim compile_sampler/FlipSimulator/DEM and public stimflow Chunk.verify APIs.
Pins remain Stim 1.15.0, stimflow 1.17.dev0 at
ffe0d043598ed5df0851a3e6b4920359a23fafbd, PyMatching 2.3.1 (dev/example only),
NumPy 2.5.4, pytest 9.2.0, Ruff 0.17.4 and build 1.6.1. No upstream copy changed.

- `python -m pytest -q tests/test_patch_reuse_knill_e2e.py
  tests/test_patch_reuse_offline_replay.py`: **61 passed in 300.29 s**.
- Corrected temporal-target checkpoint: `python -m pytest -q
  tests/test_patch_reuse_knill_e2e.py -k temporal_model`: **4 passed,
  36 deselected in 21.35 s**. A one-round ordinary SE's first record is also
  its final record; the test checks actual target record identity. The initial
  combined focused pass had 59 passed/2 failed solely from that harness assumption.
  No runtime or historic physics assertion was changed to resolve it.
- `python -m pytest`: **605 passed in 669.37 s**, retaining all 544 previous
  tests (including the 440 historic M6 checks). An earlier run was interrupted
  after 382 passing checks to apply the new temporal test correction.
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: **sdist and wheel built successfully**. The exact staged
  tree independently builds; its sdist includes the new example/guide/tests,
  while the wheel contains no examples/tests/reference code.
- `python /tmp/m7c_validate_wheel.py`: isolated wheel consumer passes three-cycle
  X/Z memory with its own noiseless GF(2) sector StageDecoder, public use-aware
  requests/views/conditional models and use/input-bound correction replay. Optional
  PyMatching, Matplotlib, examples, tests and reference imports are actively blocked;
  package code loads from the isolated installation with pinned shared dependencies.
- All seven CI example commands pass from the exact staged source tree:
  `python examples/two_patch_memory.py`, `python examples/two_patch_bell_roundtrip.py`,
  `python examples/knill_ec_single_round.py`, `python examples/offline_dem_views.py`,
  `python examples/memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731`,
  `python examples/knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732`,
  `python examples/knill_memory_three_patch_reuse.py --suite --shots 32
  --batch-size 13 --p 0.001 --seed 733`. CI adds the last bounded command to
  all four Ubuntu/Windows Python 3.11/3.12 jobs; remote results are checked after
  push and reported separately from local evidence.
- The README public-usage snippet and a different caller-authored triple schedule
  execute successfully. AST audit passes all nine functions/classes plus the
  new example module description. `python -m pip check` finds no broken
  requirements; Git whitespace checks pass. Pre-existing tracked edits/deletions
  and untracked example-status contents are preserved and excluded from staging.

Noisy report command:
`python examples/knill_memory_three_patch_reuse.py --suite --shots 2048
--batch-size 256 --p 0.003 --seed 20261108
--output-dir implementation_files/e2etest/m7c_three_patch`.
All four T=3 cases use eight batches; d=3 X/Z yield 454/553 failures of 2048,
d=5 X/Z yield 652/651. Run walls are 2.631/2.582/14.823/13.796 s; report wall
0.618 s. These are honest restricted-decoder results, not threshold claims.

`python examples/knill_memory_three_patch_reuse.py --teleportations 10 --shots 9
--batch-size 4 --p 0 --bit 1
--output-dir implementation_files/e2etest/m7c_ten_cycle` gives 51 physical wires,
773 records, 584 detectors, 21 uses and zero failures in batches 4/4/1. Run wall
10.540 s: compile/validation 3.415 s, temporal stage/view models 5.877 s, frame
maps 0.294 s, conditional models 0.837 s, sampling 0.00046 s. Prefix/model setup
is the largest observed cost here. Only physical-state width is bounded;
instructions, records, detectors, history and symbolic/model setup grow with T.
Local aggregate JSON/CSV/PNG/SVG are ignored, raw shots are not saved/committed.

Remaining limitations: inherited temporal parallel-edge ambiguity, per-patch Bell
capacity approximation, omitted cross-boundary SE offsets and incoming-sector
residual errors; no optimal joint decoding, threshold claim, automatic allocation,
adaptive sampling/factories, hardware transport or real-time feedback. General
large-T setup optimization and external production decoder/runner work remain
deferred. Verified behavior is restricted to the explicitly tested code/duration/
noise/adapter cases; no untested new runtime functionality is claimed.

## M7-B epoch-aware flows, noise, views and offline frames — 2026-11-08

Baseline: `2577b7f1f3aac2efd4938368945768e8174bfb88` (M7-A), merged on main
and independently verified in all four Ubuntu/Windows Python 3.11/3.12 jobs of
CI run `42467020421`. Existing uncommitted export/example/report changes are
preserved and excluded from this implementation's commit.

- DetectorInfo exports anchor_use_id/source_use_ids separately from immutable
  physical-support sites and existing (x,y,t) coordinates. Metadata reconstructs
  these from actual producer fragments. Current check sectors/round counters
  are use-keyed. Signed reset/readout flow boundaries and all canonical global
  detectors remain; no physical gate or deterministic relation is removed.
- TimeLayer.active_use_ids identifies inclusive reset-through-destructive-readout
  occupancy. The noise pass derives idle sites from each active use, including
  check ancillas; measured/available/reserved gaps are excluded. Global/primitive/
  instance rules, explicit zero, waiting blocks, composite inheritance and
  once-only gate/idle noise are unchanged. BindPatch remains zero duration/noise.
- PreparationDependencyEvent carries actual input/output use edges; immutable
  use_preparation_dependencies retains each historical use's latest ancestry.
  New resets start independent sources. Already teleported information retains
  legitimate previous-use preparation dependencies on the surviving state.
- DetectorSelector adds independent use_ids/use_membership filters with anchor,
  touching and strict semantics; physical-block filters still include all epochs.
  SelectionAudit exports requested and contributing uses. Default observable
  locality connects actual interacting/relocated/signed-relation uses, not all
  occupants of the same coordinates. Explicit observing-region overrides remain.
- DecoderView intentionally migrates to schema v3, fingerprinting exact physical
  circuits plus use/binding/owner, Bell, ancestry and timing histories. Regenerate
  cached v1/v2 fingerprints/views/plans. Lossless exact instruction/DEM snapshots,
  arbitrary index order, signed references, hyperedges, correlated separators and
  physical-circuit re-extraction remain intact. Local views never delete faults.
- BoundaryRequest/ReadoutRequest identify their actual use/source_preparation;
  optional preparation still means the initialization's prepared-logical target.
  Check histories, temporal models and sector transfer use the correct reset
  and current orientation through real H/CNOT. Model-only MPP targets never enter
  canonical measurements/decoder truth. Conditional Bell models use the actual
  output-use preparation and resource-use CNOT window, including existing Bell
  resources in either CNOT direction. Window/use/module IDs expose categorical
  atoms, exclusive groups and correlated readout/check/logical/survivor actions.
- Every physical preparation/SE/readout module has a use-labelled FrameBoundary.
  CorrectionBatch adds optional block_use_id/input_ids without breaking the
  three-argument API. Explicit use/order/source/shape/shot mismatches fail before
  mutation; each unique module can update once. Physical resets extinguish old
  supports while earlier Bell records can affect later teleported data. Raw
  samples remain immutable; current events recompute after software frame edits.
- Audited unchanged _logical.py, _parallel.py, planning and records.py: existing
  signed flow/reset boundaries and global-key batched transforms need no physical
  implementation change. All modified source APIs/significant helpers have
  English physical/identity/order docstrings; README/architecture and affected
  policy/status ledgers document use selection and migration.

### M7-B verification

Linux/WSL2 Python 3.12.7; commands use `.venv/bin/python`. Unchanged pins:
Stim 1.15.0, stimflow 1.17.dev0 at ffe0d043598ed5df0851a3e6b4920359a23fafbd,
PyMatching 2.3.1 (dev only), pytest 9.2.0, Ruff 0.17.4, build 1.6.1. Inspected
installed Chunk.verify/reset/readout/ChunkCompiler, NoiseModel.noisy_circuit and
Stim FlipSimulator/DEM APIs; no external source or dependency pin was changed.

- Baseline `python -m pytest`: **493 passed in 474.32 s**.
- Final `python -m pytest`: **544 passed in 568.60 s**, retaining all 493
  previous checks and adding 51 M7-B cases.
- Incremental memory/lifecycle/noise checkpoint: **29 passed in 9.34 s**.
- View/ancestry checkpoint: **110 passed in 49.05 s**.
- Stage/strict-frame checkpoint: **33 passed in 39.77 s**.
- Initial new suite: **50 passed in 53.63 s**; the later reversed-resource test
  adds one further case. Frame/record checkpoint: **27 passed in 26.08 s**.
- Final new suite plus retained missing-byproduct physics test:
  `python -m pytest tests/test_epoch_views_noise.py tests/test_epoch_stages_frames.py
  tests/test_knill_memory_offline_decoding.py::test_missing_bell_hypothesis_breaks_logical_memory -q`
  -> **52 passed in 57.19 s**.
- The v3 full-run migration initially rejected an old missing-byproduct test's
  deliberately corrupted Bell source paired with stale original requests.
  Its harness now explicitly checks that source rejection, rebuilds all requests
  from the corrupted source, and retains the original physical failure assertion.
  Migration plus both existing-resource directions: **3 passed in 2.51 s**.
  The initial full run had **542 passed, 1 failed in 532.66 s**, solely this
  now-corrected source-binding test harness; no physics assertion was removed.
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: **source distribution and wheel built successfully**.
- Isolated installed wheel: use selectors/v3 snapshots, recycled preparation/
  SE/Bell models, all frame boundaries and static DEMs pass with PyMatching,
  Matplotlib, test/helper and reference imports blocked. Pinned dependencies are
  shared read-only; package code is loaded from the isolated wheel installation.
  The exact staged Git tree independently builds and passes these wheel checks.
- README use-selection and boundary/correction snippets execute successfully;
  all modified source public/significant helper docstrings pass the audit.
- All six CI examples passed: two_patch_memory.py, two_patch_bell_roundtrip.py,
  knill_ec_single_round.py, offline_dem_views.py,
  memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731,
  knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732.
- Independent parent/current exact-instruction hashes agree for ideal/noisy
  memory/Clifford, Knill and M7-A reuse programs, including double probabilities,
  physical coordinates/wire maps and raw measurement keys/order.
- `python -m pip check`: **no broken requirements**. `git diff --check` passes.

The 51 new cases verify d=3/5 signed mixed X/Z repeated memories, raw/annotation
parities, exact noise tables and occupancy gaps; use-specific/block/joint/default
local views and physical fault marginals with excluded-region output effects;
hyperedges, correlated components and precise repeat/SHIFT_COORDS snapshots;
temporal early/late result targets at both P0 uses; actual signed H/CNOT sector
transfer across an old site's reset; all Bell atoms against independent Stim
Pauli propagation; explicit physical correction execution, M5 replay and open
outputs with two spectators; old physical-frame extinction plus surviving
teleported feedback; and stale epoch/key/source/order/support/shot rejection.
No hidden fault/tableau truth enters normal decoder inputs.

Implemented but unverified: no additional behavior is claimed. Full three-patch
multiple-cycle Knill LER comparison remains M7-C. Automatic allocation, scheduling
optimization, production/joint decoders and adaptive physical execution remain
outside scope. The unchanged four-environment CI matrix runs after push, and
its observed results are reported separately from local evidence.

## M7-A explicit binding and physical-use lifecycle — 2026-11-08

Baseline: `e296705c963be3d63762526231ab25570ef4a433` (M6-D). Its four-job
Ubuntu/Windows Python 3.11/3.12 CI run `42427365557` passed before this task.
Existing uncommitted circuit-export/example/report changes are preserved and
excluded from the M7-A commit.

- Public BindPatch(logical_id, physical_block_id) is a compile-time reservation,
  separate from physical OperationModule. It has zero gates, records, TICKs,
  reset and noise. Active/reserved/unknown targets, reused logical names, stale
  handles and parallel bind/use/reset/readout overlap fail explicitly. Initial
  mappings may now reserve a subset of registered patches, including none.
- BlockUseId(block_id, epoch) identifies an immutable reset-to-release occupancy
  on fixed physical sites. The first actual LogicalInit starts epoch 0; binding
  never advances it. Measured status remains until reservation changes it to
  uninitialized. LogicalInit performs the sole data reset. Physical indices and
  layouts stay fixed. available_blocks reports unreserved bindable patches.
- MeasurementKey has a backward-compatible trailing epoch=0; local check rounds
  restart per use while global raw indices increase. All preparation/readout
  records, signed deterministic observables and module identities remain
  addressable after retirement. BlockUseInfo retains reset/terminal modules,
  half-open global record/layer intervals and logical-owner history. Fragments,
  preparations, readouts, observables, Bell results and relocations carry use IDs.
- Planning resolves each user entry after preceding bindings/relocations. Knill
  preserves persistent data identity and slot on its surviving resource use;
  measured patches become explicitly bindable and both temporary names retire.
  Fresh aliases reset/reuse retired tableau slots within a fixed registered-patch
  capacity; 13 occupancies on one patch retain one simulator slot.
- Global physical flows/detectors/noise retain their canonical semantics. Fresh
  reset boundaries prevent inherited stabilizer/frame/sector state. Independent
  provenance validation reconstructs epochs, intervals and owner events rather
  than trusting final mappings. Source docstrings, architecture glossary, README
  example and affected AGENTS/STATUS ledgers describe these contracts.

### M7-A verification

Local Linux/WSL2 Python 3.12.7; commands use `.venv/bin/python` (equivalent to
activating the existing environment). Stim 1.15.0, stimflow 1.17.dev0 at
ffe0d043598ed5df0851a3e6b4920359a23fafbd, PyMatching 2.3.1, NumPy 2.5.4,
SciPy 1.18.1, pytest 9.2.0, Ruff 0.17.4 and build 1.6.1. No pin/upstream change.
Inspected installed named-observable allocation/o2i mapping, ChunkCompiler,
reset/readout Chunk boundaries, ChunkReflow and signed Stim flow behavior.

- Baseline `python -m pytest`: **440 passed in 374.81 s**.
- Final `python -m pytest`: **493 passed in 430.94 s**, retaining all 440
  pre-existing tests unchanged and adding 53 focused reuse/physics tests.
- Incremental lifecycle checkpoint: **21 passed in 5.62 s**, in addition to the
  32 passing physical replay cases.
- `python -m pytest tests/test_patch_reuse.py tests/test_knill_teleportation.py -q`:
  **77 passed in 122.94 s** (53 new tests plus all 24 old Knill tests).
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: **source distribution and wheel built successfully**.
- The exact staged Git tree also builds in a temporary source checkout. Its
  installed wheel passes two-use replay, an initially unreserved patch, public
  availability, corrupted-ledger rejection and global DEM construction with
  PyMatching/Matplotlib/test/reference imports blocked. Pinned dependencies are
  shared read-only; package code is loaded from the isolated wheel installation.
- All six CI example commands pass: two_patch_memory.py,
  two_patch_bell_roundtrip.py, knill_ec_single_round.py, offline_dem_views.py,
  memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731,
  knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732.
- `python -m pip check`: **no broken requirements**. `git diff --check` passes.

Tests independently read reset targets, semantic keys and global rec offsets;
verify d=3/5 X/Z both signed input bits with physical/virtual Paulis, two distinct
observables on one fixed patch, ideal/noisy DEMs and zero noiseless event flips;
reject an added cross-reset physical stabilizer flow; and check independent
spectators, registration order, retirement and open-output Knill rebinding.
No existing assertion/test is removed or weakened.

Implemented but unverified: no additional behavior is claimed. Epoch-aware local
DEM/stage request policies and a full three-patch multiple-cycle Knill decoding
proof remain M7-B/M7-C. There is no automatic allocator or production decoder.
The unchanged Ubuntu/Windows Python 3.11/3.12 matrix runs on push; final remote
results are reported after observing that run, with no local Windows claim.

## M6-D implemented and verified — 2026-11-08

Baseline local/remote commit: `c927e4b72f72c488d7bc5d853d5f812ac6ab4e86`.
Its Ubuntu/Windows Python 3.11/3.12 CI run 42424216057 passed all four jobs.

- examples/knill_memory_offline_decoding.py builds fixed X/Z memory with known
  input 0/1, resource/input SE^d by default, fresh A_t/B_t blocks for T=1/2,
  optional ordinary post-SE and final destructive readout. Logical D persists.
  One canonical physical raw batch supplies every sequential offline stage;
  gates/noise never depend on inferred outcomes. No recycling/adaptive runner.
- CompiledCircuit.make_frame_plan compiles immutable sparse correction maps once
  through actual H/CX/reset/measurement, virtual Paulis and causal Bell feedback.
  Public typed CorrectionBatch/FrameBoundary/OfflineFramePlan/Batch contracts
  validate source/boundary, binary dimensions and shot counts, reject duplicate
  updates and preserve original raw records. Current view events are recomputed
  from interpreted records. Open physical residual X/Z maps support tableau proofs.
- Public BoundaryRequest/ReadoutRequest/StageRequests and StageInputs/Result/Decoder
  separate external preparation, Bell and ordinary-SE choices. Strict temporal
  regions preserve canonical stage/global IDs. Physical noisy prefixes with
  model-only ideal MPP probes define last-record XOR actual boundary-check and
  prepared-logical targets. No probes are added to the sampled experiment or
  exposed as decoder truth. Temporal MWPM precedes a separate CSS sector solve;
  a logical flip prediction is not treated as an unspecified physical correction.
- Exact signed Pauli support elimination transports predicted net boundary sectors
  through actual transversal pairings. Bell capacity input is interpreted raw
  check parity relative to that predicted sector, not unconditional zero. Physical
  frame signs are already applied once by the plan. Raw gauges remain records.
- ConditionalReadoutModel preserves every standard Pauli/depolarizing/measurement
  atom from resource CNOT through Bell destructive readout, probabilities and
  exclusive channel groups, joint raw/check/logical effects and survivor physical
  X/Z actions. It conditions on prior sector/frame hypotheses and is not a
  deterministic shot-conditioned Bell DEM. Unsupported physical channels fail.
- Algorithms are replaceable source-example adapters only: correlated temporal
  MWPM plus CSS sector capacity matching, and conditional unit-weight per-patch
  readout matching. Canonical full DEMs and cross-stage detectors remain unchanged.
  Limitations are explicit: parallel-edge target ambiguity, omitted correlated
  joint inference, strict-window cross-boundary offsets, one-round post-SE without
  temporal information, and possible earlier residual decoder mistakes. Nonzero
  LER compares corrected final bits against intended outputs, not decoder belief.
- Exclusive perf_counter wall phases distinguish validated compilation, exported
  DEM, frame maps, stage/conditional models, matcher setup, sampler construction,
  physical sampling, m2d, current-event inputs, decoding and frame updates. Full
  CLI wall and a separate diagnostic profile are reported. All M6-D reports/figures
  are in implementation_files/e2etest/m6d_knill, separate from M6-C. Raw samples,
  profiler binaries, large logs and reference clones are excluded from commits
  and all implementation reports are pruned from package distributions.

### M6-D evidence

Unchanged installed pins: Stim **1.15.0**, stimflow **1.17.dev0** at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`; PyMatching **2.3.1** stays dev/example
only. Inspected installed matching/decode_batch/fault-ID/parallel-edge APIs,
check-matrix decoding, Stim boundary MPP/DEM/Pauli conjugation and FlipSimulator
batch/noise/randomization APIs. Read-only Hex
`5de58f2f80791054411ad3c0885a4fe3671ed56a` css_detector_module two-stage inference,
measurement_module, Bell correction generation, sparse measurement-flip maps and
static simulate sequential event recomputation were studied. No upstream source
was changed, imported at runtime or copied wholesale. No pin was changed.

Local Linux/WSL2 Python 3.12.7 validation:

- `python -m pytest --durations=15 --junitxml=.../m6d_knill/pytest.xml`:
  **440 passed in 258.20 s**. Added **46** tests; all 394 previous tests retained.
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: source distribution and wheel built successfully.
- All six examples passed, including eight-case Knill noisy/noiseless suites.
- Isolated installed wheel passed with PyMatching/Matplotlib/test/reference imports
  blocked: T=2 generation, exact global DEM/views, temporal stage models,
  conditional Bell actions and batch frame maps. Copied standalone Knill example
  runs against that wheel. Distribution contents include new code/tests/examples
  and exclude local reports, environments, raw samples and external clones.
- d=3/5 X/Z and both intended bits, T=1/2: 64 physical shots per case recover
  noiselessly with all Bell branches. Actual physical encoded-reference tableaux
  preserve XX=ZZ=+1 through T=1/2 at both distances across 16 branches each.
  Open frames agree with M5 physical replay; an omitted byproduct causes failure.
- Every conditional atom is checked against independent vectorized Stim Pauli
  propagation at d=3/5, including exclusive groups and survivor actions. Ten
  selected physical fault categories compare actual Stim global signatures;
  an undetectable logical fault correctly produces residual failures. Early/late
  result target inference is verified in a measurement-noise regime. Frame edits
  agree with explicit physical correction execution/current-event conversion.
- Noisy replay, alternate matching weights, chunk independence, one sampler call,
  no oracle input, stage/gauge partitions, physical/virtual Paulis and H,
  parallel/spectator isolation, malformed batches/source IDs and once-only updates
  pass. No stochastic LER target or performance timing threshold is asserted.
- pip check and git diff --check pass; all four external reference trees are clean.

Final unprofiled report command:
`python examples/knill_memory_offline_decoding.py --suite --shots 20000 --p 0.001
--seed 20261108 --output-dir implementation_files/e2etest/m6d_knill`.
Input/resource rounds=d, post rounds=1, 20,000 shots/case, **160,000 total shots**.

| d | Basis | T | Seed | Errors / shots | LER |
|---|---|---|---|---|---|
| 3 | X | 1 | 20261108 | 394 / 20000 | 0.01970 |
| 3 | X | 2 | 20261109 | 715 / 20000 | 0.03575 |
| 3 | Z | 1 | 20261110 | 645 / 20000 | 0.03225 |
| 3 | Z | 2 | 20261111 | 1055 / 20000 | 0.05275 |
| 5 | X | 1 | 20261112 | 373 / 20000 | 0.01865 |
| 5 | X | 2 | 20261113 | 725 / 20000 | 0.03625 |
| 5 | Z | 1 | 20261114 | 415 / 20000 | 0.02075 |
| 5 | Z | 2 | 20261115 | 756 / 20000 | 0.03780 |

Full CLI wall **44.920 s** includes startup/imports/report/exit. Exclusive experiment
wall totals **42.995 s**: validated compilation **21.119 s**, other model/map/matcher
setup **8.084 s**, current-event/input work **6.678 s**, frame updates **4.574 s**,
temporal/capacity decoding **1.535 s**, and physical sampling **0.354 s** (plus
other recorded phases). Compilation/setup dominate this workload; sampling is
under 1% of experiment wall. A separate instrumented d=5 Z T=2 1,000-shot profile
shows heavy flow reflow, Pauli-map and repeated code/metadata construction. Its
helper cumulative totals overlap and do not account for complete wall; final
unprofiled phase timings are authoritative. Machine/thread details, full CSV,
JSON parameters/fingerprints/versions, PNG/SVG and bottleneck analysis are saved
in the new folder. This run had no concurrent task test/profile/build workload;
OS activity was uncontrolled and timings are observations, not portable limits.

Implemented but unverified: no additional recovery behavior is claimed. This is
an explicitly restricted modular baseline, not exact maximum-likelihood or a
validated production joint decoder. Source seed equality is not promised across
Stim versions/SIMD machines/call structures. General conditional joint models,
optimized inference/caching/event updates, adaptive control, block reuse and
knill_bench integration remain future work. Remote CI is checked after push and
reported separately. User explicitly authorized commit/push after verification.

## M6-C implemented and verified — 2026-11-08

Baseline local/remote commit: `cf4106becd2031e71f42bb25b2858cfaf01a74ed`.

- examples/memory_offline_decoding.py uses only public converter/view APIs for
  ordinary X/Z memory, independent d/R, explicit NoiseModel or uniform p, and
  seed/shot parameters. R includes one init syndrome round. The minimal CLI's
  fixed suite contains d=3/5 X/Z R=d and two independent concurrent X/Z patches.
- One raw physical batch per experiment supplies Stim m2d event/observable-flip
  labels for global, observable-local and strict patch strategies. Results retain
  original immutable raw order, canonical ideal/noisy circuits, public metadata,
  the undecomposed global DEM, view mappings, predictions and exact XOR failures.
  Reports distinguish any-observable shot errors from per-observable errors.
- PyMatching 2.3.1 operates only in the example/tests. Derived views explicitly
  request Stim graphlike decomposition; the adapter rejects any remaining
  component with more than two detectors. Correlated ^ mechanisms stay intact;
  two-pass correlated MWPM is documented as a heuristic, not exact inference.
  Canonical DEM semantics never depend on the selected decoder.
- JSON/CSV aggregates and PNG/SVG figures include parameters, versions, source/raw
  hashes, scopes, counts and timings. Figures use 95% Wilson intervals and matched
  observable scopes. Matplotlib is a dev dependency. Small requested reports and
  figures are explicitly committed under implementation_files/e2etest; raw shots
  and large logs stay ignored, and distribution manifests prune that directory.
- A necessary M6-B precision correction replaces Stim text snapshots with exact
  immutable instruction tuples. Remote M6-B run 42422493437 passed both Linux
  jobs but failed six exact model comparisons on each Windows job: Stim 1.15 DEM
  text uses only 16 significant digits on MSVC. Circuit text also rounds gate
  arguments to six digits. Exact copies now preserve probabilities, targets,
  tags, repeats, shifts and ^ components through public Stim append APIs.
  Schema v2 fingerprints include full circuit precision, eliminating rounded
  source-identity collisions. Regenerate older v1 fingerprints. Existing exact
  equality assertions remain unchanged; upstream sources were not modified.
- README/development/architecture and affected AGENTS/STATUS files document the
  consumer and observable conventions. CI adds the fifth example with a bounded
  128 shots/case. No runner, dataset framework, runtime decoder, Knill-specific
  inference or knill_bench dependency is introduced.

### M6-C evidence

Pins remain Stim **1.15.0** and stimflow **1.17.dev0** at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. Inspected installed Stim raw sampling,
m2d/reference and DEM APIs, PyMatching 2.3.1 model/decode_batch correlation flags,
fault-ID dimensions and documented hyperedge behavior. Read-only surface-sim
`493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` memory example and lomatching
`b55a7a65969a106a547622287b620f0da2cb5e39` batch decoder/selection were inspected.
Stim printer source was inspected to diagnose platform precision. No external
source was changed, imported at runtime, or vendored.

Final local Linux/WSL2 Python 3.12.7 checks:

- `python -m pytest --junitxml=implementation_files/e2etest/pytest.xml`:
  **394 passed in 162.14 s** (26 new tests, all 368 previous tests retained).
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: source distribution and wheel built successfully.
- All five examples passed; the M6-C example ran both the bounded 128-shot/case
  isolated-wheel suite and the requested 20,000-shot/case figure suite.
- Isolated installed-wheel check passed with PyMatching/Matplotlib/test/reference
  imports blocked: exact full-precision source/model copies and same-raw m2d parity.
  A copied standalone demo ran against the installed wheel. Distribution contents
  include the consumer source/tests and exclude implementation reports, raw samples,
  local environments and reference clones.
- `python -m pip check`: no broken requirements. `git diff --check` passed;
  all four upstream reference working trees remain clean.
- Full test/lint logs, aggregate JSON/CSV, PNG/SVG and a compact verification
  report are in implementation_files/e2etest. Only compact reports/figures and
  final test/lint results are committed, with no raw shot dataset.

Figure command (Linux/WSL2 Python 3.12.7, NumPy 2.5.4, Matplotlib 3.11.2):
`python examples/memory_offline_decoding.py --suite --shots 20000 --p 0.003
--seed 20261108 --output-dir implementation_files/e2etest`.
Five experiments, **100,000 physical shots**, with one sampling call each:

| Memory | d | R | Seed | Global failures / shots | LER |
|---|---|---|---|---|---|
| X | 3 | 3 | 20261108 | 253 / 20000 | 0.01265 |
| Z | 3 | 3 | 20261109 | 265 / 20000 | 0.01325 |
| X | 5 | 5 | 20261110 | 118 / 20000 | 0.00590 |
| Z | 5 | 5 | 20261111 | 92 / 20000 | 0.00460 |
| mixed XZ | 3 | 3 | 20261112 | 528 / 20000 (any output) | 0.02640 |

Mixed-patch observable order is a_input/Z/global L0 (276 failures) then
z_input/X/global L1 (255 failures), deliberately different from physical order.
Observable-local and strict patch predictions agree with the global decoder per
observable on these same independent-patch samples. Three shots fail both outputs,
so the union count is 528, not 531. These are demonstration estimates for this
noise/circuit/decoder configuration, not a threshold or performance guarantee.
Seeds are reproducible only for fixed Stim/version/machine/call structure.

Implemented but unverified: no additional behavior is claimed. Local results do
not establish portable RNG equality or exact maximum-likelihood decoding. Remote
CI verification is performed after push and reported separately. Conditional
preparation/Bell/Knill noisy decoding remains M6-D/future work; production decoder
interfaces, optimized regions, adaptive control and runner integration stay deferred.

## M6-B implemented and verified — 2026-11-08

Baseline local/remote commit: `1d502621cab1595b35f74c1e2d628527ac11ad06`.

- Public immutable DecoderView snapshots select decoder inputs from one canonical
  physical experiment without sampling, modifying gates/noise, or importing a
  decoder. CompiledCircuit.make_decoder_view delegates to public decoding APIs.
- Explicit detector/observable/raw-record sequences preserve caller order;
  semantic selectors/callbacks preserve canonical order. IndexMap exports exact
  bidirectional global/local IDs. Reliable observable IDs remap contiguously,
  including a selected global observable 1 becoming local observable 0. Random
  Bell readout module IDs are explicitly rejected as reliable observables.
- DetectorSelector supports anchor/touching/strict block/stage membership, unions,
  X/Z checks and custom public-metadata callbacks. DetectorInfo now includes its
  actual physical anchor check basis and stable data support underlying all source
  records, checked against layouts/orientations independently of check ID prefixes.
  Explicit retain/omit/joint policies retain auditable requested/crossing/omitted
  detector IDs and actual region scope.
- Selected annotation circuits copy every original physical instruction/noise
  channel, TICK and coordinate shift. Repeat occurrences expand for arbitrary
  per-occurrence selection. Detectors move to end annotations in requested local
  order, with translated global record references and unchanged absolute
  coordinates; observable updates stay at their physical positions with local IDs.
  Stim re-extracts the DEM. Faults retain their selected effects even when they
  also touch excluded detectors; no global DEM line filtering occurs.
- Default models preserve hyperedges. Optional Stim correlated decomposition and
  DEM flattening preserve ^ semantics. Unsupported exact noise/decompositions,
  approximation options and direct global-DEM rewriting fail with typed errors;
  no silent MWPM approximation or gauge elimination is enabled.
- Vectorized sparse GF2Map operations project/recompute selected events and
  observable flips with the source circuit's noiseless reference alignment.
  RecordFlipMap and record XOR masks apply externally specified linear software
  frames to copies. Event updates agree with reconversion of corrected records.
  There is no per-shot Python loop or runtime correction-selection algorithm.
- Fingerprints cover ideal/physical circuits, Stim/schema version and public
  metadata. Public circuit/DEM/matrix objects return copies; typed DecoderInputs
  stamps a source identity on read-only arrays. Bare NumPy arrays need an explicit
  fingerprint check when exchanged between consumers; shape alone cannot prove
  sample provenance.
- Observable-local example selections use conservative physical interaction
  components (CNOT/relocation histories), with a user region-selector override.
  This supplies selection/models for external strategies, not lomatching itself.
  examples/offline_dem_views.py samples once for global/patch/observable views and
  software record updates; CI now runs all four examples. README, architecture,
  development guidance and affected AGENTS/STATUS ledgers document the real API.

### M6-B evidence

Unchanged installed pins: Stim **1.15.0**, stimflow **1.17.dev0** at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. Inspected installed circuit-to-DEM,
reference_sample, m2d conversion, DEM indexing/flattened repeats/shifts and ^ target
APIs. Read-only references inspected: lomatching
`b55a7a65969a106a547622287b620f0da2cb5e39` (observing regions, annotation circuit
selection/re-extraction), surface-sim `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad`
(semantic detector/check metadata), and Hex
`5de58f2f80791054411ad3c0885a4fe3671ed56a` (offline correction-to-record maps).
None is imported, copied into runtime code, or modified.

Final local Linux/WSL2 Python 3.12.7 checks:

- `python -m pytest`: **368 passed in 153.61 s**. Added **105** tests; all 263
  M1–M6-A tests are retained unchanged.
- Focused view/record/M6-A parity suite: **119 passed in 20.45 s**, plus the final
  six physical-basis/support and cross-stage policy tests: **6 passed in 6.11 s**.
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: source distribution and wheel built successfully.
- Isolated built-wheel checks passed with decoder/test/reference imports blocked:
  memory/Knill identity models, permutations, observable maps, record frames and
  source validation. Wheel/source archives contain the new modules, helpers and
  example while excluding local briefs, environments and external clones.
- All four examples passed. Memory, Bell and Knill ideal/noisy DEMs remain valid;
  the new example reuses one 512-shot batch for 32-detector per-observable views
  with correctly mapped local observable IDs and 370/372 local DEM mechanisms.
- `python -m pip check`: no broken requirements. `git diff --check` passed;
  all four external reference working trees remain clean.

Independent model tests compare full/local marginal characteristic functions,
exhaustively over small hand-circuit output spaces and over seeded parity masks
for larger models. Physically enumerated faults verify that a mechanism touching
both kept/removed detectors survives, including observable flips and combined
independent fault probabilities. Other tests preserve true hyperedges and correlated
^ components, check repeat/SHIFT_COORDS behavior and nonzero reference signs,
compare 25,000-shot independent-stream marginals with uncertainty-aware bounds,
validate d=3/5 memory and open/closed Knill identity models, and reconstruct/project
one raw batch into many semantic regions. Record maps agree with independently
executed physical Pauli corrections. Negative source/record/stage/basis/support/
observable/shape/model requests fail clearly. Canonical full counts and M5
noiseless teleportation/entanglement/exact noise regressions all remain intact.

Implemented but unverified: no additional M6-B behavior is claimed. Windows and
remote CI execution remain separate from these local results.
Supported projection is exact physical-circuit re-extraction, not a direct global
DEM transform. Default regions are conservative candidates, not optimized observing
regions. Conditional Bell/preparation models, automatic physical-Pauli-to-record
maps, decoded noisy recovery/LER and the M6-C/D demonstrations remain deferred.
Edited records do not automatically produce a conditional DEM. No runtime decoder,
runner, adaptive branch, block reuse or upstream modification was introduced.
User explicitly authorized commit and push after testing; local briefs, generated
artifacts, environments and external clones remain excluded.

## M6-A implemented and verified — 2026-11-08

Baseline local/remote commit: `16e0c8772d6ae450491748ddf0757e3503708d9f`.

- Canonical ideal/noisy circuits now retain every deterministic global flow-derived
  detector. Knill stage separation is an explicit non-mutating annotation view;
  quantum gates, physical/noise locations, raw records, coordinates and observables
  are preserved. Random Bell bits remain classical records.
- DetectorInfo retains global indices, exact raw parities/keys, semantic
  check/block/module anchors, primary anchor stage, all ordered source stages and
  proposed-boundary markers. Boundary candidates refer to present global
  detectors. The read-only M5 suppressed_detectors alias remains available.
- Public stage_separated_circuit and stage_separated_detector_indices provide
  the legacy view and its local-to-global detector mapping. measurement_index_by_key
  reverses raw semantic IDs. validate_metadata checks exact circuit metadata and
  typed ancestry edges against physical fragments and relocation boundaries.
- Preparation sources are tracked per physical block at actual operations.
  CNOT conservatively joins its operands' histories; Knill transfers input/resource
  histories to the survivor. Spectators and independent parallel gadgets remain
  isolated. Pre-existing resources, reference entanglement, extra SE, subsequent
  H/Paulis/CNOT, and repeated relocation preserve appropriate ancestry. Retired
  identities leave active bindings; their preparation events remain historical
  sources. Per-shot symplectic correction values are independent of source lists.
- Physical and final affine output-frame provenance uses causal sources. Existing
  CompilerContext affine frame algebra and its original regression contract remain
  unchanged. Bell results snapshot ancestry at each relocation, so later
  preparations cannot leak backward into earlier output-frame metadata.
- Frame evaluation keeps strict M5 noiseless validation as the default. The
  explicit validate_noiseless_preparation_corrections method checks final raw CSS
  equations and the prepared logical eigenvalue without frame replay. Opt-in
  validation="hypothesis" accepts noisy externally selected corrections after
  shape/identity/orientation/source/support/logical-commutation validation,
  without treating faulty final checks as truth. No decoder is selected, no
  unresolved frame is guessed, and samples/circuits are never rewritten in place.
- README, architecture, development instructions, example, AGENTS and affected
  component ledgers document the canonical-detector/API migration and limits.

### M6-A evidence

Unchanged pins: Stim **1.15.0**, stimflow **1.17.dev0** at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. Inspected the installed
ChunkCompiler metadata callback/detector insertion and public FlowMetadata API;
VCS installation metadata confirms the pinned commit. Semantic IDs use instruction
tags, leaving detector coordinates as (x,y,t). No upstream source changed.

Final local Linux/WSL2 Python 3.12.7 checks:

- `python -m pytest`: **263 passed in 169.48 s**; all 221 M1–M5 regressions
  retained, with only the two explicit Knill annotation-policy cases migrated.
- Focused causal/global/frame/boundary suite: **44 passed in 25.17 s**.
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: source distribution and wheel built successfully.
- All three existing examples passed; ideal/noisy memory, Bell and Knill DEMs
  validate, with seeded ideal detector samples identically zero.
- Isolated built-wheel import with decoder/test/reference imports blocked:
  memory, Knill, canonical/legacy DEMs, causal ancestry and noisy hypotheses passed.
  Wheel/source archives exclude local briefs, environments and external clones;
  the source archive retains the new tests.
- `python -m pip check`: no broken requirements. `git diff --check` passed;
  all four external source working trees remain clean.

New tests independently reconstruct every global detector parity/order at d=3/5
from raw Stim records over 256 shots and compare to Stim's m2d conversion. They
verify all Bell branches, full/legacy physical and fault-location equality,
registration-order invariance, open continuation, causal isolation and physical
reference entanglement. Negative stage/index/edge/sign tests fail as intended.
Noiseless selected correction execution/tableau proofs and exact once-only noise
regressions from M5 remain intact. Noisy-hypothesis tests include a final-check
measurement-result fault, actual noisy samples, deliberately wrong logical
hypotheses, malformed sources/supports/signs, and immutable repeatable replay.

The d=3 Knill example now has **52** open global detectors (legacy view: **44**),
including **8** cross-stage candidates. After two SE rounds, H and Z readout it
has **51 qubits, 99 measurements, 72 global detectors, 1 observable**, and **946**
DEM error mechanisms under the example noise model (legacy view: **56 detectors**).
At d=5 the analogous open artifact has **252** global detectors, **228** legacy
view detectors and **24** boundary candidates. These count changes are deliberate
annotation recovery, with identical physical sampling circuits.

Implemented but unverified: no additional M6-A behavior is claimed. Local checks
do not establish Windows coverage; post-push CI results are separate.
Remaining work: general noise-preserving DEM projection and decoder views (M6-B),
ordinary/Knill memory decoding demonstrations (M6-C/D), batch correction adapters,
noisy sector inference and LER. Ancestry conservatively retains histories after
actual interactions, including operations that later undo entanglement. The
legacy view does not establish independent stage fault models. Production decoders,
adaptive operations and block reuse remain deferred. Commit/push is explicitly
authorized by the user after verification; local briefs/artifacts remain excluded.

## M5 implemented and verified — 2026-11-07

Baseline local/remote commit: `f1a37d33bd5c4ca0e65a35f42516113d65d0b835`.

- BellStatePrep/KnillEC composite expansion reuses verified primitives, with
  parallel d-round X/Z resource preparation, optional existing resources, child
  operation/parent/stage IDs, and preserved primitive noise selection.
- Explicit random destructive readout retains conditional physical state flows;
  Bell bits are classical records, never deterministic logical observables.
- Knill relocates persistent logical D to physical B, retires D/A blocks and A/B
  resource identities, and retains current/open mappings and relocation history.
  Subsequent SE/H/CNOT/physical and virtual Paulis and readouts are supported.
- Open artifacts retain verified flow interfaces and faithful physical circuits
  without magic MPP/terminal measurements. append recompiles prefix/continuation.
  The default closed-memory completion check remains for backward compatibility.
- PhysicalPauliFrame and preparation/check/readout/Bell metadata preserve full
  syndrome histories, stable data support, orientation, stage/source dependencies,
  unresolved status, affine byproducts, and residual physical/logical frames.
- The external correction boundary validates CSS equations and the prepared
  logical eigenvalue, then propagates actual physical pairings, measurement
  anticommutation, virtual Paulis, and Bell byproducts exactly once. Unresolved
  corrections are rejected by the Knill interpretation API; no adaptive gates
  or production correction selector enters the primary circuit.
- Complete global physical flows and DEM validity are checked before an explicit
  detector-boundary policy excludes cross-stage annotations. Excluded relations
  retain raw parity/provenance metadata; preparation detectors remain local,
  sector-valued Bell checks remain raw metadata, and M3 correlations remain intact.

### M5 evidence

The unchanged pins are Stim **1.15.0** and stimflow **1.17.dev0** at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. PyMatching **2.3.1** is pinned
only in the development extra; tests import it unconditionally. Its required
helper under tests/ solves final noiseless preparation sectors with Matching(H_Z)
for x and Matching(H_X) for z, checking actual semantic record ordering, physical
vector lengths, and H_X z=s_X / H_Z x=s_Z. It performs no temporal fault inference.

Verified independent physics includes nonzero preparation gauges across seeds,
physical corrected Bell XX=ZZ=+1 and random singles, all four input states at
both d=3/5, all Bell branches, reference-data entanglement after teleportation,
actual correction execution on a separate Stim simulator, rotated pairings,
continued computation, and negative vector/matrix/order/mapping/orientation/
byproduct tests. Exact Knill noise tests count every gate/reset/result/idle fault
at d=3/5 and compare with independently spelled-out primitive circuits.

Final local verification in Linux/WSL2 Python 3.12.7:

- `python -m pip install -e ".[dev]"`: successful, PyMatching 2.3.1 installed.
- `python -m pytest`: **221 passed in 123.93 s** (all 173 original tests retained).
- Focused Knill teleportation/boundary/noise checks after the final provenance
  refinement: **29 passed in 54.65 s**.
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: source distribution and wheel built successfully.
- `python -m pip check`: no broken requirements.
- All three requested examples passed; ideal/noisy DEMs and seeded sampling valid.
- Built-wheel import from an isolated target: Knill generation, open continuation,
  ideal/noisy DEMs pass with PyMatching imports blocked. Wheel metadata makes
  PyMatching dev-only; the runtime wheel excludes tests and external source.
- Source/wheel archives exclude local briefs, environments, and external clones;
  the source distribution retains required test helpers. All four external source
  working trees remain clean. `git diff --check` passed.
CI includes Ubuntu/Windows Python 3.11/3.12, the required PyMatching tests, Ruff,
build, and all three examples. Post-push CI results are reported separately.

The decoder-independent Knill example ends open with 51 qubits, D->physical_B,
44 preparation/input detectors, 74 raw records, no observables, and 8 excluded
cross-stage detector relations. Continuing with two SE rounds, H, and Z readout
produces **51 qubits, 99 measurements, 56 detectors, 1 observable**; the selected
uniform-noise model gives **549 DEM error mechanisms**. Noisy decoded recovery
or logical error rate is claimed.

Pinned API inspection: Hex commit `5de58f2f80791054411ad3c0885a4fe3671ed56a`
separates preparation corrections and Bell measurement correction maps; this
informs metadata boundaries without importing Hex. Pinned ChunkReflow requires
square generator changes and has a defective nonsquare diagnostic; supported
square reflows plus physical measurement/export Chunk boundaries avoid that path.
No external source or dependency pin was changed.

Production preparation/SE/Bell decoders, noisy sector estimation, stage DEM/window
slicing with correlated faults, gauge matching/PAL/IRS, LER, and adaptive/retry
policies remain deferred in docs/deferred_work.md and decoding/STATUS.md.
No GitHub issue creation is claimed. User authorization includes commit and push
once verification completes. External clones, local briefs, environments, and
build/sample artifacts remain excluded.

## Prior M3 implementation and verification

- Multi-block OperationContext/ModuleFragment interfaces, one shared ordered CNOT
  fragment, scalar memory compatibility, atomic state updates, and overlap rejection.
- Physical transversal H with a binary code frame, all four equal-distance CNOT
  orientation combinations, and physical/virtual logical X/Y/Z.
- Signed physical check/logical flows, verified CNOT check reflows, and joint
  logical-state flow ports that preserve Bell correlations.
- Affine symbolic frames, syndrome-dependent H representative changes, final
  interpreted measurement bits, and signed proofs of observable parity/sign.
- Cross-block detector anchors/support/provenance and H/CNOT/Pauli noise overrides,
  with exact once-only gate/idle faults and zero-duration virtual operations.
- `examples/two_patch_bell_roundtrip.py`: independently verified intermediate XX=ZZ=+1,
  individual logical X/Z expectations zero, and final raw logical Z outputs (0,0).
  Distance 3 with R=3: **34 qubits, 64 detectors, 2 observables, 30 layers**;
  **16 detectors** use records from both blocks. Noisy DEM and seeded samples pass.

### M3 verification (2026-11-07)

Baseline local/remote commit at start: `d6a023c12ea223d7766da1600aa0fb0b91b8bf84`.
Dependency pins are unchanged: Stim **1.15.0**, stimflow **1.17.dev0** at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. The source-of-truth memory suite
continues to pass. Final checks in the existing Linux/WSL2 Python 3.12.7 environment:

- `python -m pytest`: **173 passed in 144.89 s** (including all 79 memory regressions).
- `python -m ruff check src tests examples`: **all checks passed**.
- `python -m build`: source distribution and wheel built successfully.
- Both `examples/two_patch_memory.py` and `examples/two_patch_bell_roundtrip.py`: passed.
- `python -m pip check`: no broken requirements.
- Built-wheel import from an isolated target: Bell round trip, virtual frame
  interpretation, and noisy DEM passed without importing this source checkout.
- Archive inspection excludes local briefs, environments, and external source;
  all four upstream source working trees remain clean.

CI retains Ubuntu/Windows Python 3.11/3.12 and now runs both examples. At local
verification time M3 remote jobs had not started; post-push results are separate.
The package pins and dependency versions from the memory environment below remain.

M3 tests include d=3/5 backend action proofs and corruption failures; all four
CNOT orientation pairs; raw truth tables and Pauli signs; twelve deterministic
random Clifford programs checked against a logical Stim oracle; affine frame and
partial-readout timing; exact multi-block faults; required/corrupted reflows; Bell
round trips at (d,R)=(3,1),(3,3),(5,1),(5,5), physical intermediate Bell stabilizers,
and invalid detector/frame/readout regressions. The original 79 memory tests remain.

The user explicitly authorized commit and push after implementation/verification.
Local briefs, environments, artifacts, and external source clones remain excluded.

## Memory-foundation implementation and prior verification

- Immutable CSS CodeSpec with algebra/rank/logical-basis validation and odd-distance
  square rotated-surface factory; validated PhysicalLayout and stable LogicalBlock.
- CodeBackend/RotatedSurfaceCodeBackend and signed memory initialization, N/Z
  syndrome-extraction, and destructive-readout chunks using public stimflow APIs.
- OperationModule, LogicalInit, SyndromeExtraction, LogicalMeasure, CompilerContext,
  ModuleFragment, CircuitCompiler, and CompiledCircuit with explicit parallel layers.
- One/two/three concurrent patches, mixed X/Z memory bases, unequal round counts,
  waiting blocks, stable logical/physical identities, and final Stim index metadata.
- Complete raw measurement, detector/observable parity, module/time-layer,
  initialization-syndrome, frame, and lifecycle provenance for memory.
- NoiseModel/NoiseParameters/NoiseOverride/NoiseInjector: circuit-level reset,
  Clifford gate, result, and global idle rules with replacement precedence and
  protection against reinjection. The ideal circuit is preserved.
- Runnable `examples/two_patch_memory.py`; installable source distribution/wheel;
  GitHub-independent pinned dependency installation; CI definition updated.

## Prior memory-core verification evidence (2026-11-07)

Local virtual environment: Linux/WSL2 x86_64, Python 3.12.7, Stim 1.15.0,
stimflow 1.17.dev0 at Stim commit
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`, NumPy 2.5.4,
SciPy 1.18.1, pytest 9.2.0, Ruff 0.17.4, build 1.6.1.

- `python -m pip install -e ".[dev]"`: successful, using the declared pinned
  GitHub stimflow source dependency without local-reference imports.
- `python -m pytest`: **79 passed** in 33.48 s.
- `python -m ruff check src tests`: **all checks passed**; the 22 pre-existing
  docstring E501 findings are resolved (future-operation files remain placeholders).
- `python -m build`: source distribution and wheel produced successfully;
  inspected archive contents exclude external source clones and generated caches.
- `python -m pip check`: no broken requirements. Imported the built wheel from
  an isolated target outside the source checkout and verified mixed-basis memory,
  logical IDs ordered differently from physical blocks, ideal sampling, and noisy DEM.
- `python examples/two_patch_memory.py`: **34 qubits, 64 detectors, 2 observables,
  26 physical layers**; ideal samples all zero, noisy DEM and seeded samples valid.
- Physics checks include signed primitive flows, deliberately corrupted physical
  gates/record parities/signs, nondeterministic first-syndrome detector rejection,
  raw parity reconstruction, and independent noisy circuit-distance searches that
  give distance **3 and 5** for both X/Z memory.
- Exact structural checks cover final reindexing, registration-order invariance,
  detector/check association, parallel depth, reset/result/gate/idle locations,
  instance/type/global replacement, zero-noise equality, and lifecycle rejection.

CI is configured for Ubuntu/Windows and Python 3.11/3.12. Those remote jobs have
not been executed in this task; local results do not establish Windows coverage.
All external source working trees remain unchanged. Remote CI results are separate
from these local verification results.

## Milestones and limits

| Milestone | Current state |
|---|---|
| M0 | Install/build/import and development workflow verified locally |
| M1 | CSS/layout/block models and memory backend contract implemented/verified |
| M2 | Three primitives and concurrent memory composition implemented/verified |
| M3 | H/CNOT/physical and virtual Paulis, affine frames, cross-block detectors, Bell round trip verified |
| M4 | Primitive/composite Clifford noise and synchronous timing verified; stage selectors deferred |
| M5 | BellStatePrep/KnillEC, random readout, open outputs, relocation, physical frame evaluation verified |
| M6-A | Canonical global detectors, causal preparation ancestry, exact metadata and frame-validation modes verified |
| M6-B | Exact physical-model marginals, semantic decoder views and batched software record transforms verified |
| M6-C/D | Ordinary/Knill decoding demonstrations and knill_bench integration deferred |
| Deferred | Text parser/CLI, other code families, scheduling optimization |

Current restrictions: one logical slot per block, no physical block reuse,
explicit logical barriers, and expanded output rounds. Readouts default to
deterministic; random readout and open outputs are explicit options. Waiting
active blocks use global idle defaults. Physical preparation correction selection
is external, with unresolved state retained until supplied. The test-only helper
resolves noiseless final sectors, without noisy fault inference. No general
code-distance solver, S/other logical Cliffords, production decoder, logical
error-rate benchmark, adaptive quantum operation, or parser/CLI is implemented.

Surface-sim revision `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` supplies the
geometry/schedule reference; Hex supplies a modular protocol reference. Neither
is imported. A project license has not been selected. Future work is explicitly
tracked in docs/deferred_work.md; knill_bench remains a downstream runner.

## Changelog

- **2026-11-08** — Implemented M6-B immutable decoder views, exact physical
  marginal DEM re-extraction, semantic/observable-local selectors, source IDs and
  batched GF(2) record frames. Added 105 tests and a one-batch example; all 368
  tests, lint, build and four examples passed. Full evidence and limits above.

- **2026-11-08** — Implemented M6-A canonical global detectors, causal preparation
  provenance, global metadata validation, explicit legacy stage views, and separate
  noisy-hypothesis/noiseless-proof modes. Added 42 tests; final 263-test suite,
  lint, build and all examples passed. See evidence and migration above.

- **2026-11-07** — Implemented M5 Bell/Knill composites, random readout and
  conditional flows, explicit open-output artifacts, logical relocation, external
  physical preparation-frame evaluation, and detector-region policy. Added 48
  physics/metadata/noise tests plus a decoder-independent Knill example, test-only
  PyMatching dev/CI coverage, deferred-work records, and current architecture/API
  documentation. Verification evidence above; commit/push explicitly authorized.

- **2026-11-07** — Implemented the M3 brief locally, preserving the memory API and
  tests. Added ordered multi-block operations, binary H code frames, affine frames,
  verified check reflow/known-state flow composition, correlated detector provenance,
  new noise selectors, Clifford/Bell physics tests, and the Bell example. Updated
  architecture, development instructions, public API, CI, and affected ledgers.
  Code and test evidence above; commit/push authorized by the user.

- **2026-11-07** — Prepared the verified memory-core changes for commit and push
  following explicit maintainer authorization. Corrected the local implementation
  brief's ignore rule to `/implementation_files/`; external source clones, local
  briefs, virtual environments, and generated artifacts are excluded from the
  commit. The 79-test, lint, build, and artifact verification results above apply.
- **2026-11-07** — Implemented the memory-core brief across core, backend,
  operations, compiler, noise, and public API; added physics/metadata/noise tests
  and the two-patch example. Updated dependencies, packaging manifest, CI,
  architecture/development/README, AGENTS, and affected folder ledgers.
  Found and fixed passive-flow detector-coordinate drift during waiting-patch
  testing by using no new flow center. Full verification and limitations above.
  User's existing `.gitignore` edit and implementation brief are preserved.
  Implementation was initially left local, uncommitted and unpushed for review,
  as requested by the brief.


- **2026-11-07** — Prepared the current scaffold for its initial GitHub upload:
  initialized local Git on `main` and created the private repository
  `https://github.com/AKTKN/logical_to_stim_converter` as `origin`.
  Only this status ledger changed during upload preparation; source placeholders
  remain unchanged. Verified that all four external source clones, caches, build
  output, and package metadata artifacts are excluded by `.gitignore`.
  With temporary verification tools outside the repository, `python -m build`
  produced the `0.0.0` source distribution and wheel, and
  `PYTHONPATH=src python -m pytest` passed the one scaffold import test.
  `python -m ruff check src tests` found **22 existing E501 docstring line-length
  errors**; these remain unresolved in this snapshot and affect CI.
  No physics functionality or runtime dependency integration was added or
  verified. Next: address the scaffold lint findings and begin M1 separately.
- **2026-11-07** — Read the package scaffold/design and external-reference guidance;
  cloned Stim/stimflow, surface-sim, Hex, and lomatching into the documented
  `external_lib/` folders. Updated `external_lib/README.md` and
  `external_lib/STATUS.md` with local availability, full commits, branches,
  source metadata, and untested installation entry points. Verified origin URLs,
  clean upstream working trees, and the presence of stimflow source classes.
  `PYTHONPATH=src python -m pytest`: **1 passed** (scaffold import only).
  Plain `python -m pytest` could not collect because the package is not installed;
  `python -m ruff check src tests` could not run because Ruff is absent.
  The workspace itself has no `.git` directory. No upstream source or package
  implementation changed; dependencies remain uninstalled and integration pins,
  physics/flow validation, and M1 remain pending.
- **2026-11-07** — Initialized documentation-first project scaffold. All source modules contain only explanatory docstrings; there is no implementation of requested QEC functionality. Initial status entries are plans, not verified results.

## Status update convention

For any implementation PR/task, record: date, changed source files, functionality added, tests run/results, upstream revision if used, outstanding issues, and next task. Update both this file and each affected folder's `STATUS.md`.
