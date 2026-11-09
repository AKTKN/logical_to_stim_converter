# AGENTS.md — Repository instructions for Codex and maintainers

This file applies to the entire repository. Read the nearest nested `AGENTS.md` and `STATUS.md` before editing files in that directory.

## Purpose and current reality

Build an independent `logical_to_stim_converter` package that compiles logical operations into physical Stim circuits, initially for rotated surface codes and later color/other CSS codes, using `stimflow` for verified stabilizer-flow composition. `knill_bench` remains the experiment runner. **As of 2026-11-07 the rotated-surface memory and M3 H/CNOT/Pauli paths are implemented and locally verified.** Core models, multi-block fragments, code orientation, affine frames, correlated detectors, concurrent physical layers, and operation noise work. Bell/Knill composites, random readouts, open outputs, Knill relocation, and externally resolved physical preparation frames now work. Offline decoder views and external ordinary-memory and restricted modular Knill MWPM/LER examples now work;
other code families and production decoder result/algorithm interfaces remain deferred. Check STATUS for exact evidence; do not infer functionality from names or docstrings.

## Source-of-truth map

- `README.md`: user-facing project overview and setup instructions.
- `STATUS.md`: global milestones, actual implementation/verification status, and chronological changes.
- `docs/architecture.md`: current design contracts, boundaries, invariants, and unresolved decisions.
- `src/logical_to_stim_converter/core/`: `CodeSpec`, `PhysicalLayout`, `LogicalBlock`, `CodeBackend`, `CompilerContext`, `ModuleFragment`.
- `.../operations/`: `OperationModule` abstract base, logical primitives, composite Bell/Knill operations.
- `.../backends/`: code-family physical implementations and optional adapters to existing generators.
- `.../noise/`: operation-aware policy; built on `stimflow` noise rules; avoids duplicate injection.
- `.../compiler/`: module assembly, flow validation, circuit metadata, compiled artifact.
- `.../decoding/`: offline decoder views, exact physical-model marginals and record transforms; no decoder algorithm.
- `tests/`: signed-flow, algebra, geometry, distance, detector/observable parity, mapping, lifecycle, and exact noise-location tests for memory and interacting Clifford circuits.
- `external_lib/`: local **reference** copies. Not tracked by Git by default. Do not edit upstream source unless explicitly directed.

## Mandatory architecture principles

1. Separate logical identity, physical block identity, local qubit key, and Stim global qubit index. Teleportation changes the logical-to-physical location, not the identity of the logical qubit.
2. Keep `CodeSpec` mathematical, independent of `PhysicalLayout`, hardware scheduling, and noise. Put code-specific physical circuits behind `CodeBackend`.
3. Implement logical primitives as subclasses of `OperationModule`; use an adapter/wrapper to hold `stimflow.Chunk`/`ChunkLoop`/`ChunkReflow` and supplementary logical metadata. Prefer composition over reimplementing flow composition or subclassing unstable stimflow internals.
4. Verify ideal stabilizer and logical flows first. Then insert noise according to composed physical time layers; an individual physical fault location must not receive noise twice because it appears inside a composite module.
5. Do not wire a specific decoder into `KnillEC`, `LogicalMeasure`, or the physical backend. Preserve raw measurements and decoder-independent observables so local and joint decoding can use the same physical samples.
6. Maintain measurement-record and observable IDs symbolically until global assembly; do not rely on brittle hard-coded `rec[-k]` offsets in module contracts.
7. Parallel logical operations require a coherent global `TICK`/idle schedule. `stimflow.ChunkCompiler.append` alone should not be assumed to encode simultaneous operations.
8. Check whether logical H/CNOT actually realizes the intended logical Clifford on the selected code and logical basis; do not assume all CSS codes share the same H geometry.
9. Preserve compatibility with Python 3.11+ and Windows development. Make `knill_bench` depend on this package, never the reverse.
10. `language/` implements M8-A syntax, M8-B static validation/lowering and M8-C
    public text/file/formatter APIs; `docs/lstim_v1.md` is the contract. Keep
    AST/syntax independent of physical objects. LogicalProgram preserves explicit
    BindPatch directives and compiles with an empty initial mapping. Formatting
    preserves all typed semantic fields, target/binding order and nested source
    groups; it never unrolls or compiles. UTF-8 file errors retain causes and
    reliable locations. M8-D certifies the bounded physical/simulation matrix in
    docs/lstim_certification.md against independent public-operation references.
    Keep exact source identity conditional on matched authored bindings/labels;
    SourceSpan/comments are frontend provenance. Offline decoder replay shares
    raw samples, never resamples, and stays in examples/tests. A CLI is deferred.
11. Canonical ideal/noisy circuits retain every verified global detector. Stage
    separation is an explicit derived annotation view; metadata keeps global IDs.
    Join preparation ancestry only through actual operand interactions/relocation.
    Keep noisy frame hypotheses separate from strict noiseless-sector proofs.
12. Decoder views preserve every physical instruction/noise channel and re-extract
    DEMs with Stim. Never discard faults merely because they touch excluded
    detectors. Preserve hyperedges/correlated ^ components and global/local maps.
    Software record frames edit copies with explicit source/reference alignment.

