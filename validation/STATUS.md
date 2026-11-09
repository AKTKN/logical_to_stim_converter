# STATUS — Research validation

## Phase 3 — M9-only Knill fault enumeration and fits (2026-11-09)

Implemented research-only `m9_knill_faults.py` and `m9_knill.py`, with a
metadata/Stim-verified d=3 post-SE data-site inventory, exhaustive categorical
weight-0/1/2 assignment ranks, paired Stim physical Pauli oracle, conditional
raw/check/logical/survivor map audit, epoch and stage ownership checks, and
source-bound external restricted modular MWPM replay. An independent frozen
decoder at `p_ref=.01` reads only the same immutable physical record and causal
stage data. No runtime `src/` code, package pin, API or license changed. The
[dated report](reports/phase3_2026-11-09/REPORT.md), schema-v1 JSON,
assignment CSV.gz tables and point CSV contain the full protocol and results.

At d=3, one teleportation has 18 M9 sites and complete assignment counts
`1+54+1377=1432`; reused three-patch, three-cycle Knill has 54 sites, seven
physical uses, three relocations and `1+162+12879=13042`. All 14,474 ranks
were evaluated with 256 independent ideal branches per rank; all 14,256 pairs
passed independent physical GF(2) action checks. All 54/162 single atoms match
the six conditional maps, own preparation-prefix exclusions and Bell-window
ownership; all 81 selected retired-support epoch checks pass in r=3. Six
selected deterministic physical circuits per case pass. Both 512-branch ideal
baselines have zero failure. No physical/frame mismatch was found.

Observed `K1=0` but its 95% upper bound is 0.01599 for each case; sampled
`K2=216 [212.41,219.59]` for r=1 and `648 [637.03,658.97]` for r=3. The
corresponding `a2=K2/9-(N-1)K1/3` estimates are `24 [23.51,24.40]` and
`72 [70.50,73.22]`. These are statistical branch averages, not exact
analytical coefficients or proof of exponent 2. Twelve actual noisy-circuit
fixed-shot points use 12,582,912 total shots with eight spawned workers. Their
nominal Wilson intervals all overlap the weight-<=2 prediction interval plus
rigorous binomial weight->=3 tail. Free-power effective slopes are 1.949
`[1.892,2.007]` and 1.964 `[1.930,1.998]`; finite-p curvature fits are in
the report. This is evidence for the bounded M9-only circuits and frozen
restricted modular MWPM, not optimal joint decoding. Ordinary-background noise
and exact branch enumeration remain outside scope.

The full numerical command in the dated report completed in **346.09 s** with
eight spawned workers; largest observed worker peak RSS was **386.5 MB**. Its
assignment-table hashes, unique rank coverage, fixed-shot stops, frozen
decision checks and all 12 Wilson/prediction interval overlaps were audited
from the regenerated JSON/CSV.gz files. Focused new tests pass **8 in 34.93 s**;
the targeted eight-worker M9/Knill/frame regression passes **275 in 317.58 s**.
Ruff format/check on the new code and Ruff check on src/tests/validation pass.
The full eight-worker repository suite passes **1,397 in 722.79 s**. `git
diff --check` passes. No unexpected mismatch or confirmed new physical error
was found; restricted-MWPM inference and unsampled ideal branch possibilities
remain limitations, not confirmed converter defects.

## Phase 2 — ordinary circuit fault census (2026-11-09)

Implemented a research-only noisy ordinary-memory location scanner, independently
derived ideal-gate/time-layer inventory, categorical per-location atom table,
physical `FlipSimulator` single-fault oracle, raw-record parity check, signed
noiseless reference audit, canonical and decoder-view DEM Fourier marginals,
first-order coefficient check, bounded incomplete Pauli-pair sample, external
supported-graphlike PyMatching memory scoring, fixed-shot Wilson intervals and
uncertainty-aware effective-power fits. No installed `src/` API, package pins,
version or license changed. The
[dated report](reports/phase2_2026-11-09/REPORT.md) and schema-v1 JSON/CSV/gzip
tables give the full protocol, source hashes, counts, seeds, commands, worker
settings, wall times, fit diagnostics and limits.

Seven d=3/5, X/Z/1/3/5-round and H/signed/spectator controls cover **2,661
physical locations and all 15,567 single-fault alternatives**. All independently
inserted atoms match raw-record and physical global signatures. A deterministic
sample of 128 among 142,309 eligible cross-location d3 Pauli pairs passes;
measurement atoms and remaining pairs were not enumerated, so no circuit-level
second-order coefficient is claimed. Selected 4-bit categorical Fourier
marginals agree with canonical/view DEMs to at most `2.2e-14`; the maximum
tiny-scale first-order discrepancy is `2.29e-8`. The independently sampled
100,000-shot categorical table has maximum eligible-bin z score 2.00. Negative
controls detect altered gates, idle channels, physical map, site/record and
logical sign. Stim shortest graphlike-fault lengths are 3 and 5 in the selected
d-round cases; generated Stim memory has different physical schedules.

Two actual eight-spawn-worker fixed-shot runs took 19.14 s and 21.11 s,
respectively, totaling 7,864,320 shots. The lower-p Z-memory pure-power
effective slopes are 1.827 (d3) and 2.898 (d5), conditional on the fit form;
the circuit-level asymptotic exponent and coefficient remain unproven. Local
verification evidence: the eight-worker full suite passed **1,389 tests in
553.55 s**; the final targeted eight-worker run passed **191 tests in
32.14 s** after the spectator label, throughput and idle provenance changes. Ruff
format/check on the new files and Ruff check on src/tests/validation pass;
`git diff --check` passes. The full suite began before those narrow final
research-runner changes; the final targeted run covers them.
M9/Knill Phase 3, full joint finite-p validation, complete pair failure
enumeration, other code families and production decoding remain outside scope.

## Phase 1 — exact code capacity (2026-11-09)

Implemented independent hand-authored d=3/5 Z-check supports, brute-force
minimum-syndrome classes, exact integer census, rational polynomial conversion,
real PyMatching cross-check, exhaustive physical fault response, deterministic
process-task sampling, binomial intervals and weighted low-q fits. Physical
circuits are copied from verified converter ideal memory and edited only at the
declared post-initialization cut. Optional plots and versioned JSON/CSV reports
are generated. `src/` and package dependencies/version are unchanged.

The [protocol and actual experiment record](reports/phase1_2026-11-09/REPORT.md)
has the counts, coefficients, fit estimates, commands, source and circuit hashes,
statistical discrepancies, replication and scope. Local focused validator tests:
8 passed under eight workers in 9.30 s, without warnings; Ruff
src/tests/validation passes. The full suite passed 1381 tests in 602.93 s
before the final research-pool-only switch from fork to spawn; the final focused
spawn tests pass. Phase 2/3, circuit-level noise, Knill M9,
maximum-likelihood coset decoding and production decoder APIs remain outside this
phase. No issue, release, tag, license or package publication was changed.
