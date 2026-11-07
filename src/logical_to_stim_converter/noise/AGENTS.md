# AGENTS.md — `noise`

Scope: `src/logical_to_stim_converter/noise/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Context-sensitive noise settings and fault insertion via stimflow noise machinery.

- Extend, do not duplicate, stimflow.NoiseRule and stimflow.NoiseModel where possible.
- Resolve default < operation type < composite stage < instance-specific physical rule overrides.
- Apply noise exactly once after global physical timing composition, including idle/waiting periods.

## Files and intended responsibilities

- `model.py` — planned **NoiseModel**: Planned configuration wrapper: base physical gate/reset/measurement/idle rules and operation/stage/instance overrides.
- `injector.py` — planned **NoiseInjector**: Planned mapping from globally tagged physical time layers to chosen stimflow noise rules and noisy Stim circuit.

All `.py` files in this folder are **docstring-only placeholders** as of 2026-11-07. Do not treat documented methods as implemented. Implement the minimum validated surface-code path first unless the user requests otherwise. Update this folder's `STATUS.md` after changes; update root status for completed milestones.
