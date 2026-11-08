# Three-patch Knill memory

The source example `examples/knill_memory_three_patch_reuse.py` builds one static
physical circuit. Caller-authored triples select exactly three rotated-surface
patches; explicit BindPatch directives reserve the measured sites before their
next resource preparation. No allocator or runtime scheduling enters the compiler.

## Physical identities and cycles

Each physical patch contains d² data plus d²-1 check ancillas, at fixed wire
indices. A use `(patch, epoch)` is one reset-to-destructive-readout occupancy.
Epoch counts generations, independently of syndrome-extraction (SE) rounds,
logical gates and physical TICKs. Persistent logical D survives teleportation;
fresh A_t/B_t names identify temporary resource states. Each full Knill cycle
prepares a Bell pair, entangles encoded blocks and destructively measures D/A.
B's physical use stays active under D after its temporary name retires.

| Cycle | D input use | A use | B/output use | D after cycle |
| --- | --- | --- | --- | --- |
| 0 | P0/0 | P1/0 | P2/0 | P2/0 |
| 1 | P2/0 | P0/1 | P1/1 | P1/1 |
| 2 | P1/1 | P2/1 | P0/2 | P0/2 |
| 3 | P0/2 | P1/2 | P2/2 | P2/2 |
| 4 | P2/2 | P0/3 | P1/3 | P1/3 |

A stage labels a semantic subcircuit, such as cycle 2's B preparation. A physical
time layer is a TICK interval for gates/idle noise. A decoder boundary is a cut
where an external algorithm returns a Pauli/readout hypothesis, without sampled
quantum truth. Resource preparation defaults to d full SE rounds; independently
configured post_rounds adds ordinary SE after every teleportation.

## Running and reusing samples

```bash
python examples/knill_memory_three_patch_reuse.py --suite --shots 2048 --batch-size 256 --p 0.003 --seed 20261108 --output-dir implementation_files/e2etest/m7c_three_patch
python examples/knill_memory_three_patch_reuse.py --teleportations 10 --shots 9 --batch-size 4 --p 0 --bit 1
```

Source-level functions expose the authored program, canonical compiled artifact,
prepared consumer and bounded aggregate run. `build_explicit_three_patch_knill`
accepts open outputs and all existing noise models. `prepare_three_patch` reuses
M6-D `prepare_compiled`; `analyze_knill(experiment, raw, boundary_decoders=...,
readout_decoders=...)` replays a stored batch without physical execution. All
stage instances receive current interpreted records/events and predicted sectors,
never model-only MPP outcomes, actual error frames or an expected final-bit truth
column. Final labels compare corrected physical readout with intended input.

`run_three_patch` compiles once, creates one sampler and calls sample once per
requested bounded batch. It drops each analysis/raw batch after aggregating
errors, timings and a stream hash. The hash identifies the actual call sequence;
Stim does not promise identical random streams across batch sizes/platforms.
Offline chunking of the **same stored samples** is exactly equivalent.

Only physical-state width stays constant: 3(2d²-1) = 51 at d=3, 147 at d=5.
Physical gate/record/detector counts and historical metadata grow with cycles.
Frame-plan and temporal-model construction also grow; this is not a constant
total-memory or runtime claim. Sampling is static, without per-stage quantum
resimulation, physical decoder corrections, retries or adaptive feed-forward.

Reports write aggregate JSON, phase CSV and PNG/SVG LER/timing figures without raw
shots or internal correction matrices. They include actual cycle uses, immutable
use/owner/binding/relocation history, module/stage IDs, selected global detector/
record IDs and counts, caller-derived view IDs, v3 source fingerprints, a SHA256
of exact flattened DEM instruction types/float arguments/targets, decoder identity
and explicit restrictions. Report wall time is separate from run wall phases.

The inherited baseline uses temporal correlated MWPM plus a CSS capacity sector
representative for preparation/ordinary SE, and independent unit-weight Bell
patch capacity matching. Ambiguous parallel-edge targets, omitted cross-boundary
SE offsets and residual incoming-sector mistakes can cause failures. The exact
global DEM and conditional correlated/exclusive fault actions stay available to
other decoders. Neither optimal joint inference nor threshold behavior is claimed.

## Verification evidence

See root STATUS and tests/STATUS for exact final commands/counts/platform results.
Tests independently execute physical tableaux and Pauli corrections for d=3/5,
both X/Z signs, random preparation gauges and all Bell branches. Three working
patches plus an untouched encoded reference retain XX/ZZ after three teleports.
Unfolding each use to a fresh patch preserves exact gate/noise atoms, probabilities,
module/TICK ordering and selected deterministic fault truth tables at both distances.
Independent noisy streams use conservative 99.99% Wilson interval overlap, without
requiring equal random bitstreams. Every Bell-interval Pauli atom is checked with
Stim FlipSimulator, including 15 exclusive DEPOLARIZE2 alternatives and survivor
actions. Use-local models retain excluded-region physical faults and compare exact
marginals; temporal targets remain model-only. Negative tests reject old preparation/
use hypotheses and detect missing later Bell feedback, wrong-epoch record edits
and physical frame copied through reset. Replay checks both decoder selections,
immutable sources/raw records, causal once-only boundaries, exact chunk equivalence,
honest noisy failure labels and a ten-cycle bounded-batch smoke.

The demonstration command above produced these observations on Linux/WSL2,
Python 3.12.7, Stim 1.15.0, PyMatching 2.3.1 (2026-11-08). Each case uses three
cycles, p=0.003, 2,048 shots in eight 256-shot batches; these are restricted
decoder results, not threshold estimates or evidence that larger d helps it.

| d | Basis | Physical qubits | Records | Detectors | Failures / shots | LER | Run wall (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | X | 51 | 255 | 192 | 454 / 2048 | 0.22168 | 2.631 |
| 3 | Z | 51 | 255 | 192 | 553 / 2048 | 0.27002 | 2.582 |
| 5 | X | 147 | 1087 | 912 | 652 / 2048 | 0.31836 | 14.823 |
| 5 | Z | 147 | 1087 | 912 | 651 / 2048 | 0.31787 | 13.796 |

Report generation took 0.618 s. At d=5/X, compile/physical validation took
9.603 s, temporal stage/view models 3.628 s, frame-map setup 0.267 s, conditional
fault models 0.361 s, sampling 0.009 s, current-event inputs 0.324 s, temporal/
capacity decoding 0.162 s, and frame updates 0.186 s. These observations were
made alongside tests, without performance thresholds.

The separate T=10 d=3 smoke used nine noiseless signed-Z shots in batches 4/4/1:
51 qubits, 773 records, 584 detectors, zero failures. Run wall was 10.540 s:
compile 3.415 s, temporal stage/view models 5.877 s, frame-map setup 0.294 s,
conditional models 0.837 s, sampling 0.00046 s. Prefix/model construction was
the largest measured setup cost here, rather than frame maps or sampling. Larger
T can increase symbolic/dense planning and repeated prefix/fingerprint work;
this bounded smoke establishes physical width and correctness, not asymptotic
setup-memory or throughput guarantees. JSON/CSV/PNG/SVG artifacts are generated
locally under implementation_files/e2etest/m7c_three_patch and m7c_ten_cycle;
raw shot matrices are neither saved nor committed.
