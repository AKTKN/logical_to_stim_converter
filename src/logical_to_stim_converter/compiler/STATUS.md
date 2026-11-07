# STATUS — `compiler`

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

## Planned per-file work

- [ ] circuit_compiler.py: Planned fragment ordering, parallel-layer handling, assembled ideal/noisy Stim circuits and stable decoder-facing metadata.

## Acceptance criteria (not yet verified)

- [ ] Ideal init + SE + destructive measurement composes with deterministic detectors.
- [ ] Independent SE on different blocks does not serialize inadvertently.
- [ ] Qubit / measurement / observable mapping survives final stimflow reindexing.
- [ ] Same compiled physical sample is reusable by multiple decoder strategies.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.
