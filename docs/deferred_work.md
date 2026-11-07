# Deferred decoder and DEM work

M6-A (2026-11-08) exports the canonical full detector circuit, exact global
record/parity mappings, causal preparation ancestry, stage-boundary candidates,
relocations and unresolved corrections. Explicit legacy stage views preserve
physics and noise. Noisy hypotheses can be propagated without asserting strict
noiseless final-sector equations; the strict proof remains separately available.
These tracked requirements remain future work; no GitHub issue creation is claimed.

- State-preparation decoding: infer physical sector corrections from noisy
  multi-round measurements; distinguish gauge initialization from fault evidence.
- Ordinary syndrome-extraction decoding: circuit-level temporal inference and
  correction updates on active blocks, with backend-independent result contracts.
- Bell-measurement/teleportation decoding: local versus joint readout inference,
  incoming/resource physical-frame dependencies, and output frame updates.
- Decoder assignment/configuration and downstream `knill_bench` integration.
- Gauge-detector matching, PAL/IRS, and other optional decoder adapters.
- Validated independent preparation DEM generation; window placement, stage DEM
  slicing, and preservation of inter-stage correlated error mechanisms. Removing
  cross-stage circuit annotations alone does not establish independent DEMs.
- Noisy preparation-sector estimation, general batch correction adapters, and
  decoder-dependent logical error-rate benchmarking. The test-only final-sector PyMatching helper is inadequate here.
- Adaptive SE, postselection, retries, physical block reuse, and scheduling
  optimization. Current Knill circuits are fixed single-round Clifford programs.

Production decoder interfaces must keep correction selection separate from linear
physical Clifford propagation. A correction result must identify its physical
support, source measurements/boundary, orientation, and logical contribution.
Unresolved corrections must remain explicit. No specific decoder belongs inside
KnillEC, LogicalMeasure, or the physical backend.
