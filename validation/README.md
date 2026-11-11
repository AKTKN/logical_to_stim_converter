# Research validation

## Independent three-patch Knill

The [Knill golden suite](golden_knill/README.md) separately certifies actual
pinned Hex corrected ideal geometry/instruments/Bell/teleportation semantics
and a production-independent direct-Stim physical/annotation/noise/M9 oracle.
It covers one teleportation, d=3/5 X/Z, open/closed outputs, signed inputs,
nonzero preparation gauges, all Bell branches, exact prior-preserving DEMs and
physical fault/survivor checks. Normal tests use frozen fixtures without Hex or
network access; an explicit live checkout audit is available. See the
[execution report](reports/knill_golden_2026-11-11/REPORT.md).

```sh
python -m validation.golden_knill.run --matrix --level all --workers 8
python -m pytest -n 8 tests/test_validation_golden_knill*.py -ra
```

## Independent golden memory

The [golden-memory suite](golden_memory/README.md) checks d=3/5 X/Z memories with
exactly three syndrome rounds using independent Stim-generator semantics,
matched elementary reset/readout faults, and a separately authored direct-Stim
physical schedule with complete gate/reset/readout/idle noise. Frozen fixtures,
signed affine-space proofs, mutation controls and an eight-worker CLI make the
checks reproducible. See its [dated report](reports/golden_memory_2026-11-11/REPORT.md).

```sh
python -m validation.golden_memory.run --matrix --workers 8
python -m pytest -n 8 tests/test_validation_golden_memory.py -ra
```

## Phase 1: code capacity

This directory is research-only. It is excluded from the installed package and
uses the optional dev dependencies PyMatching and Matplotlib. It compiles the
converter's ideal `|0>_L` Z-memory, inserts one independent data-X layer after
`LogicalInit`'s final `TICK` and before the next ideal syndrome round, and reads
Z-check detector and logical-Z flips. No ancilla, gate, reset, idle, measurement,
or M9 resource noise is present. The edited Stim circuit has its own SHA-256 and
does **not** inherit the unmodified `CompiledCircuit` source fingerprint.

Run from the repository root after installing `.[dev]`:

```sh
python -m validation.code_capacity --quick --workers 2 --output-dir validation/output
python -m validation.code_capacity --workers 2 --seed 731 --batch-size 4096 \
  --max-shots 100000 --target-failures 80 --max-seconds 60 \
  --distances 3 5 --q-values .008 .015 .03 .05 --plot \
  --output-dir validation/output
```

`--shots` aliases `--max-shots`. Tasks have fixed IDs and separate NumPy seed
streams independent of worker assignment. Every worker builds its own PyMatching
object and physical circuit; no compiled object crosses a process boundary.
Ordered task aggregation makes fixed-shot results reproducible across worker
counts. A wall-time stop can vary by machine. Up to eight process workers are
accepted; the default is at most four. The tiny exact census runs serially; the
physical pattern check is batched by Stim's `FlipSimulator`.

## Report schema v1

`report.json` has `schema_version=1`, implementation/source/version/settings,
integer `census`, `physical_checks`, `depolarizing_checks`, circuit SHA-256 and cut,
per-point counts/rates/Wilson intervals/reference bounds/stopping reason, four
weighted log-fit forms per distance and mode, and wall/CPU diagnostics.
`points.csv` is a flat summary. `--plot` adds `rates.png`. Source SHA identifies
the compiler baseline (`git rev-parse HEAD` at execution), while the circuit hash
identifies the verification-only edited Stim circuit. Raw shots are never saved.
The dated [Phase 1 report](reports/phase1_2026-11-09/REPORT.md) interprets actual
results and limitations; [STATUS](STATUS.md) records the verification gate.

The 95% Wilson point intervals are nominal binomial intervals. In runs that stop
at a target number of failures, optional stopping can change their coverage;
the fixed-shot replication is the stronger interval check. Fit intervals are
delta-method intervals from observed-binomial weighted log regression, conditional
on nonzero counts. They do not include finite-q model error or optional-stopping
effects. The three-parameter curvature fit on four q points is weakly identified.

## Phase 2: ordinary circuit fault census

`ordinary_circuit` validates the converter's actual ordinary rotated-surface
memory schedule, including reset, one- and two-qubit gates, measurement-result
flips, active idles and final readout. The research-only
`ordinary_faults` module scans actual noisy Stim instructions and derives an
expected location inventory separately from the ideal gates and time-layer
occupancy. It then inserts every categorical single-fault alternative in the
ideal physical circuit with Stim's `FlipSimulator` and compares raw-record XOR,
global detector/observable flips, canonical and selected-view DEM marginals.
The exact small-subset comparison uses a Fourier parity transform over mutually
exclusive alternatives at each location; it does not assume one DEM row per
atom. A d=3 physical Pauli pair sample is explicitly incomplete.

