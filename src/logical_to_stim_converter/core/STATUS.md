# STATUS — `core`

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

## Planned per-file work

- [ ] code_spec.py: Immutable CSS code data, H_X/H_Z and logical representatives; verify ranks/commutation and chosen symplectic pairing. No physical indices.
- [ ] physical_layout.py: Local data/check-ancilla identities, support, geometry/coupling and SE schedule metadata; no global Stim indices.
- [ ] logical_block.py: One physical code-block instance: code/layout references and local-to-global physical site assignment; logical identity tracked elsewhere.
- [ ] code_backend.py: Code-family-dependent ideal physical gadget/flow construction contract; reject unsupported transversal logical actions.
- [ ] compiler_context.py: Per-compilation registries for block availability, logical locations, measurement keys, time layers and symbolic frame rules.
- [ ] module_fragment.py: Wrapper around stimflow components plus semantic input/output, block transition, frame and measurement metadata.

## Acceptance criteria (not yet verified)

- [ ] CSS consistency and selected logical basis verified for toy/surface examples.
- [ ] Multiple blocks reuse one CodeSpec but map to distinct physical sites.
- [ ] Knill-style block reassignment updates logical location without rewriting physical identity.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.
