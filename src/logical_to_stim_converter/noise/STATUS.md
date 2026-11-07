# STATUS — Noise

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
