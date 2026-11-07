# STATUS — Repository-wide development ledger

**As of:** 2026-11-07  
**Package:** `logical_to_stim_converter`  
**Overall state:** `M3_CLIFFORD_IMPLEMENTED` (locally verified)

## M3 implemented and verified

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
| M4 | Memory/Clifford noise and synchronous timing verified; stages/composites deferred |
| M5 | Dedicated BellStatePrep/KnillEC, relocation and teleportation/adaptive frames deferred |
| M6 | Memory raw metadata implemented; decoder adapters/knill_bench integration deferred |
| Deferred | Text parser/CLI, other code families, scheduling optimization |

Current restrictions: one logical slot per block, deterministic individual final
X/Z readouts under the intended Clifford circuit, every registered block initialized
and measured once, explicit logical barriers, expanded output rounds (linear memory/circuit size). Waiting active
blocks use global idle defaults. First conjugate-basis syndromes label the random
preparation sector; no decoder-dependent correction or canonical stabilizer-sector
preparation is claimed. No general code-distance solver, S/other logical Clifford
gates, decoder algorithm, logical error-rate benchmark, adaptive physical operation,
or Knill implementation exists.

Surface-sim revision `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` supplies the
geometry/schedule reference only. Hex/lomatching remain unintegrated. A project
license has not been selected. Next: review M3, then separately scope teleportation,
nondeterministic measurement contracts, and decoder-facing integration.

## Changelog

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
