# AGENTS.md — Tests

Tests belong here, not in `external_lib`. The memory-core suite checks code algebra, N/Z geometry, signed flows and negative corruptions, circuit distance, exact detector/observable parities, concurrent patches, lifecycle, and exact noise locations. Each future operation needs positive and negative cases for correct logical/stabilizer flows, deterministic ideal detectors, qubit/measurement mapping, and composite/noise behavior. Keep tests reproducible and avoid decoder hard-wiring. Use `stimflow.Chunk.verify()` and Stim validation where appropriate. Update `tests/STATUS.md` and the affected source folder status when adding tests.

M5 requires PyMatching 2.3.1 in tests/helpers only. Import it unconditionally; CI must not skip the noiseless preparation-sector physics. Compare binary frame propagation against physical tableau expectations and explicit correction execution. Preserve all 173 original regressions.

M6-B: compare exact physical fault marginals, including hyperedges and correlated
^ components, not merely model sizes. Independent RNG streams require statistical
bounds; one stored batch must project/reconstruct identically across views. Keep
hand-circuit physics and characteristic-function checks separate from view code.
