# AGENTS.md — `core`

Scope: `src/logical_to_stim_converter/core/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Mathematical code description, physical patches, backend interface, compiler state, and fragments.

- Keep mathematical code algebra separate from physical layout and noise.
- Distinguish logical ID, block ID, physical site ID, and final Stim integer qubit index.
- Use stimflow component types for physical flow semantics rather than duplicating them.

## Files and intended responsibilities

- `code_spec.py` — **CodeSpec**: Immutable CSS code data, H_X/H_Z and logical representatives; verify ranks/commutation and chosen symplectic pairing. No physical indices.
- `physical_layout.py` — **PhysicalLayout**: Local data/check-ancilla identities, support, geometry/coupling and SE schedule metadata; no global Stim indices.
- `logical_block.py` — **LogicalBlock**: One physical code-block instance: code/layout references and local-to-global physical site assignment; logical identity tracked elsewhere.
- `code_backend.py` — **CodeBackend**: Code-family-dependent ideal physical gadget/flow construction contract; reject unsupported transversal logical actions.
- `compiler_context.py` — **CompilerContext**: Per-compilation registries for block availability, logical locations, measurement keys, time layers and symbolic frame rules.
- `module_fragment.py` — **ModuleFragment**: Wrapper around stimflow components plus semantic input/output, block transition, frame and measurement metadata.

The memory-core models and contracts are implemented; consult STATUS for validations. H/CNOT/Pauli affine frames are implemented; teleportation, adaptive frames, and relocation remain deferred. Update this folder's `STATUS.md` and root status after changes.

M3: `code_frame.py` maps canonical data coordinates to fixed physical sites and uses signed Stim conjugation. Keep current code orientation in CompilerContext, never mutate physical block identities. ModuleFragment has one ordered tuple representation of its logical/physical operands.
