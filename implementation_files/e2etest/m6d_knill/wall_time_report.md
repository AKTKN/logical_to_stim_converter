# M6-D execution wall time and bottlenecks

The unprofiled eight-case CLI took **44.920 s**, including imports/startup,
all compilation/model setup, 160,000 physical shots, offline decoding and PNG/SVG/JSON/CSV
report generation. This final run had no concurrent test/profile/build workload
from this task. OS background activity was uncontrolled. These are single-run
observations on the recorded machine, not performance limits or timing confidence intervals.

CPU: 13th Gen Intel(R) Core(TM) i7-13700H; 20 accessible logical CPUs.
See [environment.json](environment.json) for OS/Python/thread settings.

Per-experiment wall times sum to **42.995 s**. Exclusive phase totals:

| Phase | Seconds | Share of experiment wall |
|---|---:|---:|
| Validated compilation | 21.119 | 49.12% |
| Global DEM / frame maps / stage and conditional models / matching setup | 8.084 | 18.80% |
| Sampler construction and physical sampling | 0.358 | 0.83% |
| m2d construction/conversion | 0.437 | 1.02% |
| Current stage events and input preparation | 6.678 | 15.53% |
| Temporal and capacity decoding | 1.535 | 3.57% |
| Frame transformations | 4.574 | 10.64% |
| Final evaluation and remaining overhead | 0.210 | 0.49% |

The **physical sampling call itself took 0.354 s** across all
160,000 shots. Validated compilation and setup account for roughly 68% of
experiment wall time at this batch size. Current-record event/input processing
and frame transformations together cost much more than MWPM or Stim sampling.

| d | Basis | T | Shots | Full experiment s | Compile s | Stage models s | Sampling s | Current events/inputs s | Frame updates s | Decode s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | X | 1 | 20000 | 1.015 | 0.417 | 0.170 | 0.0187 | 0.140 | 0.153 | 0.039 |
| 3 | X | 2 | 20000 | 2.199 | 0.775 | 0.470 | 0.0369 | 0.379 | 0.324 | 0.066 |
| 3 | Z | 1 | 20000 | 0.938 | 0.411 | 0.165 | 0.0091 | 0.119 | 0.126 | 0.039 |
| 3 | Z | 2 | 20000 | 2.119 | 0.738 | 0.451 | 0.0182 | 0.388 | 0.314 | 0.066 |
| 5 | X | 1 | 20000 | 5.949 | 3.435 | 0.633 | 0.0408 | 0.706 | 0.564 | 0.253 |
| 5 | X | 2 | 20000 | 13.271 | 6.584 | 2.040 | 0.0882 | 2.139 | 1.284 | 0.413 |
| 5 | Z | 1 | 20000 | 5.530 | 3.079 | 0.668 | 0.0391 | 0.657 | 0.551 | 0.237 |
| 5 | Z | 2 | 20000 | 11.972 | 5.679 | 1.756 | 0.1033 | 2.149 | 1.257 | 0.422 |

The d=5, X, T=2 case is the largest here: 13.271 s total, including 6.584 s
compilation, 2.040 s stage models, 2.139 s event/input preparation and 1.284 s
frame transformations; physical sampling is 0.0882 s. The stored CSV contains all
exclusive phases, including sampler setup and both m2d phases. Raw data are sampled
once per experiment; timing categories do not imply additional physical executions.

A separate instrumented d=5, Z, T=2, 1,000-shot profile is in
[profile_summary.txt](profile_summary.txt). Hot helpers include 159 flow
auto-rewrites (2.969 cumulative profiler s), 142 stabilizer-code builds, 43,239
Pauli-map products, 115,494 Pauli-map constructions, and repeated metadata
dataclass serialization. This supports the compilation/setup diagnosis. Profiling
adds overhead and its helper totals do not cover the complete instrumented wall
time (12.350 s); cumulative rows overlap and must not be summed or compared as
exclusive phase totals. The final unprofiled perf_counter phases are authoritative.

For an external experiment, reuse the compiled artifact, frame plan, stage models
and decoder objects across batches (`prepare_experiment` then `analyze_knill`).
Further optimization candidates are caching verified code geometry/reflow work
and reducing repeated full-record copies/validation with equivalent incidence-map
event updates. Those optimizations are future work and must retain exact physics,
source provenance and once-only frame semantics. No scheduling or physics check
was removed to improve the timings.

The LER results use a restricted modular baseline: temporal MWPM may choose an
ambiguous parallel-edge representative; per-patch unit-weight Bell capacity
matching does not perform correlated joint inference; strict one-round post-SE
has no internal temporal evidence. The timing comparison does not establish
decoder optimality or a threshold.

Full command and process wall: [execution_wall.json](execution_wall.json).
Exact parameters/versions/fingerprints/counts/phases: [knill_results.json](knill_results.json).
Physical RNG equality requires fixed Stim/version/machine/call structure.
