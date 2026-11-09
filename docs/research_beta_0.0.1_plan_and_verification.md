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
