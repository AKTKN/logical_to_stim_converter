# STATUS — `decoding`

## M7-B update — 2026-11-08

DetectorSelector adds independent BlockUseId filters with anchor/touching/strict
membership. SelectionAudit records requested/retained uses; observable-local
regions use real interaction/relocation/verified-relation edges between uses.
Physical-block selectors keep all epochs. DecoderView schema v3 intentionally
fingerprints use/binding/owner, timing, Bell and ancestry histories; regenerate
v1/v2 identities. Existing exact instruction/DEM snapshots retain full double
precision, repeats/shifts, correlated components and hyperedges on Windows/Linux.

Boundary/readout requests resolve source preparations by actual use and expose
that source. The temporal model retains strict module-local observations with
model-only ideal probes. Signed sector transfer tracks current use/orientation
and surviving prior-sector expressions through H/CNOT, instead of a last/first
preparation per site. Conditional Bell models select the actual output-use prep
and resource-use CNOT window, including already prepared Bell resources. Public
window/use/module IDs audit categorical atoms, exclusivity and survivor actions.

Frame boundaries carry their use. CorrectionBatch optionally declares use and
input labels; wrong use/order/source/shots/shape fail before mutation. Unique
modules permit legitimate updates to multiple epochs, while duplicate updates
fail. Physical resets extinguish old supports without deleting Bell history.
records.py was audited: its global-key/source-bound batched maps already have no
site-preparation lookup and require no implementation change. All touched public
classes/functions and significant helpers have English physical API docstrings.

Focused new suite: 50 passed in 53.63 s. Retained view/ancestry checkpoint:
110 passed in 49.05 s; stage/strict-frame checkpoint: 33 passed in 39.77 s;
final frame/record checkpoint: 27 passed in 26.08 s. Root STATUS records complete
regression/examples/build/CI, direct fault, marginal and physical replay evidence.
No runtime decoder, automatic allocation or multicycle Knill LER claim.
Final full suite: 544 passed in 568.60 s; final new/negative checkpoint:
52 passed in 57.19 s. See root STATUS for complete command/platform evidence.

## M6-D update — 2026-11-08

frames.py adds source-bound CorrectionBatch/FrameBoundary/OfflineFramePlan and
isolated OfflineFrameBatch state, checked binary shapes/provenance, immutable raw
storage, once-only updates and current-record event recomputation. stages.py adds
typed StageInputs/Result/Decoder and Boundary/Readout/StageRequests. Boundary
models preserve noisy physical prefixes/strict detector regions, adding ideal
model-only probes for last-record XOR true-check targets and prepared logical
errors. No canonical probes or sampled decoder truth are introduced. Signed Pauli
elimination maps prior predicted boundary sectors through actual H/CNOT pairs.

conditional.py exports exact resource-CNOT-through-Bell-readout noise atoms,
probabilities/exclusive groups, joint destructive record/logical/check effects and
survivor physical X/Z actions. Unsupported physical channels raise typed errors.
This is a conditional fault-action model, not a deterministic Bell DEM. Earlier
residual decoder errors may violate the assumed incoming boundary hypothesis.

All matching adapters live in examples/knill_memory_offline_decoding.py. The
baseline uses temporal correlated MWPM then CSS capacity representatives, and
conditional per-patch capacity readout; parallel-edge ambiguities, neglected joint
inference and one-round SE temporal limits are explicit. Production algorithms,
optimized cross-boundary conditional models and general decoder result interfaces
remain future work. Full exact/fault/noiseless/noisy/wall-time evidence is in root
STATUS; installed pins remain Stim 1.15.0/stimflow ffe0d043/PyMatching 2.3.1 (dev).

## M6-C precision correction — 2026-11-08

The external ordinary-memory example uses the existing public views; no decoder
is added here. During M6-C verification, M6-B remote run 42422493437 was found to
pass Linux but fail six exact DEM identity comparisons on Windows. Stim 1.15's
DEM printer uses long-double precision (only 16 significant digits on MSVC),
which can round a double probability. Circuit text also rounds arbitrary gate
arguments to six significant digits on both platforms.

