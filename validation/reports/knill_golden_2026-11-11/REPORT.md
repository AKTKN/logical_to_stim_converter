# Independent three-patch Knill golden validation — 2026-11-11

## Source, environment and independence

Converter baseline **`a11242efff9f36f22a729ef825b9b3ca4c85c10a`** contains the
previous golden-memory suite. Work uses dedicated branch
`validation/three-patch-knill-golden`. Actual Hex source is
**`5de58f2f80791054411ad3c0885a4fe3671ed56a`**, source version **0.1.0**.
Validation ran with converter HEAD at the baseline above plus the validation/doc
changes committed with this report. Live extraction checked the exact commit, clean checkout, original source and
matrix file hashes, and explicitly passed `surface_code=True`. No Hex source,
production converter source, dependency pin, package version or license changed.

Local execution uses Linux/WSL2, Python **3.12.7**, converter source/editable
metadata **0.0.1**, Stim wheel **1.15.0**, stimflow **1.17.dev0** installed from
`quantumlib/Stim@ffe0d043598ed5df0851a3e6b4920359a23fafbd`, NumPy **2.5.4**,
SciPy **1.18.1**, PyMatching **2.3.1**, pytest **9.2.0** and pytest-xdist **3.8.0**.
Optional live-Hex tools installed only in `.venv` are stimbposd **0.2.0**, ldpc
**2.4.1**, sinter **1.16.0** and tqdm **4.70.1**. Normal frozen validation neither
imports nor requires those tools. The pre-existing editable metadata said 0.0.0;
`pip install --no-deps --no-build-isolation -e .` refreshed it to the already
checked-out 0.0.1 source without changing any dependency. `pip check` passes.
The separately installed Stim release wheel is not claimed to be built from the
stimflow dev-source commit.

The [protocol](../../golden_knill/README.md) explains APIs, CLI, theory and
maintenance. There are two genuinely different reference constructions:

- Actual unmodified pinned Hex circuits, original module support remapping and
  native correction arrays establish ideal semantics. Constructor decoder stubs
  never provide recovery truth. The expensive correction-to-measurement flip map
  is not generated. Frozen sections/matrices are Hex exports, never DUT exports.
- An independently authored direct-Stim builder uses elementary geometry, the
  written global schedule, mathematical check/logical parity propagation and
  independent signed-flow elimination. Noise is appended directly with no
  production or stimflow noise factory. DUT construction is confined to its
  named adapter/comparison boundary.

Subprocess tests forbid production/Hex/test imports and network access during
independent construction/frozen loading. Fixture types and origins are explicit
in the [manifest](../../golden_knill/fixtures/manifest.json), which includes all
16 SHA-256 values, source/version provenance, arguments and expected counts.
Default tests/CLI verify frozen bytes and generator identities without rewriting
files. Regeneration requires an explicit flag and the actual pinned Hex checkout.

## Case matrix and exact ideal evidence

Principal cases use D one initial SE, resources A/B each d SE, one Knill operation,
three fixed P0/P1/P2 patches, and X or Z final B readout. Each case separately
passes A0/A1/A2/A3/B1/B2/C1/C2; the machine-readable
[matrix](matrix.json) records individual levels rather than one combined boolean.
Ideal A additionally exercises input bit 0/1. Tests separately cover bit-one
virtual frames; B checks open and closed outputs; C1 includes open survivor probes
and heterogeneous policies; C2 checks p_st=0/.003 with zero/nonzero backgrounds.

| Case | A0 | A1 | A2 | A3 | B1 | B2 | C1 | C2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| d3 X | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| d3 Z | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| d5 X | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| d5 Z | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

A0 independently verifies CSS commutation and rank, logical anticommutation,
reflected stabilizer row spaces and logical cosets from actual Hex matrices.
The reflection is `(row,col)->(row,d-1-col)`. Raw logical representative changes
carry explicit stabilizer-syndrome signs and are physically exercised before
recovery, rather than equating naive parity supports.

