# STATUS — `decoding`

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
