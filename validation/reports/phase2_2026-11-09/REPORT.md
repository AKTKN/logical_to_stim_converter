# Phase 2 ordinary-memory circuit fault census — 2026-11-09

## Protocol and physical identities

This research-only stage uses the converter's verified ordinary rotated-surface
memory physical circuit, not its decoder fault-action maps. The noisy circuit is
scanned instruction by instruction, while the expected inventory is derived
separately from ideal tagged operations, four interleaved CNOT layers and the
active physical-use occupancy at each `TICK`. Each batched target/pair is one
exclusive physical location. Reset and measurement channels each have one
alternative; one-qubit depolarization has three at `p/3`, and two-qubit
depolarization has 15 at `p/15`. Identity has probability `1-p`. A measurement
atom flips the reported bit at measurement. The oracle propagates every atom
through the ideal circuit using Stim `FlipSimulator`, independently computes
absolute detector/observable parity from raw record indices, and checks Stim's
reported flips. Random ideal gauge outcomes and signed logical labels are
checked separately. One-qubit H noise, active idles, concurrent spectator
operations, and retirement are covered.

The shared assumptions are the compiler's ideal physical schedule, coordinate
map, tagged operation boundaries, and chosen memory basis. The inventory rule,
physical fault insertion, raw-record parity and per-location distribution are
authored in `validation/`, separate from the compiler noise injector, DEM
construction, decoder views and frame maps. The oracle is therefore independent
of those converter transforms, while still testing the converter's ideal
circuit rather than an unrelated reference circuit.

| Case | Physical locations | Fully checked single atoms | Control |
|---|---:|---:|---|
| d3 Z, 1 round, nonuniform | 112 | 556 | reset/gate/readout/idle |
| d3 X, 3 rounds, uniform | 268 | 1,536 | X memory |
| d5 Z, 1 round, uniform | 312 | 1,700 | larger patch |
| d5 X, 5 rounds, uniform | 1,168 | 7,724 | long X memory |
| d3 X, H then readout, nonuniform | 129 | 607 | 9 one-qubit H locations |
| d3 Z, virtual X, nonuniform | 112 | 556 | signed expected logical 1 |
| d3 Z, concurrent spectator, nonuniform | 560 | 2,888 | active/retired idles |
| **Total** | **2,661** | **15,567** | no unsupported atom type |

The nonuniform vector is `(p_reset,p_1q,p_2q,p_meas,p_idle) =
(.001,.002,.003,.004,.005)`; uniform census controls use `.001` in each
channel. For the d3 Z one-round case, 128 deterministic cross-location **Pauli**
pairs were checked against physical two-fault propagation and the XOR of their
single signatures. There are 142,309 eligible cross-location Pauli pairs;
measurement-result atoms and all other pairs are excluded. This pair sample is
explicitly incomplete, and no second-order circuit coefficient is inferred.

For global detector IDs 0–2 and observable 0, the complete categorical-location
Fourier distribution equals the canonical DEM, selected decoder-view DEM and
decomposed full-view DEM to at most `2.2e-14` across the seven cases. This is
an exact small-marginal comparison, allowing aliased atoms, full DEM hyperedges
and `^` components; it does not equate DEM rows to physical atoms. At a
`1e-5` common probability scale, the largest first-order signature-coefficient
difference is `2.29e-8` (spectator), consistent with finite-scale higher-order
terms. The independent categorical sampler's 100,000 d3 trials have maximum
binomial z score 2.00 among bins with expectation at least five. The chosen
subset is a bounded marginal; this does not certify the entire joint event
distribution at finite noise.

Negative controls detect reversed CX targets, swapped check-gate order, missing
and extra idle noise, reset and readout site changes, wrong physical map, late
measurement-error insertion and altered signed observable expectation. Unit
tests also reject unsupported matching hyperedges and invalid settings. The
existing `test_memory.py::test_circuit_distance` evidence is retained; the
selected d3 X/3-round and d5 X/5-round noisy circuits have Stim shortest
graphlike-fault lengths 3 and 5. Their generated Stim memory references also
have lengths 3 and 5, but physical `TICK` schedules differ. Neither equality
of graphlike length nor Phase 1 code-capacity distance implies equal LER or a
decoder-specific circuit exponent.

## Eight-worker sampling and fits

Commands (Python 3.12.7, 20 visible CPUs, eight spawned workers; Stim 1.15.0,
PyMatching 2.3.1, NumPy 2.5.4):

