# Deferred decoder and DEM work

M6-A/B (2026-11-08) export the canonical full detector circuit, exact global
record/parity mappings, causal preparation ancestry, stage-boundary candidates,
relocations and unresolved corrections. Explicit legacy stage views preserve
physics and noise. Noisy hypotheses can be propagated without asserting strict
noiseless final-sector equations; the strict proof remains separately available.
Offline decoder views now re-extract exact detector/observable marginals from the
full physical circuit, preserving fault effects across excluded annotations. Public
GF(2) record maps support software frame updates. M6-C demonstrates ordinary-memory
noisy MWPM/LER as an external consumer of one shared raw batch; it adds no runtime
decoder framework. M6-D now supplies typed temporal boundary targets, exact
conditional Bell fault
actions and static batch frame maps, with a restricted noisy modular demonstration.
These remaining requirements are future work; no GitHub issue creation is claimed.

- Production state-preparation decoding: improve temporal boundary estimates
  beyond the M6-D MWPM baseline, including ambiguous parallel-edge fault labels.
- Production ordinary-SE strategies beyond strict windows: cross-boundary
  frame reference offsets and joint conditional inference on active blocks.
- Bell-measurement/teleportation joint decoding beyond the per-patch capacity baseline:
  incoming/resource physical-frame dependencies, and output frame updates.
- Decoder assignment/configuration and downstream `knill_bench` integration.
- Gauge-detector matching, PAL/IRS, and other optional decoder adapters.
- General conditional preparation/Bell DEMs and cross-boundary reference conventions.
  M6-D exports model-only boundary probes and an explicit conditional Bell Pauli
  action model, not an exact shot-conditioned deterministic Bell DEM.
  M6-B physical marginals preserve all retained inter-stage fault effects; they
  do not establish independently decoded or conditional stage models.
- Improved noisy preparation-sector estimation and research-grade
  Knill/conditional decoder comparisons. Physical correction-to-record maps
  are now implemented for verified assembly through make_frame_plan.
  The M5 test-only final-sector helper remains inadequate for noisy inference.
  M6-D adds temporal estimates and honest finite-noise LER, without claiming
  perfect noisy sectors, optimized performance or exact maximum likelihood.
- Adaptive SE, postselection, retries, physical block reuse, and scheduling
  optimization. Current Knill demonstrations use fixed one-/two-teleportation Clifford programs.

Production decoder interfaces must keep correction selection separate from linear
physical Clifford propagation. A correction result must identify its physical
support, source measurements/boundary, orientation, and logical contribution.
Unresolved corrections must remain explicit. No specific decoder belongs inside
KnillEC, LogicalMeasure, or the physical backend.