A1 checks each signed check measurement, preparation and nondemolition flow and
both logical Pauli transports. All measurement-only affine spaces are extracted
by multiplying actual signed Stim flows, eliminating input/output Paulis and
verifying candidates with Stim. Each Hex resource has rank **20/108** and **4/12**
free syndrome bits at d=3/5. Hex A1 signed preparation/round checks total
**164/764** per case and DUT A1 checks total **182/814**; Hex's unitary D
preparation is proved exactly from its default
initialized input. No deterministic first complementary-basis syndrome is assumed.

A2 proves all recovered resource checks and XX=ZZ=+1 using **18/50 exact signed
resource flows**. Independent GF(2) physical corrections commute with the chosen
logical strings. Each implementation additionally has 64 seeded physical-tableau
trials per input case; they exercise nonzero preparation gauges. A3 proves both
signed logical channel axes after **removing D preparation**, so the input is a
genuine operator port. Corrected Bell bits are two independent free outcomes by
exact rank. All four branches occur in each 64-trial case, and corrected open
states/closed readouts transfer input eigenvalue `(-1)^bit`.

Hex's native correction array is checked as `Z^(m_X), X^(m_Z)` at its original
post-Bell instruction cut, before stripping zero-probability channels. Converter
symbolic byproducts, D→P2 relocation, use history, and every physical survivor X/Z
frame site agree with an independent linear frame plan on the **same DUT raw
records**. The frames are then physically executed in separate tableaux. The
actual public closed artifact's signed parity is also verified. Hex and converter
raw samples are never compared shot-for-shot.

## Physical inventories and full record spaces

For bit-zero physical schedule cases, DUT and direct reference agree exactly:

| Property | d3 closed | d3 open | d5 closed | d5 open |
| --- | --- | --- | --- | --- |
| Occupied/allocated patch sites | 51 | 51 | 147 | 147 |
| Physical CX pairs | 186 | 186 | 930 | 930 |
| Moments / TICKs | 30 / 29 | 29 / 28 | 42 / 41 | 41 / 40 |
| Raw measurements | 83 | 74 | 339 | 314 |
| Canonical detectors / observables | 56 / 1 | 52 / 0 | 264 / 1 | 252 / 0 |
| Complete signed affine rank | 57 | 52 | 265 | 252 |
| Free raw-record bits | 26 | 22 | 74 | 62 |

Explicit physical bit-one inputs add a logical Pauli moment; virtual inputs add
no physical duration. B/C's numerical sentinels apply to the specified bit-zero
schedule, while signed-input tests independently validate their changed channels.
CX counts follow `4d(d-1)(1+2d)+2d²`. A/B resource rounds share global moments.
The detector basis map is an explicitly recorded invertible GF(2) transform;
observable cosets and individual semantic anchors are independently checked.
Native DEMs later use the independent reference basis in both circuits.

Hex native counts are intentionally different:

| Property | d3 | d5 |
| --- | --- | --- |
| Allocated patch sites / Stim index width | 51 / 51 | 147 / 147 |
| Actually addressed physical sites | 43 | 123 |
| Open / closed measurements | 66 / 75 | 290 / 315 |
| Native detectors / observables | 40 / 0 | 216 / 0 |
| Native TICKs | 0 | 0 |
| Initialized complete open rank / free bits | 48 / 18 | 240 / 50 |
| Initialized complete closed rank / free bits | 53 / 22 | 253 / 62 |

Hex's unitary input encoder never addresses D ancillas; occupied instruction
sites differ from the three allocated patch layouts. The unitary input makes
Hex's d=5 CX count basis-dependent; bits 0 and 1 have the same counts here:

| Hex case (both input bits, open or closed) | CX pairs | CZ pairs |
| --- | --- | --- |
| d3 X or Z | 123 | 72 |
| d5 X | 558 | 400 |
| d5 Z | 557 | 400 |

Exact counts are also stored in `Hex.A1.full_record_constraints.physical_counts`
and the fixture manifest. Hex uses
sequential check gadgets and opposite Bell-preparation orientation, so physical
count equality is not required.

