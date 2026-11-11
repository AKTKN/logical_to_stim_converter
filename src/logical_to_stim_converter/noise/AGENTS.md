# AGENTS.md — `noise`

Scope: `src/logical_to_stim_converter/noise/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Context-sensitive noise settings and fault insertion via stimflow noise machinery.

- Extend, do not duplicate, stimflow.NoiseRule and stimflow.NoiseModel where possible.
- Resolve default < operation type < composite stage < instance-specific physical rule overrides.
- Apply noise exactly once after global physical timing composition, including idle/waiting periods.

## Files and intended responsibilities

- `model.py` — **NoiseModel**: Planned configuration wrapper: base physical gate/reset/measurement/idle rules and operation/stage/instance overrides.
- `injector.py` — **NoiseInjector**: Planned mapping from globally tagged physical time layers to chosen stimflow noise rules and noisy Stim circuit.

The memory noise policy and injector are implemented. Gate rules use stimflow; global idle noise is calculated once from exported physical layers. Nested-composite/stage overrides remain deferred. Update this folder's `STATUS.md` and root status after changes.

M7-B: audit idle eligibility through TimeLayer.active_use_ids, inclusive from
each actual reset through destructive readout. Available/reserved/measured gaps
receive no idle channel; explicit bindings add no time/noise. Reuse does not
change the physical rule priorities or permit duplicate composite injection.

M9: ResourcePreparationNoise is an immutable explicit opt-in above ordinary noise
precedence only within verified BellStatePrep LogicalInit intervals. Resolve
boundaries structurally after ideal validation; use data layouts/maps and actual
BlockUseIds. Suppress gate and inclusive per-use idle faults, then inject distinctly
tagged data-only DEPOLARIZE1 after the existing final TICK. Do not infer eligibility
from stage strings, current logical names, coordinate ranges or bare init pairs.

M9 follow-up: ResourcePreparationNoise validates [0,.75] even when disabled.
NoiseInjector.apply uses None for omitted metadata: enabled calls fail before
noise setup; explicit () is the caller's declared resource-free plan. Reject
other container/element types, retain duplicate checks and ordinary disabled
omission behavior. The compiler supplies the fully resolved tuple in every case.

PostInitializationNoise explicitly selects operation_id and BlockUseId; its
verified final-SE boundary receives one data DEPOLARIZE1 channel after final idle
accounting. Keep probability [0,.75], distinct provenance and public exact location
metadata. Reject M9 overlap on one use. Empty policies preserve old circuits and
source identities. Never infer a target from logical names or primitive stages.
