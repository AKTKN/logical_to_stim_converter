# Research beta 0.0.1: decisions and verification

Dependency policy update (2026-11-11): version/pin tables below record the
original generation and verification environments. Current PyPI requirements use
minimum versions; stimflow retains its exact source commit. See the
[compatibility record](dependency_compatibility.md) and current
[development instructions](development.md). Historical results remain unchanged.


This package is a research dependency for trusted collaborators using
`knill_bench`, `lomatching` and similar external simulation repositories.
Distribution is through GitHub at a pinned commit. This is an internal research
beta, not a public product launch or a general open-source release.

## Approved decisions and boundaries

- Distribution version: exactly **0.0.1**, retaining distribution name
  `logical-to-stim-converter` and import name `logical_to_stim_converter`.
- Installation: GitHub source at a full commit SHA, with Git and network access.
  No PyPI upload, published release artifacts, GitHub Release, announcement,
  automatic tag or push is authorized by this phase.
- License: **not yet selected; decision deferred**. No license file, SPDX
  expression or redistribution permission is introduced. REL-01 remains partial.
- Root README: a concise entry point is approved for Phase 2. Phase 1 leaves it
  unchanged; detailed contracts/tutorials belong in `docs/`.
- The converter provides logical-to-physical Stim compilation, physical timing,
  noise/provenance metadata, canonical DEMs, use history and decoder-neutral
  offline record/frame/model interfaces. Decoder algorithms, LER runners/sweeps,
  factory policies and shot-dependent scheduling remain downstream.
- Existing M1-M9 semantics remain intact, including M9's [0, 0.75] policy range,
  post-final-SE data targets/cuts, patch reuse and conditional fault ownership.
  No production decoder or guaranteed long-term API stability is claimed.
- Execute one phase per maintainer instruction. Every executed phase includes
  this record and its verification evidence in one focused commit. No issue is
  automatically closed, and later phases are not authorized by Phase 1.

## Integration pins and support envelope

Inspected baseline: `d8654898e22248ba23afa9a65032eb7a9d83d075` on `main`,
2026-11-09. Its metadata declares Python >=3.11 and:

| Runtime dependency | Integration requirement |
| --- | --- |
| Stim | `stim==1.15.0` |
| stimflow | Git commit `ffe0d043598ed5df0851a3e6b4920359a23fafbd`, `glue/stimflow` subdirectory of quantumlib/Stim; installed version `1.17.dev0` |
| Lark | `lark==1.3.1`; grammar included in wheel and sdist |
| NumPy | `numpy>=1.26` |
| SciPy | `scipy>=1.11` |

These declarations are unchanged by Phase 1; they are not a complete transitive
lockfile. Installation needs a compatible Stim wheel, Git on PATH, access to the
converter/stimflow Git sources and package/build dependencies. Nothing imports
an `external_lib` source checkout. See [installation and development](development.md)
for the full-SHA placeholder recipe and optional `.[dev]` tools.

