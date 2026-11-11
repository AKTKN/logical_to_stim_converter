# Independent three-patch Knill golden validation

This research suite validates **one teleportation**, using three rotated-surface
patches at d=3/5, X/Z input and resource rounds equal to d. Input D has one
initial syndrome round. The closed case ends with a destructive logical readout;
the open case leaves D physically on P2/B. It adds no decoder or installed runtime
API. See the [execution report](../reports/knill_golden_2026-11-11/REPORT.md).

Two references have different jobs. Actual pinned Hex establishes corrected ideal
instruments, Bell states and logical channel semantics. A separately authored
same-schedule direct-Stim reference establishes exact physical gates, annotations,
ordinary noise and M9. Hex and the converter have different noisy schedules;
equal Hex/converter native noisy DEMs are not an acceptance criterion.

## Run and interpret

From the checkout with `.[dev]` installed:

```sh
python -m validation.golden_knill.run --distance 3 --basis Z --level hex-ideal
python -m validation.golden_knill.run --distance 3 --basis Z --level same-ideal
python -m validation.golden_knill.run --distance 3 --basis Z --level ordinary-noise
python -m validation.golden_knill.run --distance 3 --basis Z --level m9 --p-st .003
python -m validation.golden_knill.run --matrix --level all --workers 8 --output golden.json
python -m pytest -n 8 tests/test_validation_golden_knill.py -ra
python -m pytest -n 8 tests/test_validation_golden_knill*.py tests/test_validation_golden_memory.py -ra
```

Default runs use checked-in frozen Hex/reference fixtures, require no network,
and never import Hex or its optional decoder packages. `--hex-repo PATH` adds a
live extraction audit from **`5de58f2f80791054411ad3c0885a4fe3671ed56a`**. Every
live circuit/matrix/provenance bundle must equal its pinned frozen extraction.
Do not provide an arbitrary checkout or substitute a new Hex imitation.

The CLI accepts `--distance {3,5}` (default 3), `--basis {X,Z}` (Z), `--level
{hex-ideal,same-ideal,ordinary-noise,m9,all}` (all), `--matrix`, `--workers 1..8`
(default 8), `--hex-repo PATH`, `--bit {0,1,both}` (both, ideal channel cases),
`--open-output` (noise cases), `--p-st FLOAT` (.003), `--background {zero,nonzero}`
(nonzero), `--output PATH`, and explicit `--regenerate-fixtures`. Same-ideal always
checks open and closed cases. Ordinary noise checks uniform and heterogeneous
settings. `all` expands M9 into p=0/.003 with zero/nonzero ordinary backgrounds.
The complete default matrix has **40 tasks** and separate A0/A1/A2/A3/B1/B2/C1/C2
results. Pool workers use `spawn`; each constructs its own DUT. Failures have a
nonzero exit code plus structured stage/site/moment/flow/parity/noise diagnostics.
Reported wall times are observations, never test thresholds.

## Independence and ideal semantics

`hex_adapter.py` calls actual pinned upstream constructors with
`surface_code=True` explicitly, including the original module support remapper,
transversal CNOT, Bell measurement and final logical measurement. Constructor-only
zero decoders satisfy upstream interfaces; their results never supply oracle
truth. The expensive correction-to-measurement flip-map generation is not called.
The live checkout and source file hashes are verified; upstream files stay clean.
Portable JSON fixtures retain actual sections, matrices and correction arrays.

A0 reflects the second data-array coordinate, proves CSS commutation/rank and
logical anticommutation, and compares stabilizer row spaces and logical cosets.
A stabilizer difference in a logical representative carries its measured syndrome
sign. Tests exercise the raw signed representative relation before recovery.

A1 proves each signed check measurement/preparation/preservation flow, both logical
Pauli transports and the complete measurement-only affine constraint space. Hex
uses hook-aware sequential check gadgets with H/CZ/H and MR conventions; its
ancilla output resets are not equated to converter destructive MX/M outputs.
Complementary first-round checks remain random. Signed Gaussian elimination uses
actual `stim.Flow` multiplication and verifies candidate relations with Stim.

A2 derives deterministic free-zero CSS recovery representatives over GF(2), with
logical-commuting constraints. All recovered code checks and Bell XX=ZZ=+1 have
exact signed-flow proofs and separate physical-tableau trials with nonzero gauges.
Hex prepares A in Z, B in X and applies B→A; the converter prepares A in X, B in Z
and applies A→B. Both give the corrected encoded Bell resource.

A3 derives effective Bell bits, propagating physical X/Z frames independently of
both decoder systems. D→A followed by MX(D), M(A) requires `Z_B^mX X_B^mZ`.
The genuine two-axis channel proof **removes D preparation**, making its logical
Pauli an input port. It proves X_D→X_B and Z_D→Z_B with the independently derived
record-parity corrections. Exact rank proves both Bell bits independent. Seeded
64-trial tableaux separately exercise all four branches, input bit 0/1 and open
and physically corrected closed outputs. The converter's public same-raw frame
evaluation, every survivor X/Z support, symbolic byproduct and D→P2 relocation
are checked against that independent plan. Physical and virtual signed inputs
have separate tests.

