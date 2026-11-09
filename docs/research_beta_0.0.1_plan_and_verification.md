# Research beta 0.0.1: decisions and verification

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
