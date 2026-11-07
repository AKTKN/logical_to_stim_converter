# STATUS — `decoding`

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

## Planned per-file work

- [ ] interfaces.py: Future local/joint scope, observable prediction and optional correction/soft output schemas; intentionally deferred.

## Acceptance criteria (not yet verified)

- [ ] Decoder interface can represent observable-flip predictions with or without a physical correction.
- [ ] Local/joint decoders receive data from the same physical sample without modifying source measurements.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.

- 2026-11-07 — Wrapped placeholder docstrings to remove existing Ruff E501
  failures. No decoder interface or algorithm was implemented. Raw memory
  records/detectors/observables are exported from the compiler artifact instead.
