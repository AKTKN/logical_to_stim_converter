# Phase 1 exact code-capacity validation — 2026-11-09

## Model and independent checks

The single data fault layer is after the verified Z initialization's last
`TICK` and before the second ideal syndrome round's ancilla reset. Stim data
wires come from `physical_qubit_map`, not local column guesses. The logical
label is the compiled signed expected logical-Z value 0, and the failure bit is
the MWPM prediction XOR the physical reference-relative logical-Z flip. The
brute-force solver enumerates syndrome classes using hand-transcribed d=3/5
Z-check supports and first-row logical-Z support. It never receives the true
error when decoding; the error is used only to score the result. PyMatching
uses `Matching.from_check_matrix(H_Z, faults_matrix=L_Z,
weights=log((1-q)/q))`. The only shared assumptions are physical data order,
rotated-patch geometry, and which compiled detector/observable IDs correspond to
the chosen Z memory. The reference checks match `CodeSpec`, but reference results
do not call `CodeSpec`, converter metadata projections, or a converter decoder.

Let `t=(d+1)/2`. If an error of weight `w<t` failed, a minimum correction has
weight at most `w`; their combined nontrivial logical-X chain would have weight
at most `2w<d`, contradicting distance. A weight-`t` subset of a length-`d`
logical-X string shares a syndrome with its weight-`t-1` complement and therefore
fails under minimum-weight correction. Thus the exponent is exactly `t`.
Each X stabilizer has even weight and logical X has odd weight. Two corrections
of equal weight differ by an even-weight chain, so minimum-weight ties cannot
change the logical class. This is checked exhaustively for every visited syndrome.

| d | Visited patterns | Failure counts | A | B | Minimum-correction ties |
|---:|---:|---|---:|---:|---:|
| 3 | all 512 | `[0,0,18,56,57,69,28,18,9,1]` | 18 | -70 | 10 |
| 5 | all 15,276 through weight 4 | `[0,0,0,292,4333]` | 292 | -2091 | 5,620 |

The exact d=3 polynomial is
`18q² - 70q³ + 99q⁴ - 6q⁵ - 168q⁶ + 240q⁷ - 144q⁸ + 32q⁹`.
At d=5 the exact known binomial-basis terms are
`292 q³(1-q)²² + 4333 q⁴(1-q)²¹`; the omitted failure probability lies in
`[0, Pr(Binomial(25,q)≥5)]`, never assumed zero. The Taylor beginning is
`292q³ - 2091q⁴ + O(q⁵)`. Substituting `q=2p/3` for **one** data
`DEPOLARIZE1(p)` layer gives leading `8p²` at d=3 and `2336p³/27` at d=5
when scoring only logical Z. It does not describe noisy syndrome extraction or M9.

Stim `FlipSimulator` checked each of the 512 d=3 and 15,276 d=5 patterns against
independent GF(2) syndrome/logical expressions, including zero/low weights,
random preparation gauges and signed expected label. Wrong data order, logical
support and late insertion are negative controls. Single-site X and Y yield
identical selected Z-check/logical-Z responses; Z yields zero selected response.
The full one-layer channel therefore has the same selected distribution at
`q=2p/3`. Its X-check detector distribution differs. An independent 20,000-shot
physical comparison at `q=.04, p=.06` found d=3 failures 488 (X) versus 492
(depolarizing), and d=5 failures 274 versus 300. These counts are compatible at
binomial resolution and are recorded with circuit hashes in the JSON.

## Bounded numerical run

Command (Linux/WSL2 Python 3.12.7, 20 visible CPUs):

```sh
.venv/bin/python -m validation.code_capacity --workers 2 --seed 731 \
  --batch-size 4096 --max-shots 100000 --target-failures 80 --max-seconds 60 \
  --distances 3 5 --q-values .008 .015 .03 .05 --plot \
  --output-dir validation/reports/phase1_2026-11-09
```

Wall time 19.33 s; 653,952 total sampled shots and 1,399 observed failures
across independent algebra and physical streams. All eight d=3 nominal 95%
Wilson intervals contain the exact probability. The d=5 rigorous bound overlaps
six of eight intervals. The two exceptions are physical q=.008 (24/100,000,
95% `[.000161,.000357]`, bound `[.00014028,.00014180]`) and algebra q=.015
(62/100,000, 95% `[.000484,.000795]`, bound `[.00086643,.00089783]`).
They are isolated finite-sample discrepancies. There is no minimal failing
physical pattern: all covered deterministic patterns agree. Adaptive stopping
also makes these intervals nominal rather than exact coverage statements.

An independent fixed-shot replication used seed 732, two workers, 300,000 shots
per mode at q=.008/.015 and took 39.98 s:

```sh
.venv/bin/python -m validation.code_capacity --workers 2 --seed 732 \
  --batch-size 4096 --max-shots 300000 --target-failures 0 --max-seconds 120 \
  --distances 5 --q-values .008 .015 \
  --output-dir validation/reports/phase1_2026-11-09/replication
```

At q=.008 it found algebra 33/300,000 and physical 44/300,000; at q=.015,
254/300,000 and 251/300,000. All four fixed-shot 95% intervals overlap the
rigorous bounds. Across both runs there were 1,853,952 shots and 1,981 failures.

The weighted log fits use observed binomial delta-method weights. For the main
run, unconstrained two-parameter power fits gave physical `beta₃=1.865`
(`95% [1.725,2.004]`) and `beta₅=2.696` (`[2.501,2.890]`). The finite-q
curvature fit `log P=log A+beta log q+cq` gave physical `beta₃=2.416`
(`[1.851,2.981]`) and `beta₅=2.568` (`[1.746,3.390]`); both include the exact
exponents 2 and 3 but are broad. Constraining beta to theory and fitting
curvature gave physical `A₃=19.56` (`[16.07,23.80]`) versus exact 18 and
`A₅=337.47` (`[260.56,437.09]`) versus exact 292. These are finite-q,
four-point estimates; the three-parameter fit has one residual degree of freedom
and unstable A/c extrapolation. Pure power fits drift with q because B is negative
for both distances. The JSON contains all fits, covariance-derived intervals,
normalized `P/q^t`, counts and timing. These intervals quantify sampling in the
fitted model, not finite-q model error or adaptive-stopping coverage.

The graph is [rates.png](rates.png). The full [report.json](report.json),
[points.csv](points.csv) and [fixed-shot replication](replication/report.json)
are compact, reproducible artifacts; no raw samples are stored.

## Provenance, checks, limitations

The compiler source at execution was `be734ce71c5140a9e01ccd1fdb2d181678cef663`
(main HEAD before this validator). Stim 1.15.0, PyMatching 2.3.1 and NumPy 2.5.4
were inspected and recorded. The final report uses validator implementation
`phase1-2` with explicit spawned workers. Physical ideal/edited circuit SHA-256, cut indices,
data wires, seed/task settings and actual wall phases are in JSON. The inserted
Stim circuits are verification-only and cannot claim the original compiled source
fingerprint. The validator commit is the commit containing this report; no
runtime compiler bytes changed. Focused tests and repository-wide checks are
tracked in [validation STATUS](../../STATUS.md) and root STATUS.

This validates one uniform data-X layer and ideal Z memory at d=3/5 with uniform
minimum-weight syndrome decoding. It makes no claim about arbitrary geometries,
maximum-likelihood coset decoding, circuit noise, physical correction, M9/Knill,
other CSS families or production decoder interfaces. Phase 2 and 3 remain separate.
