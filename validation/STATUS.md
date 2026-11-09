# STATUS — Research validation

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
