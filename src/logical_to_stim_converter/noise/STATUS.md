# STATUS — Noise

## Explicit post-initialization data channel — 2026-11-11

Added frozen PostInitializationNoise(operation_id, block_use_id, probability)
and NoiseModel.post_initialization tuple. Resolve exact init final-SE cuts after
ideal verification; inject after existing final idle accounting and before later
gates, including final open outputs with no extra TICK. Public frozen boundaries
retain use/module/data-site/probability/instruction provenance. Reject duplicate
uses, stale selectors and overlap with M9. Empty policies retain old behavior.
M9's eligibility/suppression/resolver are reused, not reimplemented. Public direct
injection requires explicit verified metadata. Root STATUS records gate evidence.


Final complete local gate: **1,664 passed in 1,035.32 s** with eight workers,
no failures/skips. Ruff and pip checks pass; exact packaging and CI attribution
are in docs/parallel_knill_deep_clifford.md and root STATUS. All eight runtime
CI jobs (Ubuntu/Windows, Python 3.11/3.12, Stim 1.15/1.16) pass tests, builds and
all eleven examples at b74df32; this final follow-up changes documentation only.

## M9 follow-up — 2026-11-09

The policy's closed supported range is now [0,.75], enforced at construction
for either enable state with finite/non-boolean/type checks. Other noise channels
retain [0,1]. Direct NoiseInjector.apply distinguishes None/omitted from explicit
(): enabled omission fails before noise setup; explicit () declares no resources.
Tuple/element checks reject malformed arguments and existing duplicate use/module
checks remain. Standard compilation resolves and supplies the complete plan; the
injector does not reconstruct Bell composite eligibility from primitive-only
inputs. Exact direct/compiler/reference circuits, native DEMs and source identities
are tested, including probability zero and exactly .75. Root STATUS records
commands/results. The old p=1 sampling evidence below is historical only.


## M9 initial update — 2026-11-09 (historical pre-restriction)

model.py adds immutable ResourcePreparationNoise with strict bool, finite
probability and config-type checks. resource_preparation.py resolves actual
BellStatePrep composite children, PreparationInfo, BlockUseIds, tagged final SE
measurements/TICKs and layout data sites into immutable cuts. Public provenance
audits reject ambiguous membership, missing/duplicate uses/sites and misplaced
channels. NoiseInjector consumes indexed cuts, suppresses only the two resource
initialization modules' gates and per-use inclusive preparation idles, and emits
one tagged independent DEPOLARIZE1 per data target after the existing final TICK.
Waiting D/spectators and later resource waiting/gate/readout noise retain their
ordinary precedence. Enabled zero suppresses preparation noise without a channel;
disabled mode matches independent original-rule circuits and exact DEMs. Root
STATUS records the original exact physical-location, historical p=1 sampling,
regression and CI checks. The initial API permitted sampling for p>3/4 despite
Stim's DEM limitation; the follow-up now rejects these probabilities. No upstream
pins/source changed.


## M7-B update — 2026-11-08

NoiseInjector audits idle eligibility with TimeLayer.active_use_ids, preserving
the existing inclusive reset-through-readout convention and all physical rules.
Gate and idle channels remain inserted once after ideal signed-flow assembly.
Available/reserved/retired gaps are excluded; later initialization re-enters with
the new use. No BindPatch duration/noise or decoder-dependent rule is introduced.

Independent d=3/5 sequential/parallel/composite tables compare every reset,
measurement, 1q/2q and idle channel target/probability/layer, active uses, ancilla
idles, zero overrides, inherited composite overrides, moved zero-time binds and
reinjection rejection. Canonical DEMs pass. Installed pins and source references
are unchanged; root STATUS records final full verification and exact API evidence.

## M5 verification — 2026-11-07

The existing injector requires no second composite noise path. Every physical
instruction keeps its primitive module tag; shared CNOT modules own both blocks
and each pair receives one fault. Composite instance overrides are inherited by
children; primitive type/global resolution remains intact. Waiting input/output
blocks, active ancillas, measured/retired blocks, and zero-duration virtual gates
retain the global schedule convention.

New d=3/5 Knill tests compare exact gate/reset/result/idle channels, targets,
probabilities, and layers, including primitive-equivalent noisy circuits, both
resource and Bell CNOTs, metadata preservation, seeded reproducibility, and DEM
validity. Root STATUS records final results. Stage-specific noise selectors and
custom correlated models remain deferred; stage provenance is now populated.

## M3 update — 2026-11-07

M3: NoiseModel operation selectors accept TransversalH, TransversalCNOT,
and LogicalPauli. The existing injector works with generalized physical-time
provenance: one CNOT module owns both blocks but each physical pair receives one
noise rule. H and physically executed Pauli gates use one-qubit Clifford noise.
Virtual Paulis have no physical tick, idle exposure, or gate faults. Exact channel,
probability, target, and layer counts pass for mixed concurrent operations;
zero-noise equality and record-index preservation remain. A CNOT-only noise model
produces correlated detector effects across the two blocks. No decoder-dependent
noise or composite stage selector was added.

Evidence: the extended 173-test suite, Ruff, and both examples; exact final
commands/results are in root STATUS. Dependencies remain pinned to Stim 1.15.0
and stimflow commit ffe0d043598ed5df0851a3e6b4920359a23fafbd. External
source trees are unchanged.

## Prior memory implementation record

**2026-11-07: memory noise model/injector implemented and verified.**

`model.py` implements immutable global NoiseParameters, partial NoiseOverride,
and NoiseModel selection: instance > primitive type > global, per channel. None
inherits; zero replaces inherited noise. The upstream NoiseModel/NoiseRule API
provides anticommuting reset faults, one-/two-qubit Clifford depolarization, and
measurement-result flips. Invalid probabilities are rejected.

`injector.py` applies gate noise only after ideal flow verification and derives
global idle faults once from composed physical layers and live blocks. Physical
tags preserve operation provenance. Waiting live blocks use global idle defaults;
currently operated blocks use their effective primitive rule. All block sites,
including ancillas, are eligible from initialization through destructive readout.
Uninitialized/retired sites are excluded. Already noisy input is rejected.

Evidence: exact channel/target/probability counts for concurrent X/Z patches,
operation and instance replacement (including zero), reset/result errors, one-qubit
upstream rule, idle waiting/retirement, no reinjection, zero-noise equality,
unchanged record/detector/observable targets, deterministic seeded smoke samples,
and noisy DEM/fault-distance checks. See root STATUS for final commands/results.

Deferred: stage and nested-composite overrides, correlated custom noise models,
and general scheduling. ModuleFragment's stage provenance is reserved for a later
additive extension. No upstream source was changed.

History: 2026-11-07 scaffold -> minimal circuit-level memory noise.