The baseline [CI run 42552076079](https://github.com/AKTKN/logical_to_stim_converter/actions/runs/42552076079)
was inspected: Ubuntu/Windows x Python 3.11/3.12 all completed successfully.
Those are baseline results, not CI for the unpushed Phase 1 commit. The existing
workflow runs pytest with eight workers, Ruff, build and nine examples. Local
Phase 1 verification uses Linux/WSL2 Python 3.12.7, Stim 1.15.0, stimflow
1.17.dev0, Lark 1.3.1, pytest 9.2.0/pytest-xdist 3.8.0, Ruff 0.17.4 and build 1.6.1.
Other platforms/Python versions have not been certified here.

## Phase ledger

### Phase 1 — Version and GitHub installation policy (2026-11-09)

**Objective and issues:** Establish the approved research-dependency identity and
install policy. [#1 REL-01](https://github.com/AKTKN/logical_to_stim_converter/issues/1)
is partially addressed; license-dependent acceptance remains pending. Inspected
#2-#7 for context; their broader consumer/docs contracts remain later work.

**Commit subject:** `Prepare v0.0.1 research beta: establish GitHub installation policy`

**Isolation:** Baseline `main` has unrelated user edits to README, manifest,
status, examples and exported artifacts. Work proceeds on branch
`research-beta-0.0.1-phase1` in a separate worktree so those bytes and the original
checkout's branch/index remain intact. No reset, rebase or upstream edits.

**Affected files and changes:**

- `pyproject.toml`: change only distribution version 0.0.0 -> 0.0.1.
- `docs/development.md`: focused full-commit GitHub install instructions,
  prerequisites, version verification, runtime/dev distinction, support evidence
  and pending license; correct the current CI example count to nine.
- This record: approved decisions, integration pins, phase scope and evidence.
- `tests/test_lstim_packaging.py`: extend the existing private-tree wheel/sdist
  test with version/name/Python/runtime-requirement metadata checks, absence of
  unapproved license metadata and installed-distribution identity. Retain its
  existing public LSTIM/noisy/M9 consumer checks with optional imports blocked.
- Root `STATUS.md` and `tests/STATUS.md`: current pointers/evidence, leaving all
  historical checkpoint results intact.

**Rationale and compatibility:** Keep the existing packaging/test approach and
public import paths. A metadata-only version change avoids altering physical
circuits, flows, detector/observable IDs, noise, patch epochs or model schemas.
Git pins reproduce source identity while allowing existing declared dependency
ranges; a full transitive lock and a public distribution mechanism are outside
this phase. The placeholder must refer to a commit containing 0.0.1, not the
historical 0.0.0 baseline or a fabricated version tag.

**Verification performed:** Commands below use the existing Python 3.12.7 dev
environment for tests/build and a separate temporary virtual environment for the
runtime-only consumer. `PYTHONPATH=src` selects this worktree during pytest;
the installed consumer runs from outside both source checkouts with `-I`.

| Command/check | Observed result |
| --- | --- |
| `PYTHONPATH=src python -m pytest -n 8 tests/test_lstim_packaging.py tests/test_lstim_api.py --tb=short --durations=5` | **26 passed in 8.68 s**, eight pytest-xdist workers; includes the existing isolated-wheel memory/three-patch/M9 consumer |
| `python -m ruff check src tests examples` | All checks passed |
| `git diff --check` | Passed |
| `python -m build --outdir <temporary-directory>/dist` | Isolated build passed: `logical_to_stim_converter-0.0.1.tar.gz` and `logical_to_stim_converter-0.0.1-py3-none-any.whl`; wheel built from the sdist |
| Archive metadata audit with `email.parser.BytesParser`, `tarfile` and `zipfile` | Wheel/sdist both declare 0.0.1 and no license expression/text; packaging test also verifies name, Python requirement, runtime declarations and grammar |
| `python -m venv <temporary-directory>/consumer-venv`, then its `python -m pip install <wheel>` | Passed without `.[dev]` or system-site packages; pip used cached artifacts including the wheel for the exact pinned stimflow Git revision |
| Fresh environment `python -c "from importlib.metadata import version; print(version('logical-to-stim-converter'))"` | Printed `0.0.1` |
| Fresh environment `python -I` public LSTIM smoke (source below) | Metadata/DEM validation and physical sampling passed: 17 qubits, 49 records, 40 detectors, 1 observable, raw shape `[4,49]`; four ideal shots had zero events/observable flips |
| Fresh environment `python -m pip check` | No broken requirements found |
| Parsed baseline/current `pyproject.toml` comparison and scoped Git diff | Only version differs; dependencies, runtime source, README, manifest and CI unchanged |

The fresh consumer blocks imports of `examples`, `tests`, `external_lib`,
PyMatching, Matplotlib, Hex, surface-sim, `knill_bench` and `lomatching`; it also
checks optional decoder/test distributions are absent and the imported converter
is inside the fresh environment. It compiles this inline source with public
`parse_logical_circuit(source).compile(noise_model=NoiseModel.uniform_depolarizing(.001))`,
validates metadata, extracts the native DEM and samples once with seed 11:

```text
FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z(3) D
SE(2) D
MZ D
```

Resolved direct runtime versions in that environment were Stim 1.15.0,
stimflow 1.17.dev0, Lark 1.3.1, NumPy 2.5.4 and SciPy 1.18.1. No optional decoder
is needed for this compile/DEM/sample smoke. No noisy decoding performance claim
follows from it.

**Acceptance progress:** The explicit version, wheel/sdist metadata,
runtime-only installed import/compile, installation guidance and committed
decision record address the Phase 1 subset of REL-01. The license decision/SPDX
criterion remains pending. Existing wheel consumer checks provide focused
regression evidence; the larger REL-02 workflow is still Phase 4.

**Original Phase 1 verification limits:** The full test/example integration gate
was not rerun at that checkpoint; the planned final gate remains Phase 5.
Windows/Python 3.11 Phase 1 execution and new remote CI
were not run; the four successful remote jobs cited above belong to the baseline.
The GitHub install command uses an explicitly marked future commit placeholder:
no 0.0.1 commit had been pushed at that checkpoint, so remote installation was
not attempted. Cached stimflow resolution is not a new cold Git-clone verification.
Local wheels/sdists, environment and sampled arrays are not committed or published.

**Outstanding decisions and next phase:** License and associated SPDX metadata
remain undecided; #1 stays open. Phase 2 (documentation navigation and concise
README) requires separate instruction. API reference, fuller installed-consumer
tutorials and the final integration gate remain Phases 3-5. No push, tag, release,
publication, issue closure or dependency change is part of Phase 1.

## Follow-up integration and push handoff — 2026-11-09

The maintainer subsequently requested committing/pushing the latest local changes
and making the worktrees clean. This separately authorizes the Git push deferred
by the original Phase 1 instruction; it does not authorize Phase 2, a license,
tags, releases, PyPI publication or issue closure.

The reviewed inspection/export work is preserved in commit `aeeeabc`: six exact
Stim snapshots, the exporter, Japanese guide, 1,552-row map and sdist manifest,
plus removal of eight old ordinary-memory report/figure/log files. README now
links to their historical Git version. Phase 1 commit `6072ab0` is retained and
merged into `main`, rather than rewriting either history. Both worktree branches
are intended for the authorized push. Runtime source is byte-identical to the
M9 baseline and the metadata change remains version 0.0.0 -> 0.0.1 only.

**Integration commit subject:** `Integrate v0.0.1 beta with reviewed circuit exports`

**Verification before that commit/push:**

- `python -m pytest -n 8 --tb=short --durations=10`: **1367 passed in 384.11 s**.
- `python -m ruff check src tests examples` and Git whitespace checks: passed.
- Copy build inputs with the existing private-tree helper, then
  `python -m build --outdir <temporary-directory>/dist`: passed; wheel and sdist
  both report 0.0.1, exact runtime/grammar bytes match, requirements are unchanged,
  no license assertion is added, and all nine inspection assets ship in sdist.
- A new virtual environment installed the built wheel with runtime dependencies
  only. With optional/example/test/reference imports blocked, installed public
  APIs compiled both supplied LSTIM inputs, validated metadata, extracted native
  DEMs and sampled four raw shots: memory `[4,49]`, three-patch `[4,255]`.
  Ideal events/observable flips were zero. M9 enabled compilation retained six
  resource boundaries and all three conditional Bell models with 54 atoms each.
- Installed distribution version is 0.0.1; `python -m pip check` passed.
- The prior export review verified every CSV instruction/provenance row and
  reproduced all six snapshots byte-for-byte in a temporary directory. The
  metadata-only integration changes none of those programs or runtime sources.

These are local Linux/WSL2 Python 3.12.7 results. The successful four-job CI run
cited earlier remains baseline evidence; new push/CI outcomes are reported only
after observing them. This handoff does not complete the remaining beta phases
or the unresolved license-dependent acceptance of REL-01.

## Phase 2 + Phase 3 — Documentation and public consumer API (2026-11-09)

**Scope and authorization:** The maintainer requested the combined phase brief,
parallel pytest verification, one commit and a push, then reiterated “Commit and
push it.” This explicitly authorizes the Git push deferred by the brief's default
restriction. It does not authorize later phases, tags/releases, publication,
license selection or issue edits/closures. Baseline `main` and reachable remote
main both resolved to `8a409593ab09441c189ec3fe8742ab3f64055cce`; the working tree
was clean, so no isolation worktree was needed and no unrelated edits were staged.

Read root AGENTS/STATUS, the Phase 1 ledger, manifest/CI/metadata, live root and
decoding exports, signatures, source and physics/API/packaging test usage.
Read the current descriptions and all comments for #1–#7 through the GitHub
connector, including #4's M9 injector/boundary addendum. Main targets are
[#3 DOC-01](https://github.com/AKTKN/logical_to_stim_converter/issues/3) and
[#4 DOC-02](https://github.com/AKTKN/logical_to_stim_converter/issues/4).
#2/#5 inform consumer needs without authorizing Phase 4; #6/#7 remain detailed
P1 physics/worked-example documentation rather than automatically completed work.

**Commit subject:** `Document v0.0.1 consumer API and reconcile current scope`

### README relocation map and changed files

The inspected README had **987 lines**; the new entry point has **108**. It
contains one 18-line standalone Python quick start, capabilities/limits, a reachable
full-SHA 0.0.1 install, short navigation and pending-license text. Existing
physical explanations were mapped before removal:

| Old README material | Authoritative destination / treatment |
| --- | --- |
| Installation and test/dependency detail | README minimum plus [development](development.md); replace stale local/unpushed placeholder with reachable Phase 1 integration |
| LSTIM source/format/file/errors and certification | Existing [usage](lstim.md), [v1 contract](lstim_v1.md), [certification](lstim_certification.md); new [API language entry points](api_reference.md#language-entry-points) |
| Two-patch memory and ordinary-memory decoding | New [examples guide](examples.md#ordinary-memory); source example, graphlike/correlation limits, reference-relative labels and preserved historical report URL |
| Explicit BindPatch reuse and use-specific selection | Existing [architecture glossary/use contracts](architecture.md#identity-and-lifecycle-glossary-m7-a), new [API identities](api_reference.md#identities-and-physical-meaning) and [view contracts](api_reference.md#decoder-views-and-index-maps) |
| Interfaces/metadata/affine frames and canonical-detector migration | New [compiled artifact](api_reference.md#compiler-and-compiled-artifacts) and [metadata](api_reference.md#measurement-and-protocol-metadata) reference; existing architecture preserves detailed physical contracts |
| Noise and M9 | Existing architecture/noise and [M9 guide](resource_preparation_noise.md), plus [API policy/injector contract](api_reference.md#noise-policy) |
| H/CNOT/Bell round trip and Pauli modes | New [Clifford example guide](examples.md#logical-clifford-and-bell-round-trip), existing orientation/flow/affine architecture sections and executable source |
| Bell/Knill/open continuation and preparation frame selection | New [open continuation example](examples.md#knill-relocation-and-open-continuation), existing physical-frame architecture, new [frame API](api_reference.md#offline-frame-plans-and-corrections) |
| Offline views, record flips, stages and conditional models | New API sections with shapes/order/source/errors and executable fragments; detailed existing architecture and M9 boundary guide remain authoritative |
| M6-D fresh resources and M7-C repeated three-patch decoding | New [external examples](examples.md#external-knill-decoding-demonstrations), existing [three-patch guide](three_patch_knill.md); retain explicit limitations/timing and distinguish source adapters from installed runtime |
| Physical text/line-map inspection | Preserve navigation to [Japanese guide](../examples/stim_circuit_guide_ja.md), CSV, snapshots and exporter through README/examples/index |
| Milestone status / future work / obsolete local report link | New [index matrix](index.md#current-implementation-and-limitations), reconciled [deferred work](deferred_work.md); old outcomes stay historical in STATUS and old ordinary-memory reports retain a commit URL |

Changed files: README; docs/index.md, api_reference.md and examples.md (new);
architecture.md, deferred_work.md, development.md and future_logical_syntax.md;
this ledger; root STATUS.md and new docs/STATUS.md. No source, test, manifest,
workflow, version, dependency, license or external reference source changes.

**Rationale and API decision:** Keep documentation organized around consumer
contracts rather than copying the old README or generating a source dump. The
index matrix links supported M7/M8/M9 behavior and limitations to source/tests.
The reference documents actual public import paths, signatures, metadata,
record/index/array ordering, source-bound correction hypotheses, raw immutability,
exact physical marginal DEMs versus categorical conditional Bell actions, and
private/example boundaries. Documented consumer APIs target internal 0.0.1
integration without promising durable semantic versioning for all low-level root
exports. The reachable install pin fixes runtime source, not transitive ranges.

### Verification and acceptance

Local execution uses Linux/WSL2 Python 3.12.7, pytest 9.2.0 / pytest-xdist 3.8.0,
Ruff 0.17.4 and the unchanged pinned integration. Temporary build source,
distributions, checking scripts and the fresh consumer environment are outside
the checkout. Build inputs use the existing private-tree helper so parallel
setuptools tests do not race with the manual build.

| Command/check | Observed result |
| --- | --- |
| `git status --short --branch`, `git log -4`, `git ls-remote origin refs/heads/main` | Clean main at reachable full SHA `8a409593ab09441c189ec3fe8742ab3f64055cce`; its metadata declares 0.0.1 |
| Live `inspect.signature`, annotations, exported names and source/test inspection | Reference reconciled with actual language/compiler/noise/decoding APIs, fields and consumer array conventions |
| `.venv/bin/python -m ruff check src tests examples` | All checks passed |
| Private `copy_package_source`, then `.venv/bin/python -m build --outdir <temporary-directory>/dist` from the copied tree | Isolated build passed; 0.0.1 sdist and wheel built, with wheel built from sdist |
| Wheel/sdist audit with `BytesParser`, `tarfile`, `zipfile`, current pyproject and exact source bytes | Correct version/name/Python/dependencies, no license assertion; new README metadata payload matches; runtime/grammar bytes unchanged; new guides included in sdist |
| `.venv/bin/python -m venv <temporary-directory>/runtime-venv`, then that environment's `python -m pip install <wheel>` | Fresh runtime-only install passed; no dev extras/system-site packages. Exact pinned stimflow wheel resolved from pip cache, not a new cold Git clone |
| Fresh environment `python -I <temporary-directory>/verify_snippets.py <checkout> <environment>` from an outside-checkout consumer directory | All **7** new Python blocks pass: standalone README, four connected API blocks and two independent practical-example blocks. Converter imports verified inside environment, optional/test/example/reference/downstream imports blocked, optional decoder/test distributions absent |
| Installed README output / independent ideal check | Prints `17 40 1`; raw shape `[4,49]`; ideal four-shot events and observable flips all zero; noisy native DEM and metadata validation pass |
| Installed view/stage/frame and M9 example checks | Caller record permutation, event reconstruction, stage target shape, source/use/column-bound identity correction and unchanged raw batch pass; M9 example has two resource boundaries and 639 categorical fault atoms, native canonical DEM valid |
| Fresh environment `python -m pip check` | No broken requirements found |
| Lightweight relative-link/anchor checker over README, all docs and Japanese inspection guide | All relative filenames/anchors resolve; ignores fenced/inline code and checks GitHub-style heading slugs. Final count recorded below |
| `git diff --check` and docs/source scope review | Passed; documentation-only change, no runtime/decoder behavior or upstream source modified |

The first temporary link audit exposed an incorrect version-heading anchor, which
was fixed; code-like LSTIM labels were then excluded from link parsing. An initial
metadata audit compared a MIME-decoded replacement string for Unicode; decoding
the raw payload as UTF-8 fixed the checker and the exact README comparison passed.
Neither audit required changing package behavior. Fresh runtime direct dependency
versions were Stim 1.15.0, stimflow 1.17.dev0, NumPy 2.5.4, SciPy 1.18.1 and Lark 1.3.1.

**Document review:** Checked current/deferred claims across README, architecture,
deferred work, development and future syntax. Removed present-tense M7/M8/M7-C
contradictions and the stale claim that assembly-derived Pauli maps/conditional
models remained unimplemented. Retained historical records and the intentional
old-report Git URL. Documentation contains no machine-specific installation paths,
new dead artifact links, invented tag, license permission or decoder optimality /
threshold guarantee. Exact M9 [0,.75], enabled-zero, direct omitted-versus-empty
boundary contract and intermediate-operand-SE rejection are preserved.

**Acceptance progress:** #3's current implementation reconciliation/matrix and
#4's consumer API/glossary documentation are addressed in this combined phase,
with source/test links and actual installed snippet evidence. No issue is closed
or edited. Detailed #6/#7 worked single-fault/epoch guides are not claimed complete.

**Remaining work and limits:** Phase 4's fuller public-only installed-consumer
StageDecoder workflow and two end-to-end tutorials (#2/#5), Phase 5's final beta
integration gate and the license decision (#1) remain separate authorization.
The nine workflow CLI examples are not separately rerun in this documentation
phase; their underlying regression tests run in the full suite. Windows/Python
3.11 and new remote CI are not executed/claimed here. No cold-cache Git install,
release/tag, upload, published artifacts or numeric LER/threshold certification.

**Final parallel regression:** `.venv/bin/python -m pytest -n 8 --tb=short
--durations=10` passes **1367 tests in 365.99 s**, eight workers, no failures or
skips. This includes existing focused packaging/API tests and all signed-flow,
physical/noise/provenance/reuse/LSTIM/decoder-neutral regressions. No runtime
implementation is left unverified by a new source change because source is
unchanged. All newly authored executable Python blocks are separately verified
as described above; broader deferred capabilities are not implied.

**Final link review:** **204 relative links across 16 documents** resolve,
including exact heading anchors and new status/ledger navigation. Root status's
new relative targets were also checked. The final package build is refreshed
from the completed documentation tree; local artifacts stay outside Git.

## Phase 4 — Installed consumers and tutorials (2026-11-09)

**Authorization/dependencies:** The maintainer requested Phase 4 implementation,
testing, commit and push. This explicitly authorizes the Git push deferred by
the file brief; it does not authorize Phase 5, a license, tags/releases, artifacts
publication or issue edits/closures. The clean starting `main` is the committed
Phase 2 + Phase 3 revision `e41c16e4fbdbf98274cc2adbe16ed0c68ea5cc5a`.
Its concise README, docs index, API reference and reconciled current-state claims
were verified before implementation; Phase 1/2+3 history remains intact.

Read current bodies/comments for
[#2 REL-02](https://github.com/AKTKN/logical_to_stim_converter/issues/2),
[#5 DOC-03](https://github.com/AKTKN/logical_to_stim_converter/issues/5),
[#4 DOC-02](https://github.com/AKTKN/logical_to_stim_converter/issues/4) and
[#7 DOC-05](https://github.com/AKTKN/logical_to_stim_converter/issues/7).
Inspected root/folder instructions/status, existing CI/private-wheel path,
M6-D/M7-C source consumers, public exports/signatures and stage/frame/M9 physics
contracts. Stim 1.15.0, stimflow 1.17.dev0 at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd` and Lark 1.3.1 remain unchanged.

**Commit subject:** `Add public-only installed consumers and memory/Knill tutorials`

### Architecture and artifacts

- [examples/installed_consumer.py](../examples/installed_consumer.py): one
  self-contained external asset (259 lines), copied by the user/test outside the
  checkout. Imports only public root/decoding APIs, NumPy and standard library.
  Its CLI accepts a separately supplied source and samples once; analysis functions
  have no sampler or hidden physical-fault input. No runtime package files change.
- The two unchanged inputs are [ordinary memory](../examples/lstim/memory_d3.lstim)
  and [three-patch Knill](../examples/lstim/three_patch_knill_d3.lstim). The installed
  wheel supplies neither source files nor the consumer script; tutorials provide
  complete source text and a transparent script-copy instruction. All ship in sdist.
- [tests/installed_consumer_checks.py](../tests/installed_consumer_checks.py):
  copied as `consumer_checks.py` beside the external script, never imported as
  `tests`. Public-only workflow/import/source/use/shape/model checks reuse compiled
  artifacts from the existing isolated-wheel consumer. A single build serves all
  six new ideal/noisy/M9 subcases and the preserved prior packaging/API checks.
- [tests/test_lstim_packaging.py](../tests/test_lstim_packaging.py): extends the
  existing private source-tree build, metadata/archive and outside-checkout import
  path test. Verifies both tutorials contain the exact supplied source texts and
  the sdist contains the consumer; wheel continues excluding examples/tests.
- [tests/test_installed_consumer.py](../tests/test_installed_consumer.py): six
  source-tree physics/interface cases. Reuses independent public-operation authors,
  exact M8 equality helpers and the existing Stim conditional-atom oracle. Tests
  signed/multiple-observable labeling, strict frame replay and one actual sampler
  call per CLI workflow. Oracles stay in tests, outside consumer inputs.
- [ordinary tutorial](ordinary_memory_tutorial.md) and
  [Knill tutorial](knill_memory_tutorial.md): supplied inputs, runtime-only install,
  external commands, dimensions/orders, adapter hook, failure convention and limits.
  README remains 110 lines; index/API/example/development navigation and affected
  root/docs/tests/examples STATUS files point to the completed Phase 4 work.

**Why inference stays external:** The converter compiles a verified static physical
experiment and exports exact models/provenance and linear propagation. Decoder
algorithms, model assignment, hypotheses, empirical failure aggregation and adaptive
policies remain caller choices. The consumer's `ObservedSectorAdapter` implements
the public StageDecoder protocol with binary elimination: trust current last
records, select a CSS sector representative and impose the known initialization
logical constraint; predict zero last-result errors and no readout flips. Free
variables are zero, not minimum weight. It correctly resolves random noiseless
preparation sectors but is deliberately inadequate for general noisy inference.
No PyMatching or Matplotlib enters the consumer/runtime. Users can replace the
adapter without recompiling/resampling the physical batch.

### Physics, identity and model assumptions

Ordinary memory retains the canonical full DEM and a deliberately permuted exact
view: detectors (39,37,...,1), observable (0,), records (48,47,46,45). Full record
parities reproduce Stim m2d events/labels; selected record order does not truncate
physical measurement/noise history. The predictor receives events, not observable
truth. Failure is predicted XOR reference-relative actual flip, independently
checked against interpreted readout XOR prediction XOR intended value. A signed
2-observable test reverses IDs (1,0) and distinguishes intended 1 from reference
flip 0. Hyperedges/correlated components are retained, never forced into matching.

Knill uses all three labeled cycles, seven BlockUseIds, three relocations and
persistent D ending P0/2. Causal stage requests provide current interpreted
records/events and transported expected sectors. Source/use/column-bound
CorrectionBatch values are applied once; raw records remain immutable. Final
failure is corrected physical readout XOR intended value, without reapplying the
symbolic frame already represented by the frame plan. Independent strict physical
frame replay checks the noiseless result and full corrected record batch.

M9 checks six actual resource boundaries, exact .003 probability, data-only layout
targets, post-final-SE idle/TICK placement before actual resource CNOT and distinct
tags. Concurrent channels can be adjacent after the same TICK. Preparation prefixes
exclude their own post-SE channel, while retaining legitimate earlier-cycle faults.
Conditional models begin before the earliest relevant channel, preserving exclusive
X/Y/Z alternatives and raw/check/logical/survivor actions. M9-only windows have
54 atoms; mixed background windows have 639 here, with 54 specifically post-SE.
Existing independent Stim atom tests verify physical raw/survivor mappings, not
just model sizes. Incoming hypotheses and unsupported intermediate operand-SE
windows remain exactly as documented; #23 is not implemented.

The external wheel test rejects accidental optional imports and module path leakage
(including a synthetic noninstalled converter module), wrong binding to an active
patch, raw/stage/prediction/correction shapes/dtypes, stale source/conditional models,
wrong epochs, swapped columns and duplicate corrections. It prohibits quantum
execution during replay. A supported canonical circuit with intermediate operand
SE explicitly rejects its conditional model with UnsupportedProjectionError.

### Observed fresh runtime-only results

An independent private-source isolated build creates 0.0.1 wheel/sdist outside the
checkout. A new venv, without system site packages or dev extras, installs that
wheel. The exact pinned stimflow wheel resolves from cache, not a new cold Git
clone. A temporary `verify_runtime.py` runs all six CLI cases and both tutorial
Python blocks from the external consumer directory with optional/test/example/
reference/downstream imports blocked and converter module paths checked inside
the fresh environment. Installed versions: Python 3.12.7, Stim 1.15.0, stimflow
1.17.dev0, NumPy 2.5.4, SciPy 1.18.1, Lark 1.3.1.

| Workflow / policy | Raw bool shape | Events shape | Output/failure shape | Canonical DEM errors | Conditional atoms per Bell | Observed failures / 32 |
| --- | --- | --- | --- | --- | --- | --- |
| Memory ideal | [32,49] | [32,40] | [32,1] | 0 | n/a | 0 |
| Memory p=.001 | [32,49] | [32,40] | [32,1] | 492 | n/a | 3 |
| Knill ideal | [32,255] | [32,192] | [32,1] | 0 | 0/0/0 | 0 |
| Knill ordinary p=.001 | [32,255] | [32,192] | [32,1] | 2698 | 585/585/585 | 13 |
| Knill M9-only p_st=.003 | [32,255] | [32,192] | [32,1] | 138 | 54/54/54 | 1 |
| Knill p=.001 + M9 p_st=.003 | [32,255] | [32,192] | [32,1] | 1093 | 639/639/639 | 9 |

All use seed 41, one raw batch per case. Rates describe only the specified weak
baseline and tiny observed batches, not numerical LER accuracy, recovery guarantees,
performance or thresholds. The two tutorial Python snippets additionally replay
the same 32 rows and pass raw-immutability/label assertions. Fresh `pip check`
reports no broken requirements. Runtime/grammar/dependency/version/license metadata
and final archive/link checks are recorded with the final verification below.

Commands executed (temporary source/dist/env/scripts stay outside Git):

```text
.venv/bin/python -m pytest -n 8 tests/test_installed_consumer.py tests/test_lstim_packaging.py --tb=short --durations=5
.venv/bin/python -m ruff check src tests examples
copy_package_source(<temporary-directory>/source)
.venv/bin/python -m build --outdir <temporary-directory>/dist
.venv/bin/python -m venv <temporary-directory>/runtime-venv
<fresh-python> -m pip install <temporary-directory>/dist/logical_to_stim_converter-0.0.1-py3-none-any.whl
<fresh-python> -I <temporary-directory>/verify_runtime.py <temporary-directory> <checkout>
<fresh-python> -m pip check
git diff --check
```

Initial focused checkpoint: **5 passed in 17.77 s** (before two CLI-count cases
were added). An earlier installed-wheel attempt failed a newly authored assertion
that every channel must directly follow TICK, then another assertion incorrectly
excluded all prior-cycle channels from later preparation prefixes. The tests were
corrected to the existing physical contract above; no compiler/noise implementation
changed. Final focused and regression results appear below.

**Compatibility and remaining work:** Internal 0.0.1 consumer shapes/contracts are
now exercised from an actual built distribution, with no new runtime API, physics,
version, dependency revision, allocator, production decoder or adaptive controller.
This addresses the bounded public-only workflow/tutorial acceptance of #2/#5;
issues remain open/unmodified. Detailed P1 #6/#7 worked guides and production joint
inference are not claimed complete. Phase 5's complete suite/all-example/platform
integration gate and license choice remain separate tasks. The full suite and
nine-example CI matrix are not run as a Phase 5 gate here; this phase runs the
focused checks below and fresh runtime consumer/tutorial smokes. No new remote CI,
Windows/Python 3.11, cold-cache Git install, license grant, tag/release or publication
is claimed. Stop after this single authorized commit/push.

**Final focused regression:** `.venv/bin/python -m pytest -n 8
tests/test_installed_consumer.py tests/test_lstim_packaging.py tests/test_lstim_api.py
tests/test_epoch_stages_frames.py tests/test_record_frames.py
tests/test_resource_preparation_models.py tests/test_resource_preparation_e2e.py
--tb=short --durations=8`: **117 passed in 146.14 s**, no failures or skips.
This includes all six new local cases and the extended shared-build wheel consumer,
plus related API/epoch/frame/M9 d=3/5 signed same-raw regressions. Ruff
src/tests/examples and whitespace checks pass. The existing CI pytest command
collects these tests without requiring a new workflow job or extra runtime deps.

**Final documentation/package review:** README is 110 lines. **240 relative links
across 18 documents** resolve with exact filenames/GitHub-style heading anchors;
new root status targets also resolve. The final private-source build refreshes
wheel/sdist from the completed tree. Metadata checks retain 0.0.1, Python >=3.11,
exact runtime declarations and no license assertion; archive checks compare the
README payload, every runtime/grammar byte and all scoped source/docs/test assets.
Build products, environments, scripts/logs and sampled arrays stay outside Git.

## Phase 5 — Final integration gate and handoff (2026-11-09)

### Scope, source identity and authorization

The maintainer explicitly requested this gate, commit and push. That request
supersedes the brief's default no-push rule, without authorizing a version bump,
license, tag/release, PyPI upload, issue edits/closure or product launch. The clean
starting main and origin/main both identify pushed Phase 4 commit
**`c45bf1f19081b55a414db7183557a1ec34b9a797`**. Phase 1 integration `8a409593`,
combined Phase 2+3 `e41c16e` and Phase 4 `c45bf1f` are present and committed.
Read root/folder instructions/status, all documentation and its links/snippets,
public exports/signatures, package/manifest/CI configuration, prior phase records,
and current #1–#5 bodies/comments. No unrelated work needed isolation.

The current local source/wheel and the latest pushed GitHub revision were tested
separately **before this Phase 5 commit/push**. Local fixes below affect only docs
and ledgers; all installed Python/grammar bytes, physical behavior, version,
dependency declarations, tests and example code are identical to c45bf1f. A later
Phase 5 commit is not retroactively the SHA tested by the GitHub install command.

**Commit subject:** `Record final v0.0.1 integration gate and collaborator handoff`

### Gate 1 — Packaging and two installation routes

Distribution/import identities remain `logical-to-stim-converter` /
`logical_to_stim_converter`, version **0.0.1**, Python **>=3.11**. Runtime pins:
Stim 1.15.0, stimflow at **ffe0d043598ed5df0851a3e6b4920359a23fafbd**
(`glue/stimflow`, installed 1.17.dev0), Lark 1.3.1, NumPy >=1.26 and SciPy >=1.11.
Optional dev requirements retain PyMatching 2.3.1, pytest-xdist 3.8.0, Matplotlib,
pytest, Ruff, build, setuptools and wheel. They are absent from both fresh runtime
installations. No license/COPYING file or license metadata/assertion is introduced.

A private source tree made with the established copy_package_source helper avoids
parallel setuptools races. The declared setuptools backend builds sdist and a
wheel from that sdist with isolated build dependencies. Archive checks validate
name/version/Python/runtime and optional requirements, exact packaged grammar,
README metadata payload and runtime source bytes; docs/examples/input sources
belong to sdist, while the wheel has only runtime package/data and dist-info,
without examples/tests/external reference imports. Final source/docs bytes are
rechecked after the documentation fixes and completed ledgers.

Two new, separate venvs outside the checkout (no system site packages):

| Route / command | Observed result / identity |
| --- | --- |
| `<wheel-python> -m pip install <private-dist>/logical_to_stim_converter-0.0.1-py3-none-any.whl` | PASS; built wheel installed with runtime dependencies only. Initial private build reflects the c45bf1f runtime; final build refreshes changed docs/README, with identical runtime/grammar bytes. |
| `<github-python> -m pip install --no-cache-dir 'logical-to-stim-converter @ git+https://github.com/AKTKN/logical_to_stim_converter.git@c45bf1f19081b55a414db7183557a1ec34b9a797'` | PASS; actual network clone/fetch resolves converter c45bf1f and stimflow ffe0d043. Both wheels built from fetched Git sources, not a cached stimflow wheel. |
| `importlib.metadata.version('logical-to-stim-converter')` | 0.0.1 in both fresh environments |
| Installed `direct_url.json` audit | GitHub installation records requested_revision and commit_id equal to the full c45bf1f SHA; stimflow's commit_id is exactly ffe0d043598ed5df0851a3e6b4920359a23fafbd |
| Exact installed `.py`/`.lark` comparison to local src | PASS for every runtime/grammar file in both environments; no editable/check-out module leakage |
| `<wheel-python> -m pip check`, `<github-python> -m pip check` | Both PASS, no broken requirements |

Fresh verification runs with `-I` from an external consumer directory. Only the
standalone consumer asset and explicitly supplied LSTIM inputs are copied there;
optional/example/test/reference/downstream imports are blocked, distribution
absence is checked, and every loaded converter module resolves inside its venv.
Both routes parse, compile, validate metadata, extract canonical/view DEMs, build
stage/conditional/frame models and sample exactly one raw batch per consumer
case. No decoder replay resamples quantum state or edits physical raw records.

Each route freshly executes the six 32-shot seed41 cases:

| Workflow / noise | Raw bool shape | Global events shape | Logical/failure shape | Canonical DEM errors | Conditional atoms per Bell | Observed failures / 32 |
| --- | --- | --- | --- | --- | --- | --- |
| Memory, ideal | [32,49] | [32,40] | [32,1] | 0 | n/a | 0 |
| Memory, ordinary p=.001 | [32,49] | [32,40] | [32,1] | 492 | n/a | 3 |
| Knill, ideal | [32,255] | [32,192] | [32,1] | 0 | 0/0/0 | 0 |
| Knill, ordinary p=.001 | [32,255] | [32,192] | [32,1] | 2698 | 585/585/585 | 13 |
| Knill, M9-only p_st=.003 | [32,255] | [32,192] | [32,1] | 138 | 54/54/54 | 1 |
| Knill, ordinary p=.001 + M9 p_st=.003 | [32,255] | [32,192] | [32,1] | 1093 | 639/639/639 | 9 |

The complete reports agree between routes. They establish interface/source and
bounded reproducibility evidence, not numerical LER accuracy or correction of
all noisy shots. The observed-sector/identity-readout consumer deliberately
ignores temporal/joint fault likelihoods. Both routes use Linux/WSL2 x86_64,
Python 3.12.7, glibc 2.35, Stim 1.15.0, stimflow 1.17.dev0, Lark 1.3.1,
NumPy 2.5.4 and SciPy 1.18.1. These dependency versions were observed, not locked
beyond the project's existing declarations.

### Gate 2 — Fresh full regression and physical evidence

| Command/check | Observed result |
| --- | --- |
| `.venv/bin/python -m pytest -n 8 --tb=short --durations=10` | **1373 passed in 401.70 s**, eight pytest-xdist workers, no failures/skips |
| `.venv/bin/python -m ruff check src tests examples` | All checks passed |
| Private `python -m build --outdir <private-dist>` | Isolated sdist/wheel build passed; no shared checkout build output |
| All nine exact `.github/workflows/ci.yml` example commands | PASS, exit 0 each; complete commands listed below |
| `python examples/export_stim_circuits.py` in private tree | PASS; six .stim snapshots and complete CSV line map reproduce byte-for-byte |
| Fresh installed package/docs checks | PASS, both installation routes and every Python documentation block as detailed here |
| Git working/staged whitespace and scope audit | PASS; no runtime/test/example/dependency/CI/upstream source changes |

The full run freshly includes these focused physics/interface groups; prior phase
results are not substituted for this execution:

| Contract | Executed evidence / bounded conclusion |
| --- | --- |
| M7 reuse / relocation / epochs | test_patch_reuse, test_patch_reuse_knill_e2e, test_epoch_stages_frames, test_patch_reuse_offline_replay: repeated explicit three-patch uses, persistent D, reset frame removal and legitimate classical history |
| M8 source/direct equality | test_lstim_physical_equivalence, test_lstim_simulation_e2e, test_installed_consumer: independent public constructors, matched bindings/labels, exact ideal/noisy/DEM/metadata and same-raw replay |
| M9 exact physical noise | test_resource_preparation_noise, test_resource_preparation_e2e: disabled compatibility, Bell-owned reset/SE/result/idle suppression, ordinary D/spectator/waiting noise, post-final-SE data targets/tags, no duplicate injection |
| M9 probability / native DEM | Policy bounds/types for both flags, .75 endpoint, actual noisy native DEM and direct injector omitted/None/empty tuple contract; no capped channel or fallback |
| Canonical/global and local models | test_decoder_views, test_knill_decoder_views, test_epoch_views_noise, test_global_detector_provenance: full physical fault retention, exact marginals, hyperedges/correlated ^ components and global/local maps |
| Boundary / conditional models | test_resource_preparation_models and conditional atom tests: preparation probes before their own channels, exclusive categorical atoms and joint raw/survivor actions; intermediate operand-SE cut explicitly rejected |
| Offline frames / installed consumers | test_record_frames, test_frame_validation_modes, test_installed_consumer, test_lstim_packaging: same immutable raw batch, source/use/shape/column checks, once-only causal edits, strict noiseless replay versus noisy hypotheses |

Established example commands, run from a private copy with its src selected:

```text
python examples/two_patch_memory.py
python examples/two_patch_bell_roundtrip.py
python examples/knill_ec_single_round.py
python examples/offline_dem_views.py
python examples/memory_offline_decoding.py --suite --shots 128 --p 0.001 --seed 731
python examples/knill_memory_offline_decoding.py --suite --shots 64 --p 0.001 --seed 732
python examples/knill_memory_three_patch_reuse.py --suite --shots 32 --batch-size 13 --p 0.001 --seed 733
python examples/lstim_equivalence.py --shots 32 --p 0.001 --seed 826
python examples/knill_resource_preparation_noise.py --shots 32 --p 0.001 --p-st 0.003
```

Local dev tools: pytest 9.2.0, pytest-xdist 3.8.0, Ruff 0.17.4, build 1.6.1 and
PyMatching 2.3.1. The full suite ran concurrently with private example/build
verification; observed wall times are not performance assertions. Exact remote
CI results/commit identity are recorded separately below, without treating CI
configuration or a prior green commit as execution of the new local commit.

### Remote platform gate — exact pushed-source attribution

Inspected [Actions run 42575410209](https://github.com/AKTKN/logical_to_stim_converter/actions/runs/42575410209),
triggered by the authorized Phase 4 push of
`c45bf1f19081b55a414db7183557a1ec34b9a797`. The matrix has four observed jobs:

| Job | Observed status during local handoff | Conclusion / action |
| --- | --- | --- |
| test (ubuntu-latest, 3.11) | Completed successfully at final inspection | PASS for c45bf1f |
| test (ubuntu-latest, 3.12) | In progress in full regression at inspection | PENDING final completion |
| test (windows-latest, 3.11) | In progress in full regression at inspection | PENDING final completion |
| test (windows-latest, 3.12) | In progress in full regression at inspection | PENDING final completion |

The initial 2026-11-09 07:04 UTC (16:04 JST) inspection showed all jobs running;
a subsequent pre-commit inspection confirmed Ubuntu/Python 3.11 completed
successfully. The other three jobs were still in full regression at that final
inspection. Local Linux execution is PASS; complete current remote platform
coverage remains **PENDING** until the remaining jobs conclude. No workflow rerun
or remote mutation was needed/requested. Earlier green baseline run 42552076079
remains historical evidence only. This new local Phase 5 documentation commit
has no observed remote CI result before its final authorized push. These pending
external jobs are a verification limit, not a discovered physics defect.

### Gate 3 — Documentation review and scoped clarifications

Reviewed README, all docs pages, historical ledgers and inspection links. README
remains about 110 lines, with one compact standalone quick start. Verified public
import paths/signatures and all **13** fenced Python blocks from the installed
wheel: README/API continuation, independent practical examples, both installed
tutorials, LSTIM usage and M9 usage. Two contract fragments (v1 API/certification)
receive explicit public imports/source/noise/file context; they are not claimed
standalone. Checkout/sdist-context snippets receive copies of their input files,
never imports of examples/tests. Both tutorials give full separately supplied
source text and identify copied consumer assets versus installed wheel contents.

Narrow current-document fixes, without rewriting historical results:

- README, development and ordinary tutorial now pin the **actually installed**
  pushed c45bf1f revision. The development page identifies fresh uncached Git
  evidence and distinguishes it from the separate current local wheel.
- M9's initial sample path is explicitly checkout/sdist context, with an installed
  tutorial link. Preparation-prefix prose excludes its **own** post-SE channels;
  legitimate earlier-cycle channels remain. This matches freshly executed tests.
- The LSTIM specification describes its implemented inspection paths/package
  structure instead of leaving a former implementation instruction in present
  tense; no syntax/API behavior changes.
- Certification labels M8-D's eighth example as historical and states the current
  nine-example workflow. Current index/API/status navigation points to this gate.

No current claim of deferred M7/M8/M7-C functionality, automatic allocation,
production decoder, generic QLDPC/universal gates, stable production API, PyPI
release/tag or granted license was found. Detailed physics stays in docs; snapshots
remain optional inspection artifacts, not runtime inputs. Link/anchor and final
archive review results are appended below.

### Gate 4 — Criterion-by-criterion acceptance

PASS means the bounded internal-beta criterion has observed evidence, not issue
closure, release approval or a durability/decoder-performance guarantee.

| Issue / criterion | Artifact or fresh test | Result | Remaining action / risk |
| --- | --- | --- | --- |
| #1 REL-01: version/name/Python/dependency metadata | pyproject, final wheel/sdist audits, test_lstim_packaging | PASS | Source pin does not freeze every transitive dependency |
| #1 REL-01: real commit-pinned GitHub route | Fresh --no-cache-dir install at c45bf1f; converter/stimflow direct_url.json and runtime byte checks | PASS | Git/network and compatible package wheels remain prerequisites |
| #1 REL-01: license choice / SPDX-compatible grant | No selected license or license metadata introduced | **PENDING** | Owner must make the legal/release decision; #1 remains partial/open, not a general redistribution grant |
| #3 DOC-01: concise README / navigation / current scope | README, docs/index, architecture, deferred work, language milestones, link review | PASS | Historical outcomes remain dated; unsupported families/non-Clifford/adaptive scope stays deferred |
| #4 DOC-02: public imports, signatures, identity glossary | api_reference, root/decoding exports, installed snippets and full API regressions | PASS | Internal 0.0.1 paths only; no durable promise for every root low-level export |
| #4 DOC-02: shapes/order, source validation, exception limits | View/stage/frame/conditional docs; installed negatives and full epoch/record tests | PASS | Array width alone cannot establish source identity; noisy hypotheses do not prove recovery |
| #2 REL-02: built/installed public-only consumer | Extended private-wheel test, six fresh cases in each of two runtime-only environments | PASS | Consumer assets/inputs supplied separately; decoder algorithms remain external |
| #2 REL-02: current platform CI execution | Run 42575410209 at exact c45bf1f SHA | **PENDING** | Observe final conclusions for all four Ubuntu/Windows x Python 3.11/3.12 jobs; local full suite already passes |
| #2 REL-02: same-raw replay / decoder neutrality / source checks | test_installed_consumer, test_lstim_packaging, frame/stage tests, blocked replay execution | PASS | Illustrative observed-sector/identity-readout adapter is inadequate for general noisy inference |
| #5 DOC-03: reproducible ordinary memory tutorial | Full input, external script/commands, local/global maps and signed labels, installed snippets | PASS | Empirical rates are specific to supplied predictor and finite batch |
| #5 DOC-03: reused-patch Knill / M9 tutorial | Seven uses/three relocations, full input, public model/frame hook and conditional atom checks | PASS | Intermediate operand-SE conditional hypotheses remain explicitly unsupported; no optimality/threshold claim |

Issues #1–#5 remain open/unmodified. P1 #6/#7 detailed worked single-fault/temporal
inference guides are not silently completed by this gate.

### Confirmed defects, investigation risks and handoff

**Confirmed new runtime/packaging defects:** None found in this gate. The scoped
current-doc ambiguities above are corrected. Their reproducers are inspection of
c45bf1f's development/M9/spec/certification wording versus the existing executed
contracts; they did not require a physical/compiler/decoder change.

**Known limits, not new bugs:** The conditional post-SE window rejects an
intermediate operand preparation/SE measurement with UnsupportedProjectionError;
no workaround or #23 extension is introduced. Restricted modular MWPM and the
public-only observed-sector baseline can fail on noisy shots. General code
families, non-Clifford gates, allocation and adaptive execution remain unsupported.

**Unconfirmed investigation risks:** Performance/conditioning outside the documented
d=3/5 bounded matrix, larger static circuits, decoder optimality and broader
platform/transitive-version combinations are not certified. No failing reproducer
was found that would justify classifying these as confirmed defects or opening
duplicate issues. Remote coverage is attributed only to observed jobs/SHAs.

**Tested pushed install command** (Git/network access; no fabricated tag):

```sh
python -m pip install --no-cache-dir "logical-to-stim-converter @ git+https://github.com/AKTKN/logical_to_stim_converter.git@c45bf1f19081b55a414db7183557a1ec34b9a797"
```

For collaborator entry points use [README](../README.md),
[installation and pins](development.md), [public API/glossary](api_reference.md),
[ordinary memory](ordinary_memory_tutorial.md) and [three-patch Knill](knill_memory_tutorial.md).
Copy the linked standalone script and inputs outside the checkout as those pages
instruct. With only installed runtime dependencies, representative commands are:

```text
python -I installed_consumer.py memory memory_d3.lstim --p .001 --shots 32 --seed 41
python -I installed_consumer.py knill three_patch_knill_d3.lstim --p .001 --m9 --p-st .003 --shots 32 --seed 41
```

Use public parse/compile/metadata/DEM/view/stage/frame entry points; supply your
own decoder. Optional PyMatching/plotting examples require dev dependencies and
remain separate. This Phase 5 documentation commit was initially ahead of the
pushed c45bf1f tested above; the maintainer authorized its final commit/push.
Runtime/tests/example code remain identical, but no new-commit CI/install result
is inferred before observing it. **License decision pending** is the remaining
REL-01 legal/release decision; no publication action follows from passing tests.

### Final archive/link review and stop state

All **267 relative Markdown links across 44 tracked documents** resolve, including
exact heading anchors. README remains **110 lines**. Final isolated wheel/sdist
content review checks current README metadata, exact runtime/grammar bytes,
unchanged runtime/dev requirement declarations, all docs and supplied example
assets, and absence of unapproved license or bundled upstream sources. Both
working/staged whitespace checks pass. Runtime/test/example source and dependency
configuration are unchanged from the tested pushed c45bf1f revision.

The final built wheel was reinstalled without changing runtime dependencies;
installed version/namespace/refreshed README metadata and pip check also pass.

The committed scope is README/installation pin updates, the narrow M9/LSTIM/CI
wording clarifications, current navigation/status pointers and this Phase 5 record.
No additional feature implementation is pending within the bounded local gate.
Complete remote platform conclusions and the owner license decision remain
PENDING as stated above; broader decoder/performance research remains out of scope.
Local build/env/sample/log artifacts are not committed or published. Stop after
the single authorized verification commit and push.
