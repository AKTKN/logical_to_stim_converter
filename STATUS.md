# STATUS — Repository-wide development ledger

**As of:** 2026-11-08
**Package:** `logical_to_stim_converter`  
**Overall state:** `M7_A_IMPLEMENTED` (explicit physical-patch reuse and use identities)

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
