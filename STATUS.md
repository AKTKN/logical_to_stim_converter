# STATUS — Repository-wide development ledger

**As of:** 2026-11-08
**Package:** `logical_to_stim_converter`  
**Overall state:** `M6_A_IMPLEMENTED` (local physics verification)

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
| M6-B/C/D | Offline DEM views, decoder demonstrations and knill_bench integration deferred |
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
