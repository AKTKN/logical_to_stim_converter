# STATUS — `noise`

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

## Planned per-file work

- [ ] model.py: Planned configuration wrapper: base physical gate/reset/measurement/idle rules and operation/stage/instance overrides.
- [ ] injector.py: Planned mapping from globally tagged physical time layers to chosen stimflow noise rules and noisy Stim circuit.

## Acceptance criteria (not yet verified)

- [ ] Overriding SE CX noise does not change an unrelated standalone CNOT.
- [ ] Composite Bell/Knill circuits do not double-apply noise to nested primitives.
- [ ] Idle errors reflect globally active physical sites and simultaneous modules.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.