Hex's native circuit omits explicit D reset because its simulator starts in |0>.
For full initialized raw-record spaces, the analysis explicitly prepends **only
an analysis R on D data**, never altering native fixture sections. Native
arbitrary-input flow ranks are reported separately: **40/216 open** and
**44/228 closed**. Every native declared detector is individually a valid signed
flow and the declared rows are independent, but native annotations are
intentionally incomplete for the initialized full experiment. Independent
propagated gauge/check/logical rows span exactly the full signed spaces above.
Bit-one cases preserve negative affine signs, rather than silently discarding
phases or interpreting a unitary encoder as an unconditional state reset.

## Ordinary noise, overrides, faults and M9

C1 compares complete causal noisy traces and atomic Counters with explicit
stage, patch/use, moment, parent, side, ordered targets and exact probability.
Ordinary settings are reset=.01, one_qubit=.02, two_qubit=.03,
measurement=.04, idle=.05. There are **zero physical 1q Clifford locations** in
this bit-zero schedule. Counts apply independently in both bases:

| Closed atomic locations | d3 | d5 |
| --- | --- | --- |
| Reset errors | 83 | 339 |
| CX depolarizations | 186 | 930 |
| Measurement-result flips | 83 | 339 |
| Active idle depolarizations | 720 | 2852 |
| D idles during A/B preparation alone | 323 | 1519 |
| Final B ancilla idles after data readout | 8 | 24 |

All reserved/uninitialized and retired uses are excluded independently. Per-stage,
per-patch, per-channel counts and actual probability sets are retained in the
machine-readable reports. Heterogeneous cases independently exercise instance >
primitive-type > global precedence, None inheritance and explicit zero disable.
D waiting noise is not suppressed by a resource preparation's policy.

Every physical instruction/channel remains when canonical annotations are
reconstructed. Native Stim DEMs, including all priors, hyperedges and native
correlation/separator structure, compare as exact objects. No rounded text,
decomposition, decoder model, removed mechanism or support-only equality is used.
Diagnostics include the first differing native row and exact float hex values.

Deterministic fault tables independently compare NumPy symplectic propagation,
Stim and DUT raw-record responses. Per case: **907/2451 closed** and
**922/2498 open** probes at d=3/5. Coverage includes all reset/result locations,
every Bell transversal CX pair's **15** nonidentity Pauli alternatives, selected
SE CXs, early/middle/late D waiting idles and every resource-boundary X/Y/Z data
fault. Open cases compare every physical survivor X/Z component. This is a
specified physical probe subset, not an exhaustive ordinary-fault census.
Terminal idle Pauli probes are individually classified inert: **24/72 closed**
and **48/144 open**. Other zero-signature mechanisms remain explicitly counted
by category; no physical channel is dropped.

C2 is separate from Hex and ordinary noise. Both Bell-owned prep intervals
suppress their ordinary reset/SE/result/idle channels, even at p_st=0. Exactly
**18/50** data channels are inserted at p_st=.003 after final SE/TICK and before
resource entangling CX, with no new TICK. Full-background p_st=0 counts are
reset/CX/result/idle **17/42/35/476** (d3) and **49/130/99/1944** (d5).
Nonzero p_st adds the 18/50 data depolarizations. Zero-background cases isolate
those special channels. Independent use/interval/data/cut expectations are
cross-checked against actual DUT boundary metadata after oracle construction.
All p_st/background variants have exact native common-basis DEM equality.

## Negative controls and reproducible verification

