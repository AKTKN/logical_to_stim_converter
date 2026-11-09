# Validation Phase 3: d=3 M9-only Knill faults

**Outcome:** The bounded physical and numerical validation passed. All declared
weight-0/1/2 assignments were evaluated for one and three teleportations;
no physical/frame mismatch or failed ideal baseline was found. The sampled
failure curves are compatible with the low-weight predictions within their
reported uncertainty. This is evidence for the stated circuits and frozen
restricted modular MWPM, not a proof of an exact asymptotic exponent or of
optimal joint decoding.

## Reproduction and source identity

The compiler baseline is commit
`91407ba6dbf13a39d315446da3cb330ad9ee607b` (Phase 2). The command was
run from the repository root on 2026-11-09:

```sh
.venv/bin/python -m validation.m9_knill --cycles 1 3 --workers 8 \
  --batch-size 128 --shot-batch-size 8192 --branches 256 --seed 9903 \
  --max-shots 1048576 --target-failures 0 --max-seconds 240 \
  --p-values .001 .002 .003 .005 .008 .012 \
  --reference-probability .01 \
  --output-dir validation/reports/phase3_2026-11-09
```

Eight spawned processes were used on a machine reporting 20 CPUs. Stim 1.15,
PyMatching 2.3.1, NumPy 2.5.4 and the pinned stimflow commit
`ffe0d043598ed5df0851a3e6b4920359a23fafbd` were used. Each task rebuilds
the circuit and decoder locally; fixed assignment chunk and sampling task seeds
do not depend on worker number. The exact compiler fingerprints, ideal/noisy
circuit SHA-256 hashes, full site/use/channel inventory, timings and per-worker
peak RSS are in [report.json](report.json). The compressed
[`r=1` assignment table](assignments_d3_Z_r1_m9_only.csv.gz) and
[`r=3` assignment table](assignments_d3_Z_r3_m9_only.csv.gz) are rank-complete;
[memory_points.csv](memory_points.csv) contains the flat Monte Carlo grid.
No raw physical shot arrays were saved.

## Physical and decoder protocol

Both circuits compile public d=3 rotated-surface `|0>_L` Z-memory programs.
Only `ResourcePreparationNoise(enabled=True,p_st_transversal=p)` is active:
each Bell-resource half gets one physical `DEPOLARIZE1(p)` on each of its nine
data sites after its final preparation SE/TICK and before the resource CNOT.
Each site has categorical outcomes I/X/Y/Z with probabilities
`1-p,p/3,p/3,p/3`. Actual Stim instruction names, tags, target wires and
probabilities agree with `ResourcePreparationBoundary` use/epoch/site metadata.
No ordinary, ancilla, gate, idle, terminal readout or model-only MPP noise is
included. Enabled `p=0` reproduces the ideal physical circuit.

The one-cycle circuit has 51 physical qubits, 107 measurements, 80 global
detectors, three uses, one relocation, two resource boundaries and 18 M9 sites.
The reused three-patch circuit has 51 physical qubits, 255 measurements, 192
global detectors, seven uses, three relocations, six resource boundaries and
54 M9 sites. All 512 sampled ideal random-gauge/Bell branches per circuit have
zero final logical failure with either the ideal or frozen decoder. The ideal
flow and zero-event stage equations give the structural `K0=0` baseline.

A seeded *pair* of Stim `FlipSimulator`s executes the same ideal circuit, with
and without deterministic faults, and subtracts the same random stabilizer
gauges. This independently checks raw-record flips, all global detector and
observable flips, and survivor X/Z physical Pauli supports. Turning off
stabilizer randomization is unsuitable for recycled patches because post-reset
stabilizer markers can appear as false later record flips. Every single Pauli
alternative is checked against the conditional Bell model's six raw/check/
logical/survivor maps: 54 atoms in `r=1`, 162 in `r=3`. Every physical pair is
checked for GF(2) action composition: 1,377 and 12,879 pairs respectively.
Six selected assignments per circuit also pass explicit deterministic physical
Stim circuit sampling. Own post-SE faults are excluded from their preparation
prefix and included in the correct Bell window; the 18/54 exclusive channel
groups, reuse epochs and 81 retired-support checks in `r=3` pass. Decoder
decisions are recomputed from each combined raw syndrome, not XORed as though
MWPM were linear. No mismatches appear in the machine-readable counterexample
array. The preexisting unsupported intermediate-operand-SE projection remains
an explicit `UnsupportedProjectionError` contract.

The consumer-owned decoder is the repository's **M6-D restricted modular
MWPM**: correlated temporal boundary matching at the frozen `p_ref=.01` DEM,
unit-weight CSS sector capacity matching, then conditional unit-weight
per-patch readout matching, with PyMatching's default tie behavior. Its causal
`StageInputs` and source-bound correction batches are replayed once through the
existing offline frame plan. It sees physical records and causal stage data,
never injected-fault labels, final truth, or model-only preparation MPP probes.
The final failure is the corrected logical-Z readout XOR intended zero;
physical observable labels remain reference-relative. At each actual sampling
probability, the first 64 records are replayed under both source objects with
the same frozen decoder to check decision invariance. The approach ignores
joint inference across stages and is not an optimal Knill decoder.

