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
