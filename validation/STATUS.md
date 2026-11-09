# STATUS — Research validation

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
