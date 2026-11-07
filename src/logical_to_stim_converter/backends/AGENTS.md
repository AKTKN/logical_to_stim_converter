# AGENTS.md — `backends`

Scope: `src/logical_to_stim_converter/backends/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Code-family-specific physical implementation adapters.

- Generate ideal Stim physical gadget circuits and stimflow flows for CodeSpec + PhysicalLayout.
- Inspect pinned external library APIs and record commits; prefer narrow adapters to forks.
- Clearly identify unsupported gates, geometry, or code families; no silent approximations.

## Files and intended responsibilities

- `surface_code.py` — planned **SurfaceCodeBackend**: Planned rotated surface-code layout and SE/Clifford/readout implementation, reusing surface-sim if verified.
- `color_code.py` — planned **ColorCodeBackend**: Future backend for color codes; deliberately not an initial implementation milestone.

All `.py` files in this folder are **docstring-only placeholders** as of 2026-11-07. Do not treat documented methods as implemented. Implement the minimum validated surface-code path first unless the user requests otherwise. Update this folder's `STATUS.md` after changes; update root status for completed milestones.
