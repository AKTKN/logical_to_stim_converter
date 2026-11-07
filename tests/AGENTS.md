# AGENTS.md — Tests

Tests belong here, not in `external_lib`. The memory-core suite checks code algebra, N/Z geometry, signed flows and negative corruptions, circuit distance, exact detector/observable parities, concurrent patches, lifecycle, and exact noise locations. Each future operation needs positive and negative cases for correct logical/stabilizer flows, deterministic ideal detectors, qubit/measurement mapping, and composite/noise behavior. Keep tests reproducible and avoid decoder hard-wiring. Use `stimflow.Chunk.verify()` and Stim validation where appropriate. Update `tests/STATUS.md` and the affected source folder status when adding tests.

M5 requires PyMatching 2.3.1 in tests/helpers; M6-C also uses it in the external
memory example and its integration tests. Import it unconditionally; CI must not skip the noiseless preparation-sector physics. Compare binary frame propagation against physical tableau expectations and explicit correction execution. Preserve all 173 original regressions.

M6-B: compare exact physical fault marginals, including hyperedges and correlated
^ components, not merely model sizes. Independent RNG streams require statistical
bounds; one stored batch must project/reconstruct identically across views. Keep
hand-circuit physics and characteristic-function checks separate from view code.


M6-C: raw readout parity XOR affine frame XOR expected value must equal Stim's
observable flip labels on the same batch, including signed inputs and virtual/
physical Paulis. Check one physical sampling call, chunk-independent decoding,
strict/local mixed-patch IDs and deterministic faults. Reject unhandled matching
hyperedges; never assert a stochastic LER target. PyMatching/Matplotlib stay in
the dev/example layer. Exact snapshot tests must catch probability rounding and
source-fingerprint collisions on both Windows and Linux.
