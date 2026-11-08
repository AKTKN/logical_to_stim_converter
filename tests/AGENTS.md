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

M6-D: retain prior physics tests; use d=3/5 T=1/2 and physical reference tableaux.
Test temporal boundary targets separately from capacity sector representatives,
including early/late noisy result bits. Check exact conditional Bell Pauli atoms,
exclusive groups, survivor frames and actual injected physical fault signatures.
Frame edits must change later current events exactly once while preserving raw
physical batches. Test decoder replacement, chunking, spectators and no hidden
truth in stage requests. Wall timings are reported without performance thresholds.

M7-B tests use actual reset intervals, not bare block names. Check every physical
noise location and use-scoped DEM marginal, including excluded-region output
faults, exact probabilities, hyperedges and correlated components. Verify temporal
targets with independent faults, all Bell atoms with Stim, sector transfer through
real H/CNOT, and frame replay against explicit physical corrections across resets.
Keep the M7-A regression physics. v3 negative tests must rebind deliberately
corrupted Bell semantics after first checking rejection of stale source requests.

M7-C independently certifies three working patches through >=3 cycles using
actual physical tableaux/correction execution, random gauges and Bell branches,
plus an untouched encoded reference. Unfold reset intervals to fresh patches to
compare exact gate/noise sites and selected deterministic fault truth tables;
compare independent noisy streams with explicit confidence bounds. Check static
sampling calls, causal once-only corrections, chunk-identical predictions and
physical readout failure labels. Ten-cycle smoke bounds physical width only.