## Workflow for each coding task

1. Read root and folder `STATUS.md`; identify the requested milestone and dependencies.
2. Inspect the actual pinned upstream APIs before copying integration code. Record versions/commits and any behavioral assumptions in status or docs.
3. Make the smallest scoped change. Do not silently expand into parser, scheduling optimization, decoder switching, or non-Clifford support.
4. Add a focused test that can fail on an incorrect physical flow, frame, detector, mapping, or noise rule. Do not replace physics checks with mere import tests once functionality exists.
5. Run applicable checks: `python -m pytest -n 8` (pytest-xdist dev dependency),
   `python -m ruff check src tests`, plus relevant Stim/flow validation. Build
   tests use private temporary source trees to avoid parallel setuptools races.
6. Update the affected folder's `STATUS.md` and root `STATUS.md` (what changed, evidence/tests, unimplemented/blocked items, date). Update `AGENTS.md` if architecture/responsibility changes and `README.md` if user-visible instructions change.
7. In the completion report, separate verified behavior, implemented but unverified behavior, and remaining plans. Do not call a stub implemented.

## Repository safety

- Never modify or commit `external_lib` copies by default. Consult `external_lib/README.md` for pinned-revision and import guidance.
- Avoid committing `.venv/`, artifacts, sampled data, secrets, large caches, or non-redistributable external code.
- Avoid mutable global state for per-shot Pauli frames, sampled data, or compilation contexts.
- Preserve deterministic ordering and seeded reproducibility of generated circuits/metadata.
- No license is selected; do not add one without maintainer instruction.


M6-C keeps PyMatching and Matplotlib in the dev/example layer. Memory LER uses one
raw batch and externally decoded reference-relative observable flips. Canonical
DEMs preserve physical correlations; graphlike matching conversion is explicit
and rejects unsupported hyperedges. DecoderView schema v3 uses immutable exact
instruction snapshots, never lossy Stim text, for probabilities and source identity.


M6-D adds typed stage requests and source-bound batch correction hypotheses.
Compiler frame plans precompute sparse physical H/CNOT/readout/Bell feedback maps;
no shot loop or decoder belongs in quantum assembly. Boundary MPP probes are
model-only targets, never sampled canonical measurements or decoder truth. Raw
Bell checks are conditional offline syndromes, not new deterministic detectors.
Preserve exclusive groups and survivor actions in conditional fault models.
Record phase wall times outside the shot loop and state baseline approximations.

M7-A adds explicit BindPatch reservations and immutable BlockUseId/BlockUseInfo
history. Physical block/site identities never change on reuse. Only LogicalInit
starts/increments an epoch; bindings have no physical duration/reset/noise. Fresh
logical names reserve explicitly selected available patches. Reject stale aliases,
pending-reservation conflicts and parallel physical overlap. Keep historical
readouts/observables and persistent data slots through relocation; reset retired
internal tableau slots before assigning fresh states. Decoder policies across
epochs are implemented in M7-B; the explicit three-patch example is M7-C.

M7-B scopes detector anchors/sources, active time layers, preparation ancestry,
boundary/conditional requests and correction maps to BlockUseId or unique module
IDs. Physical-block selectors include all epochs; use selectors distinguish
anchor/touching/strict membership. Observable locality uses a time-expanded graph
of real interactions/relocations, never coordinate reuse alone. Reset removes old
physical frames but preserves legitimate teleported/classical dependencies.
Fingerprint schema v3 includes use histories and requires cached v1/v2 artifacts
to be regenerated. Preserve exact physical instructions, noise and raw samples.

M7-C authors a visible P0/P1/P2 binding schedule in examples, using existing
KnillEC primitives and M6-D external adapters. It bounds physical-state width,
not circuit/record/history size. Sample one static circuit once per bounded
batch; never execute stages again for decoder hypotheses. Preserve the separate
M6-D fresh-resource behavior and its result format. Report corrected physical
readout XOR intended state, honest restricted-decoder limitations and separate
setup/sampling/events/decoding/frame/report wall phases. Keep orchestration,
PyMatching and plotting outside the installed runtime package.

M9 adds opt-in ResourcePreparationNoise at noise compilation time. Only the two
LogicalInit primitives structurally owned by BellStatePrep have ideal reset/SE
intervals; other gates/uses and waiting layers keep ordinary noise. Post-SE
DEPOLARIZE1 targets layout data sites once per BlockUseId, after existing final
TICK/idle accounting and before resource CNOT, with distinct stochastic provenance.
Keep preparation probes before these channels and conditional Bell models starting
at them. Reject unsupported intervening operand SE boundaries explicitly. Preserve
disabled circuits/fingerprints and canonical ideal schedules; no new LSTIM syntax.

M9 follow-up restricts p_st_transversal to finite non-boolean [0,.75] values,
including disabled configurations, for native exact DEM compatibility. Validate
the actual noisy circuit without caps/fallbacks. Enabled direct NoiseInjector.apply
requires an explicit verified tuple; None/omitted fails, () declares no resources.
Only standard compilation resolves/validates full Bell eligibility; do not add a
second resolver or infer it from primitive stages/names.
