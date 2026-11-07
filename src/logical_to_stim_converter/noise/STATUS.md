# STATUS — Noise

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