```sh
.venv/bin/python -m validation.ordinary_circuit --workers 8 \
  --batch-size 16384 --seed 9201 --max-shots 131072 \
  --target-failures 0 --max-seconds 120 \
  --p-values .002 .004 .006 .008 .012 \
  --output-dir validation/reports/phase2_2026-11-09
.venv/bin/python -m validation.ordinary_circuit --workers 8 \
  --batch-size 65536 --seed 9202 --max-shots 524288 \
  --target-failures 0 --max-seconds 120 \
  --p-values .0005 .001 .0015 .002 .003 \
  --output-dir validation/reports/phase2_2026-11-09/low_p
```

The first run took 19.14 s and sampled 1,572,864 fixed shots, with 120,366
failures across ten Z fit points and two X controls. The second took 21.11 s,
sampling 6,291,456 fixed shots and 161,922 failures. Counts below are failures
out of 131,072 (first run) and 524,288 (second run), **per complete shot**:

| d, Z rounds | First p grid → failures | Lower p grid → failures |
|---|---|---|
| d3, 3 | `.002:854, .004:3052, .006:6347, .008:10587, .012:19755` | `.0005:288, .001:951, .0015:1999, .002:3526, .003:7224` |
| d5, 5 | `.002:198, .004:1700, .006:5148, .008:10917, .012:25903` | `.0005:19, .001:122, .0015:378, .002:938, .003:2958` |

X-memory controls were d3 X/3-round at `p=.008`: 10,019/131,072 and
39,797/524,288; d5 X/5-round at `p=.012`: 25,886/131,072 and
103,722/524,288. One scale `p` controls five independent channel types at
their actual physical locations. The external decoder is PyMatching's two-pass
correlated matching on a decomposed view whose components have at most two
detectors. It receives detector samples and its declared DEM, while physical
observable flips are held out until scoring. Unsupported hyperedges are
rejected; this decoder is a defined approximation on the supported decomposition.

Weighted log fits `log(P)=log(A)+beta_eff log(p)` on the lower grid give
`beta_eff=1.827` (conditional 95% `[1.786,1.868]`) at d3 and `2.898`
(`[2.799,2.996]`) at d5. The three-parameter curvature fits
`log(P)=log(A)+beta_eff log(p)+c p` give `1.820` (`[1.644,1.996]`) and
`2.877` (`[2.351,3.403]`), respectively. The wider grid has substantial
curvature: pure-power slopes 1.692 and 2.387 versus curvature-fit slopes
2.028 and 3.465. These are **effective finite-p** estimates, not established
asymptotic exponents or analytic coefficients. The lower-grid curvature terms
are weakly identified and 19 failures at the d5 lowest point leave material
count uncertainty. Wilson point intervals and full fit diagnostics are in the
machine-readable reports. The nominal fit intervals condition on positive
counts and the fitted form; they exclude finite-p model error.

## Artifacts, provenance and limits

Validation commands included the full eight-worker suite and a final targeted
eight-worker run:

```sh
.venv/bin/python -m pytest -n 8 --tb=short --durations=10
.venv/bin/python -m pytest -n 8 -q \
  tests/test_validation_ordinary_circuit.py tests/test_noise.py \
  tests/test_clifford_noise.py tests/test_memory.py \
  tests/test_decoder_views.py tests/test_global_detector_provenance.py --tb=short
.venv/bin/python -m ruff format --check \
  validation/ordinary_faults.py validation/ordinary_circuit.py \
  tests/test_validation_ordinary_circuit.py
.venv/bin/python -m ruff check src tests validation
git diff --check
```

The full suite passed 1,389 tests in 553.55 s. It started before the narrow
spectator case-label, throughput and idle-provenance changes; the final targeted run
after those changes passed 191 tests in 32.14 s. Ruff and whitespace checks
passed. The validator's own eight fast tests passed separately in 7.06 s.

The [main JSON](report.json), [main CSV](memory_points.csv),
[lower-p JSON](low_p/report.json), [lower-p CSV](low_p/memory_points.csv) and
deterministic `atoms_*.csv.gz` tables retain physical location identities,
absolute signatures, exact counts, hashes, seeds, settings, worker count and
wall times. The compiler baseline at execution is
`d3a34d47cc10d1272e11125ed34a87925bec6621` (the committed Phase 1
HEAD). The validator commit is the commit containing this report. No runtime
source or installed dependency changed. The checked-out stimflow reference
remains pinned at `ffe0d043598ed5df0851a3e6b4920359a23fafbd` per package
metadata; Stim's batched-channel merging and measurement-result semantics were
checked against the installed 1.15 API during this work.

This stage proves the enumerated single-fault responses and declared small
distribution identities for these seven circuits. The pair audit is sampled,
full high-dimensional finite-p equivalence is unconfirmed, and no complete
decoder-failure coefficient has been enumerated. The distinct Stim-generated
memory schedule prevents a like-for-like LER comparison. M9/Knill Phase 3,
other code families, production decoding, and release work remain separate.