Run from the repository root with `.[dev]` installed:

```sh
python -m validation.ordinary_circuit --quick --workers 2 \
  --output-dir validation/output/phase2
python -m validation.ordinary_circuit --workers 8 --batch-size 16384 \
  --seed 9201 --max-shots 131072 --target-failures 0 --max-seconds 120 \
  --p-values .002 .004 .006 .008 .012 \
  --output-dir validation/reports/phase2_2026-11-09
```

The runner accepts at most eight spawned workers. It gives each task a stable
seed independent of worker assignment; each worker rebuilds its own circuit,
simulator and optional PyMatching decoder. `--batch-size` bounds in-flight
sampling; `--max-shots`, `--target-failures`, and `--max-seconds` limit each
memory point. The reported failure is any MWPM predicted observable XOR the
physical reference-relative observable flip, per **shot**. The decoder sees
detectors and its decomposed graphlike model, never the truth label. Unsupported
hyperedges are rejected. Point intervals are nominal Wilson intervals; fits
use observed-binomial weighted log regression and report effective exponents.
No circuit-level analytic exponent or coefficient is asserted.

Each deterministic `atoms_*.csv.gz` row records revision/fingerprint,
instruction/tag/module, cut/TICK layer, channel, stable site and use epoch,
batched target position, exclusive group, alternative and identity
probabilities, insertion convention, and absolute global detector/observable
IDs. `report.json` schema v1 records circuit hashes, exact census/DEM checks,
pair sample, first-order differences, point counts, fits, settings and wall
times; `memory_points.csv` provides a flat point summary. The dated
[Phase 2 report](reports/phase2_2026-11-09/REPORT.md) gives the actual commands,
results and limits. No raw shot data is stored. `src/` is unchanged.

## Phase 3: M9 Knill fault enumeration and fits

`m9_knill_faults` scans actual M9-only `DEPOLARIZE1` instructions and their
resource-boundary, physical-site and use-epoch metadata. It ranks every d=3
categorical assignment of weight 0, 1 or 2. A paired Stim `FlipSimulator`
checks raw/global detector/observable and survivor responses; the same immutable
raw record feeds the existing external M6-D restricted modular MWPM and causal
offline frame replay. Assignment failure probabilities are averaged over
sampled ideal random gauges and Bell branches. `m9_knill` also samples actual
noisy circuits with decoder weights frozen at `p_st=0.01`.

Run a capped check or reproduce the full eight-worker experiment:

```sh
python -m validation.m9_knill --quick --workers 2 \
  --output-dir validation/output/phase3_quick
python -m validation.m9_knill --cycles 1 3 --workers 8 --batch-size 128 \
  --shot-batch-size 8192 --branches 256 --seed 9903 \
  --max-shots 1048576 --target-failures 0 --max-seconds 240 \
  --p-values .001 .002 .003 .005 .008 .012 \
  --reference-probability .01 \
  --output-dir validation/reports/phase3_2026-11-09
```

`--max-patterns` selects a deterministic rank prefix and marks coefficients
incomplete; `--quick` applies that cap. Spawned workers reconstruct their own
circuit and decoder, with chunk seeds independent of worker count. `report.json`
schema v1 contains source and circuit hashes, boundary/site/use metadata,
physical checks, rank coverage, sampled `K_w` and coefficient intervals,
location/Pauli resolved counts, binomial-tail-bounded predictions, Wilson
intervals, fits and timing/memory diagnostics. Each compressed
`assignments_*.csv.gz` row records a rank, fault sites/axes, failed ideal
branches, physical signature masks and source identity. `memory_points.csv`
summarizes actual noisy-circuit Monte Carlo. The dated
[Phase 3 report](reports/phase3_2026-11-09/REPORT.md) explains the results.
No raw shot arrays are committed.

Assignment locations and physical responses are exhaustive within these
circuits. `K_1`, `K_2` and fitted slopes remain statistical because ideal branch
averaging is sampled; zero observed single-fault failures do not prove an exact
exponent. The finite-p partial probability covers weights through two, and its
upper interval adds the rigorous higher-weight binomial tail. The decoder is
restricted modular MWPM, not optimal joint Knill inference. Runtime `src/`
is unchanged.