Each corruption begins with a passing baseline and asserts the designated cause:
SE CX deletion/direction/support; global moment timing; Bell-resource CX
orientation; Bell readout basis; dropped preparation recovery; swapped byproduct
axes or placement; signed input/logical cosets; detector/observable records;
reset errors moved before their **matching** reset; omitted/duplicated/altered CX
noise; changed result flips; missing waiting-D idle; reserved/retired idle;
M9 ancilla/double/wrong-cut channels; and restored prep noise at enabled p_st=0.
Extra noisy TICKs, tiny exact DEM-prior changes, and explicitly empty ordinary/M9
candidate circuits have explicit diagnostic tests. Missing optional arguments and
empty supplied circuits are distinguished.
A fault moved across a disjoint reset is legal commutation and is not called a
physical mismatch; the corresponding mutation targets the same qubit's reset.

Required commands use the existing `.venv/bin/python` on this machine:

```sh
python -m pytest -n 8 tests/test_validation_golden_knill.py -ra
python -m pytest -n 8 tests/test_validation_golden_memory.py tests/test_validation_golden_knill.py -ra
python -m pytest -n 8 tests/test_validation_golden_knill_hex.py tests/test_validation_golden_knill_fixtures.py -ra
python -m pytest -n 8 --durations=15
python -m ruff check src tests examples validation
python -m validation.golden_knill.run --matrix --level all --hex-repo external_lib/Hex \
  --workers 8 --output validation/reports/knill_golden_2026-11-11/matrix.json
python -m validation.golden_knill.run --matrix --level all --open-output \
  --workers 8 --output validation/reports/knill_golden_2026-11-11/open_matrix.json
```

The complete repository run used eight workers and passed **1,574 tests in
845.00 s**, including all 128 new Knill tests (84 primary, 21 Hex and 23 fixture
checks). No tests failed or were skipped. The earlier complete run passed
1,572 in 775.59 s before the last two empty-candidate regressions were added.
The required initial primary run passed 82 in 156.25 s; the initial combined
memory/Knill run passed 131 in 171.61 s. Both empty-candidate regressions then
passed in 7.08 s. The original 49-case memory baseline also passed independently
in 43.62 s.

Only mutation-test assertions were subsequently tightened: each Hex and fixture
corruption now establishes a passing baseline and checks its precise relevant
failure. The final focused rerun below covers these assertion changes; the
validation implementation did not change after the full run began.

Final eight-worker checks passed **133 in 272.02 s** (49 existing memory and
84 primary Knill cases), and **44 in 20.58 s** (21 Hex plus 23 fixture checks).
Together they cover every new test in its final assertion form.

The final [live principal matrix](matrix.json) passed **40/40 tasks in
243.101 s** with eight spawned workers: eight actual live-Hex ideal cases,
eight open/closed ideal physical cases, eight ordinary-noise uniform/heterogeneous
cases and sixteen M9 p_st/background combinations. Every actual Hex bundle matched
its frozen extraction, including original correction placement.

The final [open-output matrix](open_matrix.json) independently passed **40/40
in 236.854 s**, using frozen Hex inputs. Its eight ordinary and sixteen
M9 cases omit final readout and compare every survivor X/Z action; all have exact
native DEM equality. Open fault totals are 922/2498 at d=3/5, with all terminal
idle probes retained and inert. All separate A0/A1/A2/A3/B1/B2/C1/C2 entries pass.
Both JSON files retain full stage/use counts, exact probabilities, detector row
maps, branch/gauge and fault evidence rather than only an overall PASS.

Ruff over src/tests/examples/validation, formatting of all 17 new Python files,
`pip check`, whitespace, all 16 fixture SHA-256/LF checks and all local documentation
links pass. Actual pinned live Hex extraction also passed before the final matrix
refresh. Runtime source/pins and the upstream Hex checkout remain unchanged.

