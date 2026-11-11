# STATUS — Independent Knill golden validation

## 2026-11-11

Implemented separate pinned-Hex corrected ideal A0–A3 and independent direct-Stim
physical/annotation B1–B2, ordinary-noise C1 and M9 C2 oracles. The envelope is one
teleportation, three fixed patches, d=3/5, X/Z, D one initial SE and resources d SE.
Open/closed outputs, signed physical/virtual inputs, nonzero gauges, all Bell
branches and independent physical frame replay are covered. Sixteen frozen
oracle bundles have explicit provenance and read-only defaults; optional live
extraction uses actual pinned `surface_code=True` Hex, never decoder truth.

The [protocol](README.md) documents invariants, CLI and maintenance. Final commands,
counts, cases, exact row/DEM comparisons, fault and mutation evidence, fixture
hashes, platform/CI state and limits are in the
[execution report](../reports/knill_golden_2026-11-11/REPORT.md).
Production source, release dependencies, package version, license and upstream
source are unchanged. Broader protocols/decoders/LER remain outside certification.

Verification with eight workers: **1,574 repository tests passed in 845.00 s**;
final memory/primary gate **133 in 272.02 s** and Hex/fixture gate **44 in 20.58 s**.
This includes all **128** new tests. Ruff, formatting, pip/whitespace and frozen
hash/LF checks pass. Final CLI matrices are recorded in the linked report.

Both eight-worker CLI matrices passed **40/40 tasks**: live Hex plus closed-noise
principal matrix **243.101 s**, and open-output noise matrix
**236.854 s**, including physical survivor actions and exact DEMs.