views.py now snapshots immutable tuples of exact public instruction arguments,
targets, tags and nested repeats, and rebuilds copies through Stim append APIs.
This is exact object copying, not fault projection or DEM rewriting. Fingerprint
schema v2 includes full circuit precision; v1 identities must be regenerated.
New regressions emulate the Windows DEM printer, distinguish sources that print
identically, and preserve exact probabilities, escaped tags, repeat structure,
coordinate shifts and correlated separators. Existing equality tests remain exact.
Root STATUS records final full-suite/build/example/CI evidence and pinned versions.

## M6-B implemented — 2026-11-08

views.py provides immutable source-fingerprinted DecoderView snapshots, exact
ordered IndexMaps, SelectionAudit, DEMOptions and DecoderInputs. Physical circuit
re-extraction preserves all gates/noise/records and hyperedges; arbitrary detector
permutations use end annotations with translated global records and coordinates.
Repeat occurrences expand without dropping SHIFT_COORDS or TICKs. Stim handles DEM
repeat/shift/decomposition semantics. Public model/circuit properties return copies.

selectors.py supports anchor/touching/strict blocks/stages, X/Z physical checks,
unions and custom public-metadata callbacks. observable_local_views constructs
one reliable-observable view per physical interaction component, with user override.
Random Bell outcomes cannot be selected as deterministic observables. records.py
provides immutable sparse GF2Map and source-bound RecordFlipMap; batch projection,
reference-aligned recomputation and XOR updates never change caller raw records.
errors.py provides typed invalid-selection/source/undefined-observable/DEM failures.
interfaces.py remains a decoder-result placeholder; no decoder algorithm is added.

Supported models use exact physical-circuit re-extraction. Default extraction
retains hyperedges. Explicit Stim decomposition and flattening are supported;
unsupported exact noise/decomposition raises typed errors without gauge elimination
or disjoint-error approximation. Direct DEM rewriting, optimized observing-region
selection, conditional Bell models and automatic physical correction-map generation
remain deferred. Edited records do not automatically define a new conditional DEM.

Evidence: 119 focused view/record/M6-A tests passed, plus 6 final basis/support and
cross-stage-policy tests. All four examples pass; lint/build/dependency checks pass.
Final full-suite and isolated artifact evidence are in root STATUS. Pins remain
Stim 1.15.0 and stimflow 1.17.dev0 at ffe0d043598ed5df0851a3e6b4920359a23fafbd.
Inspected installed Stim DEM, flattened/repeat/shift/target-separator, reference
sample and m2d APIs. Inspected read-only lomatching b55a7a6, surface-sim 493f800,
and Hex 5de58f2 reference sources; none is imported, changed or vendored.

## Earlier scaffold history

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

M5 keeps this production-decoder namespace unimplemented. Physical correction
result/propagation contracts live in core/protocol.py and compiler/_frames.py;
selection remains external. The required PyMatching helper is test-only, operates
on noiseless final preparation sectors, and performs no circuit-level inference.
Future state-preparation, ordinary SE, and Bell-measurement decoder work, gauge
matching/PAL/IRS, stage DEM/window validation, cross-stage fault correlations,
noisy sector estimation, LER studies, and adaptive retry policies are tracked in
docs/deferred_work.md. No GitHub issue creation is claimed.

## Planned per-file work

- [ ] interfaces.py: Future local/joint scope, observable prediction and optional correction/soft output schemas; intentionally deferred.

## Acceptance criteria (not yet verified)

- [ ] Decoder interface can represent observable-flip predictions with or without a physical correction.
- [ ] Local/joint decoders receive data from the same physical sample without modifying source measurements.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.

- 2026-11-07 — Wrapped placeholder docstrings to remove existing Ruff E501
  failures. No decoder interface or algorithm was implemented. Raw memory
  records/detectors/observables are exported from the compiler artifact instead.
