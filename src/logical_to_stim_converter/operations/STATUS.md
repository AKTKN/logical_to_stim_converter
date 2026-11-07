# STATUS — `operations`

**2026-11-07 state:** `SCAFFOLDED`. All Python modules are placeholder docstrings. No domain functionality implemented.

## Planned per-file work

- [ ] base.py: ABC and common build/validate contract; targets, operation ID, optional noise instance override.
- [ ] initialization.py: Prepare |0_L> (Z) or |+_L> (X) using physical reset plus specified repeated SE rounds.
- [ ] syndrome_extraction.py: Generate a configurable number of SE rounds and associated flow boundaries; prefer stimflow.ChunkLoop.
- [ ] transversal.py: Physical transversal gates, verified logical/stabilizer transforms, code-specific layout/basis effects.
- [ ] pauli.py: Logical Pauli operation, either physical gate realization or virtual logical Pauli-frame update.
- [ ] measurement.py: Destructive X/Z readout and terminal flow/observable metadata; mark consumed block.
- [ ] bell_preparation.py: Composite two-state preparation + H + transversal CNOT, or future alternative resource gadget.
- [ ] knill_ec.py: Composite Bell measurement, logical relocation D->B and symbolic correction/bell measurement metadata; decoder-independent.

## Acceptance criteria (not yet verified)

- [ ] Each primitive generates an ideal flow-verified fragment for supported code.
- [ ] Both basis states initialize and read out correctly in an ideal memory test.
- [ ] CNOT/H/Pauli flow actions match declared logical action.
- [ ] KnillEC updates block locations, preserves raw measurement context, and does not select a decoder.

## Implemented and verified

- [x] Directory, `__init__.py`, placeholder source files, and local `AGENTS.md` / `STATUS.md` created.
- [ ] Any operational code or physics correctness test.

## Development history

- 2026-11-07 — Initial scaffold only. No physics code or validated API.

After each implementation task, record **date**, **files and contracts changed**, **checks/results**, **upstream versions**, **limitations**, and **next actions** here and in the repository root `STATUS.md`.