## Complete assignment ranks and low-noise algebra

For `N` independent categorical sites, there are `1`, `3N`, and
`9*binom(N,2)` assignments of weights 0, 1, and 2. Both full sets were covered,
with 256 independent ideal branches *per assignment*:

| Cycles | N | Weight 0 | Weight 1 | Weight 2 | Total | Remaining |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 18 | 1 | 54 | 1,377 | 1,432 | 0 |
| 3 | 54 | 1 | 162 | 12,879 | 13,042 | 0 |

With `f_D(S,a)` the branch-averaged conditional failure probability for a
fixed decoder, `K_w=sum_{|S|=w,a} f_D(S,a)`, and
`P_L(p)=sum_w K_w(p/3)^w(1-p)^(N-w)` exactly. Thus
`a1=K1/3` and `a2=K2/9-(N-1)K1/3`. The observed assignment failure counts
were 0 at weight 0 and 1, and 55,296 (`r=1`) / 165,888 (`r=3`) failed
ideal-branch draws at weight 2. No assignment had mixed outcomes in its 256
draws. This is a sample observation, not a proof that every possible gauge
and Bell branch has the same outcome.

| Cycles | K1 estimate, 95% upper | K2 estimate, 95% interval | a2 estimate, 95% interval |
| ---: | ---: | ---: | ---: |
| 1 | 0, 0.01599 | 216, [212.41, 219.59] | 24, [23.51, 24.40] |
| 3 | 0, 0.01599 | 648, [637.03, 658.97] | 72, [70.50, 73.22] |

The coefficient intervals use independent-branch Hoeffding bounds with a
zero-success exponential bound and a three-weight allocation of nominal 5%
error. `a1` is estimated at zero with upper bound 0.00533 in both cases.
Because branch averages are sampled, neither `K1=0` nor the exact leading
exponent 2 is established. The data support a *candidate* quadratic leading
term. The full per-location/axis and cycle-pair failed-branch counts are in
`report.json` and the assignment tables.

At finite `p`, the reported partial prediction is
`K0(1-p)^N+K1(p/3)(1-p)^(N-1)+K2(p/3)^2(1-p)^(N-2)`.
Its branch-confidence interval is enlarged above by the rigorous
`Pr[Binomial(N,p)>=3]` bound; weight-three-and-above contributions were not
enumerated. This is not an exact finite-p formula from only the measured
`K0`–`K2`.

## Independent noisy-circuit Monte Carlo and fits

Each of six `p` values per circuit used 1,048,576 shots of the *actual* M9-only
converter circuit. The total was 12,582,912 shots, with fixed max-shot stops;
the nominal 95% Wilson intervals and prediction intervals are in `report.json`.
All 12 pointwise intervals overlap the weight-two prediction plus branch
uncertainty and higher-weight bound. Counts below are final corrected logical-Z
failures, with one raw batch reused for all decoder stages:

| p | r=1 failures | r=3 failures |
| ---: | ---: | ---: |
| .001 | 30 | 65 |
| .002 | 119 | 296 |
| .003 | 209 | 684 |
| .005 | 575 | 1,826 |
| .008 | 1,486 | 4,578 |
| .012 | 3,339 | 10,121 |

Observed-binomial weighted log-log fits give effective free-power slopes
`beta=1.949` (95% interval `[1.892,2.007]`) for `r=1` and `1.964`
(`[1.930,1.998]`) for `r=3`. The three-parameter finite-p curvature fits give
`beta=1.765` (`[1.551,1.979]`) and `2.017` (`[1.885,2.148]`) respectively;
their curvature parameters have intervals spanning zero and are weakly
identified on six points. These are finite-p effective fits with delta-method
counting intervals. They do not establish the asymptotic power. The code-capacity
Phase 1 prefactors `18`/`292` are unrelated to this M9 Knill channel.

## Verification status and limits

The focused Phase 3 validator tests pass **8 in 34.93 s**; the targeted
eight-worker M9/frame/Knill regression passes **275 in 317.58 s**; the full
eight-worker repository suite passes **1,397 in 722.79 s**. Ruff format/check
on new code, Ruff check on src/tests/validation and `git diff --check` pass.
[Validation STATUS](../../STATUS.md) records the final gate. All complete physical
checks above passed; no converter runtime file, package API, dependency pin,
license, release or tag was changed. The independent deterministic-circuit
spot check covers six assignments per case, while all pairs receive the paired
`FlipSimulator` physical action check. Branch probabilities and all fit
coefficients remain statistical. The decoder intentionally uses restricted
modular MWPM and leaves optimal joint inference untested. Ordinary-background
noise was excluded from this M9-only polynomial experiment.
