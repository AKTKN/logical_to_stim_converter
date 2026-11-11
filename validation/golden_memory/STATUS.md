# STATUS — Independent golden memory

## Minimum dependency compatibility (2026-11-11)

Stim acceptance uses the unchanged >=1.15.0 floor and PEP 440 ordering.
Generation-environment manifest metadata and every frozen byte stay unchanged;
exact stimflow source/version checks and all physical/DEM assertions remain.
The [two-version compatibility record](../../docs/dependency_compatibility.md)
contains installation, focused/full test, lint/build and CI evidence.
Both Stim wheels pass all 177 existing golden cases in the 202-case focused
gate (114.54/117.26 s), and all 1,598 full tests (538.12/482.09 s).
No frozen bytes, generator hashes, physical or DEM assertion changes.


## 2026-11-11

Implemented research-only A ideal semantic equivalence, B elementary shared
reset/readout fault equivalence, and C1/C2 independent direct-Stim ideal/noisy
schedule validation for d=3/5, X/Z and exactly three SE rounds. Frozen independent
fixtures, version/source/hash manifest, a read-only default verifier, explicit
maintenance flag, deterministic eight-spawn-worker CLI and corruption tests are
present. Exact signed flow/affine rank, metadata, causal physical order, complete
noise multisets and native unrounded DEMs are checked. See the
[protocol](README.md) and [execution report](../reports/golden_memory_2026-11-11/REPORT.md)
for final evidence. Runtime source, dependencies, package version and license
are unchanged. Broader physical programs and decoder claims remain outside scope.

Verification: the full eight-worker repository suite passes **1,446 tests in
472.92 s**, including all **49** new golden-memory cases. Ruff
src/tests/examples/validation and whitespace pass. The report records final
focused and eight-worker per-case/matrix CLI execution with machine-readable
results: **49 focused tests in 27.72 s**, all four CLI runs and the
16-task eight-worker matrix (**24.045 s**) pass. A/B/C1/C2 have no unexplained
mismatch in the stated envelope.
