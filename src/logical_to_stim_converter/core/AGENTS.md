# AGENTS.md — `core`

Scope: `src/logical_to_stim_converter/core/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Mathematical code description, physical patches, backend interface, compiler state, and fragments.

- Keep mathematical code algebra separate from physical layout and noise.
- Distinguish logical ID, block ID, physical site ID, and final Stim integer qubit index.
- Use stimflow component types for physical flow semantics rather than duplicating them.

## Files and intended responsibilities

- `code_spec.py` — planned **CodeSpec**: Immutable CSS code data, H_X/H_Z and logical representatives; verify ranks/commutation and chosen symplectic pairing. No physical indices.
- `physical_layout.py` — planned **PhysicalLayout**: Local data/check-ancilla identities, support, geometry/coupling and SE schedule metadata; no global Stim indices.
- `logical_block.py` — planned **LogicalBlock**: One physical code-block instance: code/layout references and local-to-global physical site assignment; logical identity tracked elsewhere.
- `code_backend.py` — planned **CodeBackend**: Code-family-dependent ideal physical gadget/flow construction contract; reject unsupported transversal logical actions.
- `compiler_context.py` — planned **CompilerContext**: Per-compilation registries for block availability, logical locations, measurement keys, time layers and symbolic frame rules.
- `module_fragment.py` — planned **ModuleFragment**: Wrapper around stimflow components plus semantic input/output, block transition, frame and measurement metadata.

All `.py` files in this folder are **docstring-only placeholders** as of 2026-11-07. Do not treat documented methods as implemented. Implement the minimum validated surface-code path first unless the user requests otherwise. Update this folder's `STATUS.md` after changes; update root status for completed milestones.