| Frozen independent oracle | SHA-256 |
| --- | --- |
| `same_d3_x_closed.stim` | `d1b5e5fdb8403b0d929e742ddda6dc9c91f948276b21c352ca6218ca8a898ae1` |
| `same_d3_x_open.stim` | `bd1666fffe5037989f32549cd7c777524ff3bb0aa3de572d6ee77d9e535bd692` |
| `hex_d3_x_bit0.json` | `3d9b90081795b84a597d0df0a9cbc3739d521bc2ddd7496bacb2b2502fe8dfb5` |
| `hex_d3_x_bit1.json` | `682e7b48716fb36dcd4b991ad121c3b0db5fb341ccf32e7650af05af719146f9` |
| `same_d3_z_closed.stim` | `cdb5584634fda69f9a7f5d88f20230f3f0c0600eab29858b4ee30164b2a7ea0f` |
| `same_d3_z_open.stim` | `466a2a410662bc6e5427d4e22758b84ab6a69a051a67164d3e173f7ecd5feee5` |
| `hex_d3_z_bit0.json` | `9e73b1072ce4b15ab9ba26421b7a160c233b2398ba5fdb9cb89fab35263aade9` |
| `hex_d3_z_bit1.json` | `2abbb0c5c6d9ede4ae2c883a1177f7aaaef7862db4a5f5145a18acff8339c3dd` |
| `same_d5_x_closed.stim` | `f566cd42ccbfafe571ab1e2daa2a993660b2ddd9361a3c2b1d49b52c097283c4` |
| `same_d5_x_open.stim` | `1432aeb542fa6ec3bb063c19877754cd13504a28a891313c29e5fdcae4387789` |
| `hex_d5_x_bit0.json` | `58e8a9c5535adea1ebadc30dd8017c768d7465603391b93865c19312abd5a234` |
| `hex_d5_x_bit1.json` | `c79478831a6b5ce316e2882e77cdd71734ff42ce6ae740af69a66d5061855df7` |
| `same_d5_z_closed.stim` | `9524190d3aa3669d6bd343be95c602d5e0cf35ba549fccc720e7083851382d63` |
| `same_d5_z_open.stim` | `3f6f6031a3fc64e5a04e47e94423158451778996886dd62d54bfb356d8c7c86c` |
| `hex_d5_z_bit0.json` | `bfafba53163791907fe1209edf1abe03029ad887d27a2f368a86bea8d10bd31c` |
| `hex_d5_z_bit1.json` | `0218031bed1969003c95e0e781daa2fe874826631617fe32095228320c68d574` |

Fixture maintenance is explicit:

```sh
python -m validation.golden_knill.run --regenerate-fixtures --hex-repo external_lib/Hex \
  --matrix --level all --workers 8
```

Review independent generator sources, actual Hex source provenance, all 16 hashes,
mathematical supports, signed flow/rank evidence, physical schedule and noise
matrix before accepting maintenance. Normal tests and CLI cannot overwrite
fixtures. Default tests run with no upstream checkout or network requirement.
No raw shots, cache or third-party implementation files are committed.

## Platform/CI evidence and remaining scope

The prior [a11242e workflow](https://github.com/AKTKN/logical_to_stim_converter/actions/runs/42952668261)
was inspected: Ubuntu Python 3.11/3.12 passed; Windows Python 3.11/3.12 failed six
fixture-checksum tests. The Windows 3.11 log had 1,440 passed / 6 failed and
identified four `.stim` hashes plus their dependent fixture/CLI tests. This task
adds `*.stim text eol=lf` and a scoped LF rule for the new Hex JSON fixtures,
preserving existing attributes. Private-Git tests actually check out all frozen
files with `core.autocrlf=true` and `core.eol=crlf`, proving identical literal
bytes under that conversion policy. This is not an actual Windows execution.

New-branch GitHub Actions had not run when this report was committed. The local
evidence above covers Linux/WSL2 and the simulated Git newline policy; it does
not establish Windows execution or a successful new-branch remote CI run. The
post-push completion message records the actual new workflow state separately.

Verified claims stay within one teleportation, d=3/5, the specified surface-code
schedules, X/Z and stated noise policies. There is no implemented-but-unverified
extension claimed by these oracles. Reuse/multiple teleportations, other code
families/rounds, decoder/LER/threshold/optimality, and equal Hex/converter noisy
DEMs remain outside certification. No independently reproduced production defect
was found and no production correction was made. All upstream source trees and
release dependency pins remain unchanged.
