# AGENTS.md — Tests

Tests belong here, not in `external_lib`. As of scaffolding, only an import smoke test is implemented. Each future operation needs positive and negative cases for correct logical/stabilizer flows, deterministic ideal detectors, qubit/measurement mapping, and composite/noise behavior. Keep tests reproducible and avoid decoder hard-wiring. Use `stimflow.Chunk.verify()` and Stim validation where appropriate. Update `tests/STATUS.md` and the affected source folder status when adding tests.
