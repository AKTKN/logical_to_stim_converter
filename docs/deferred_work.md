# Deferred decoder and DEM work

M6-A/B (2026-11-08) export the canonical full detector circuit, exact global
record/parity mappings, causal preparation ancestry, stage-boundary candidates,
relocations and unresolved corrections. Explicit legacy stage views preserve
physics and noise. Noisy hypotheses can be propagated without asserting strict
noiseless final-sector equations; the strict proof remains separately available.
Offline decoder views now re-extract exact detector/observable marginals from the
full physical circuit, preserving fault effects across excluded annotations. Public
GF(2) record maps support software frame updates. These remaining requirements
are future work; no GitHub issue creation is claimed.

- State-preparation decoding: infer physical sector corrections from noisy
  multi-round measurements; distinguish gauge initialization from fault evidence.
- Ordinary syndrome-extraction decoding: circuit-level temporal inference and
  correction updates on active blocks, with backend-independent result contracts.
- Bell-measurement/teleportation decoding: local versus joint readout inference,
  incoming/resource physical-frame dependencies, and output frame updates.
- Decoder assignment/configuration and downstream `knill_bench` integration.
- Gauge-detector matching, PAL/IRS, and other optional decoder adapters.
- Conditional preparation/Bell DEM construction and window/boundary conventions.
  M6-B physical marginals preserve all retained inter-stage fault effects; they
  do not establish independently decoded or conditional stage models.
- Noisy preparation-sector estimation, automatic physical-correction-to-record
  maps, and decoder-dependent logical error-rate benchmarking. The test-only final-sector PyMatching helper is inadequate here.
- Adaptive SE, postselection, retries, physical block reuse, and scheduling
  optimization. Current Knill circuits are fixed single-round Clifford programs.

Production decoder interfaces must keep correction selection separate from linear
physical Clifford propagation. A correction result must identify its physical
support, source measurements/boundary, orientation, and logical contribution.
Unresolved corrections must remain explicit. No specific decoder belongs inside
KnillEC, LogicalMeasure, or the physical backend.
