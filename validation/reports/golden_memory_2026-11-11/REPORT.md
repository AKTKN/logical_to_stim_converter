# Independent golden-memory execution report — 2026-11-11

## Source and independent provenance

DUT baseline: **`5086c236bfc34e35a3dc040862f1174770a4699d`**, branch
`validation/phase3-m9-knill-faults`. This checkout includes the prior Phase 1–3
research validators; the implementation prompt's inspected main
`be734ce71c5140a9e01ccd1fdb2d181678cef663` has an older directory inventory.
The new suite preserves those validators and changes no runtime `src/` code,
source pin, package version, decoder, parser, scheduling policy or license.

Local environment: Linux/WSL2, Python **3.12.7**, Stim **1.15.0** wheel,
stimflow **1.17.dev0**, installed from
`quantumlib/Stim@ffe0d043598ed5df0851a3e6b4920359a23fafbd`, `glue/stimflow`.
The installed direct-url metadata and the read-only local Stim source checkout
both confirm that full commit. Source inspection covered the standard surface
code generator/reset/readout noise, stimflow flow/chunk/noise interfaces, and
current converter geometry, primitive, compiler, metadata and noise paths.
The Stim wheel's release version is distinct from the inspected stimflow source
commit; this report does not assert that the wheel was built from that dev SHA.

The [protocol and CLI](../../golden_memory/README.md) define the methods and
independence boundary. The direct reference uses elementary dual-grid geometry
and direct Stim instructions. It does not import converter code or read DUT
circuits/metadata. Converter imports occur only in the DUT constructor bridge.
A subprocess forbids converter/test imports while building all four references.
Frozen ideal fixtures originate only from that reference builder, with reviewed
d=3 support sentinels, d=3/5 CSS algebra, explicit four-layer gates and signed
physical checks. No DUT export or third-party source snapshot is a fixture.

The [manifest](../../golden_memory/fixtures/manifest.json) records generator
SHA-256, versions, source/baseline commits, counts and the following fixture
SHA-256 values:

| Independent fixture | SHA-256 |
| --- | --- |
| d3_x.stim | `ea2c65d1b43a73de10e15bf0d2754ef8f624d7aa9ac95c72b1b51d2e40721aff` |
| d3_z.stim | `aa7a040f590803ff3b4be9708a3dfa5ce1e8c8ae2d6a2f3e8b3118107ee4413d` |
| d5_x.stim | `1d00d9b170e75cda462f1e2d3d24132ce348c906e174a63f3dabdd0316eeb4c9` |
| d5_z.stim | `f4d5de965d01f0e994f2a884d5a764baaf017ab99380f4f620c8506ffc8c9b1e` |

## Exact results

All four cases execute exactly `LogicalInit(...,1)`,
`SyndromeExtraction(...,2)`, `LogicalMeasure`, with the initialization round
included in the three-round total. The table applies independently to both X
and Z bases:

| Property | d=3 | d=5 |
| --- | --- | --- |
| Occupied data + ancilla sites | 17 | 49 |
| Raw measurements | 33 | 97 |
| Canonical detectors / observables | 24 / 1 | 72 / 1 |
| Converter moments / TICKs | 20 / 19 | 20 / 19 |
| A complete signed affine rank | 25 | 73 |
| A free raw-record bits | 8 | 24 |
| A signed round flows per implementation | 54 | 150 |
| B matched elementary faults | 66 | 194 |
| B matched faults with zero signature | 0 | 0 |
| B distinct matched signatures | 38 | 114 |
| B unmatched terminal MR resets, individually inert | 8 | 24 |
| C2 reset errors | 33 | 97 |
| C2 CX depolarizing target pairs | 72 | 240 |
| C2 measurement-result flips | 33 | 97 |
| C2 active idle depolarizing sites | 130 | 306 |
| C2 one-qubit Clifford locations | 0 | 0 |

**A:** Both schedules have exactly the independently predicted signed ideal
record support. Elimination multiplies signed `stim.Flow` objects and verifies
each resulting measurement-only flow with Stim. Exact rank/completeness and
round nondemolition/logical-flow proofs supplement the 64-shot zero-event
smoke test for each circuit. Complementary first-round checks are random. The
standard generator's sparse indices and H/MR ancilla outputs are handled by
occupied-coordinate reflection and data-only round ports.

