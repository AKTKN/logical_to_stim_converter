# Phase 1 code-capacity validator

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
