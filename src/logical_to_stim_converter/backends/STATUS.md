# STATUS — `backends`

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

## Planned per-file work

- [ ] surface_code.py: Planned rotated surface-code layout and SE/Clifford/readout implementation, reusing surface-sim if verified.
- [ ] color_code.py: Future backend for color codes; deliberately not an initial implementation milestone.

## Acceptance criteria (not yet verified)

- [ ] A pinned surface-sim/Stim version provides a validated rotated-surface layout and QEC cycle.
- [ ] Surface CNOT/H implementations have verified logical actions and layout transforms.
- [ ] No accidental assumptions about all CSS codes having transversal H.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.
