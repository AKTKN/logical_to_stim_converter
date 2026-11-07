# STATUS — Repository-wide development ledger

**As of:** 2026-11-07  
**Package:** `logical_to_stim_converter`  
**Overall state:** `MEMORY_CORE_IMPLEMENTED` (locally verified)

## Implemented and verified

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

## Verification evidence (2026-11-07)

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
| M3 | Transversal CNOT/H and logical Paulis not implemented |
| M4 | Memory noise and synchronous physical time verified; stages/composites deferred |
| M5 | BellStatePrep/KnillEC, relocation and general frame rules not implemented |
| M6 | Memory raw metadata implemented; decoder adapters/knill_bench integration deferred |
| Deferred | Text parser/CLI, other code families, scheduling optimization |

Current memory restrictions: one logical slot per block, same preparation/readout
basis, every registered block initialized and measured once, explicit logical
barriers, expanded output rounds (linear memory/circuit size). Waiting active
blocks use global idle defaults. First conjugate-basis syndromes label the random
preparation sector; no decoder-dependent correction or canonical stabilizer-sector
preparation is claimed. No general code-distance solver, Clifford/frame propagation,
decoder algorithm, logical error-rate benchmark, or Knill implementation exists.

Surface-sim revision `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` supplies the
geometry/schedule reference only. Hex/lomatching remain unintegrated. A project
license has not been selected. Next: review this local memory implementation,
then separately scope transversal-operation and frame contracts.

## Changelog

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
