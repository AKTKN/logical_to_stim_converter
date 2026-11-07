# AGENTS.md — `backends`

Scope: `src/logical_to_stim_converter/backends/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Code-family-specific physical implementation adapters.

- Generate ideal Stim physical gadget circuits and stimflow flows for CodeSpec + PhysicalLayout.
- Inspect pinned external library APIs and record commits; prefer narrow adapters to forks.
- Clearly identify unsupported gates, geometry, or code families; no silent approximations.

## Files and intended responsibilities

- `surface_code.py` — **RotatedSurfaceCodeBackend**: Verified ideal memory chunks using stimflow and the pinned surface-sim geometry/schedule convention.
- `color_code.py` — planned **ColorCodeBackend**: Future backend for color codes; deliberately not an initial implementation milestone.

RotatedSurfaceCodeBackend implements memory and H/CNOT/Pauli chunks with code orientation. Bell/Knill composites reuse these primitives; no dedicated Knill backend gadget is needed. Color-code support remains unimplemented. Update this folder's `STATUS.md` and root status after changes.