## Exact physical and noise reference

`spec.py`, `reference_same_schedule.py` and `reference_noise.py` use elementary
geometry and direct Stim, with no converter/Hex construction, noise factories,
production metadata or saved DUT circuits. They may reuse the independent
single-patch golden-memory geometry. A subprocess blocks production, Hex and
test imports and network access while constructing references and noise.

The schedule is D reset plus one SE, concurrent A/B resets plus d SE rounds,
resource CX(A,B), Bell CX(D,A), simultaneous MX(D)/M(A), then optional MX/M(B).
Check directions are X=`NW,SW,NE,SE`, Z=`NW,NE,SW,SE`. Independent physical lifetimes
activate all sites of a patch in its first data-reset moment and retire it after
its destructive-readout moment. D remains idle-eligible during resource creation;
reserved and retired patches are excluded.

B1 compares every physical moment/TICK, basis, CX direction and per-wire causal
order through occupied-coordinate mapping. Only disjoint operations inside one
moment may commute. B2 independently authors check anchors and logical parities,
proves the complete signed affine space, and checks actual metadata. An invertible
GF(2) row map records detector basis changes; logical observable cosets are checked
modulo that independent detector space. No annotation is copied from the DUT.

| Closed case | d=3 | d=5 |
| --- | --- | --- |
| Patch sites / CX pairs / TICKs | 51 / 186 / 29 | 147 / 930 / 41 |
| Raw records / detectors / observables | 83 / 56 / 1 | 339 / 264 / 1 |
| Complete signed constraint rank / free bits | 57 / 26 | 265 / 74 |

Open cases have 28/40 TICKs, 74/314 records, 52/252 detectors and no observable.
Hex's unitary input addresses no D ancillas: it allocates 51/147 patch sites but
actually addresses 43/123, with different record/annotation counts. These native
counts are reported separately, not forced to equal the converter's counts.

C1 manually inserts reset=.01, 1q=.02, 2q=.03, result=.04 and idle=.05 channels.
The independent resolver checks instance > primitive type > default, with None
inheriting and zero disabling. There are no physical 1q Clifford locations in
this bit-zero schedule. Ordinary closed reset/CX/result/idle location counts are
**83/186/83/720** (d3) and **339/930/339/2852** (d5), counted atomically.

The full causal instruction stream and a Counter of every location agree. Keys
retain stage, patch/use, physical moment, parent occurrence, side, channel,
ordered targets, probability and per-wire ordering. Canonical native Stim DEMs
are extracted after independently reconstructing common annotations. Every
physical instruction/channel, prior, hyperedge and native correlation component
is retained; no rounded text, decomposition or removed fault establishes equality.

Independent binary symplectic propagation is checked against Stim and DUT for all
reset/result locations, every Bell-CX pair's 15 Pauli alternatives, selected SE
CXs, early/middle/late D waiting idles and all resource-boundary X/Y/Z faults.
Open cases also compare every physical X/Z survivor action. Terminal ancilla idle
faults are retained and individually classified as inert. Negative controls
reject each specified physical/frame/annotation/noise/timing corruption after its
baseline succeeds.

C2 independently suppresses ordinary resource preparation noise from A/B data
reset through final SE, including enabled p_st=0. Post-SE data-only channels
follow the existing final TICK and precede resource CX, without new duration.
Other operations and D waiting idles retain ordinary rules. Both p_st=0/.003
and zero/nonzero backgrounds are checked. Per-resource use/boundary metadata is
cross-checked only after constructing the independent expectation.

## Fixture maintenance and platform bytes

`fixtures/manifest.json` distinguishes independently authored direct-Stim
fixtures from actual Hex extractions. It records source/version provenance,
arguments, counts, SHA-256 and independent generator hashes. Default tests and
CLI only read them. To intentionally regenerate after reviewing the specification
and pinned upstream APIs:

```sh
python -m pip install stimbposd==0.2.0 ldpc==2.4.1
python -m validation.golden_knill.run --regenerate-fixtures --hex-repo external_lib/Hex \
  --matrix --level all --workers 8 --output golden-live.json
```

Review all fixture, source/hash and matrix diffs; never regenerate to conceal an
unexplained DUT mismatch. Maintenance tests modify only private copies. The Hex
checkout is optional, ignored and read-only; no third-party implementation is
vendored or imported by installed consumers. The optional extraction dependencies
above are development tools, not new project dependency pins.

`.gitattributes` forces `*.stim` and this suite's fixture JSON to LF. A private Git
repository checks actual fixture bytes after checkout under `core.autocrlf=true`
and `core.eol=crlf`. That is a simulated checkout-policy test, not a Windows OS
execution claim; actual CI status is recorded separately in the execution report.
Certification remains bounded to the specified one-teleportation d=3/5 protocols;
no decoder/LER, reuse, other schedule or Hex-vs-converter noisy equivalence is
claimed.