**B:** All **520** matched elementary mechanisms across the four cases have
identical deterministic semantic detector/logical signatures. Every response
is certified as a signed flow, even when distinct mechanisms share signatures.
All **64** intentionally unmatched post-final-MR reset mechanisms are separately
proved inert. No mechanism is removed from a DEM to obtain agreement. CX/gate
noise is outside this cross-schedule comparison.

**C1/C2:** All ideal and fully noisy physical moment sequences agree exactly
under the documented representation normalizations. C2 uses
`(reset,one_qubit,two_qubit,measurement,idle)=(.01,.02,.03,.04,.05)`.
Counters retain every target/pair location, exact double probabilities and
causal position, including idles after the last data measurement. Independently
canonical native DEMs compare as exact Stim objects, with no text rounding or
fault projection. Each case/variant also verifies 27 paired deterministic
X/Y/Z propagation probes at beginning/middle/end round boundaries: **216 paired
probes** over four cases and two C variants.

No unexpected physics, frame, annotation, mapping or noise mismatch was found.
Mutation controls reject deleted/reversed/altered CXs, changed check support,
noncommuting layer swaps, corrupted detector/logical rows, reset errors moved
across reset or changed in basis/target, omitted/altered CX depolarization,
missing/duplicate/wrong-site/inactive idle channels, altered result-flip
probabilities/locations and removed final TICK boundaries. Additional tests
check signed Bell-Y elimination, GF(2) multiplicities, metadata anchors, source
independence and read-only/default fixture maintenance.

## Reproduction and verification

Run from the repository root with the existing `.[dev]` environment. Commands
use the `.venv/bin/python` interpreter on this machine:

```sh
python -m pytest -n 8 tests/test_validation_golden_memory.py -ra
python -m pytest -n 8 -ra --tb=short --durations=10
python -m ruff check src tests examples validation
python -m validation.golden_memory.run --distance 3 --basis Z --level all
python -m validation.golden_memory.run --distance 3 --basis X --level all
python -m validation.golden_memory.run --distance 5 --basis Z --level all
python -m validation.golden_memory.run --distance 5 --basis X --level all
python -m validation.golden_memory.run --matrix --workers 8 --output /tmp/golden.json
```

The CLI defaults to eight spawned workers. The complete matrix dispatches 16
independent tasks. Tests use eight pytest-xdist workers; maintenance tests
regenerate only private temporary fixtures. No raw sample data or caches are
committed. Machine-readable final per-case evidence is stored beside this
report in `d3_z.json`, `d3_x.json`, `d5_z.json`, `d5_x.json` and `matrix.json`.

Final local results:

- Focused eight-worker pytest: **49 passed in 27.72 s**.
- Full eight-worker repository pytest: **1,446 passed in 472.92 s (7m52s)**;
  all 1,397 prior cases retained, no failures, skips or warnings.
- Ruff `src tests examples validation`: **all checks passed**.
- All four requested per-case CLI invocations: **A/B/C1/C2 passed**,
  with default worker limit eight. Wall times were 2.259 s (d3 Z),
  2.296 s (d3 X), 23.707 s (d5 Z),
  and 23.387 s (d5 X).
- Complete eight-spawn-worker, 16-task matrix: **all passed in
  24.045 s**. Every per-case report equals its corresponding matrix
  subset exactly. Timings are observations, never test thresholds.
- Fixture checksum/generator identity and documentation local-link audits pass;
  `git diff --check` passes. The read-only external Stim checkout is clean.

The initial focused gate passed 47 tests before two additional scope/metadata
negatives were added. The final full suite and final focused 49-test run both
include those additions and every final source change. No test result is
inferred from a prior commit or a different environment.

## Limits and remaining work

Verified scope is one patch, d=3/5, X/Z, exactly three syndrome rounds and the
specified ordinary-noise settings. There is no implemented-but-unverified
extension claimed by this suite. Multi-patch or interacting logical operations,
other rounds/distances/code families, M9/Knill/reuse, arbitrary noise policies,
LER/threshold/decoder optimality and new Windows/remote CI coverage are outside
this certification. Those retain their separate regressions and research
reports. No general noisy equivalence is claimed for the two different CX
schedules. No production defect or production source fix was needed.
