# LSTIM physical and simulation certification (M8-D)

The frontend compiles to the same existing physical experiment as an independent
Python program when code/placement, explicit binding order, operation labels,
logical barriers and noise match. The tests compare Stim objects and exact
floating-point probabilities, including correlated DEM components; printed Stim
text is not an exact serialization or a physical proof.

## Paired runnable sources

Run from a checkout or sdist with `.[dev]`:

```bash
python examples/lstim_equivalence.py --shots 32 --p 0.001 --seed 826
```

The [example](../examples/lstim_equivalence.py) reads the exact frozen
[memory source](../examples/lstim/memory_d3.lstim) and
[three-patch source](../examples/lstim/three_patch_knill_d3.lstim) and independently
constructs both references with existing public operations. References do not
inspect ASTs, call the parser/lowering, or use the M7 runner to generate programs.
For example, the complete memory reference is:

```python
code = CodeSpec.rotated_surface(3)
compiler = CircuitCompiler(
    [LogicalBlock.placed("P0", code, patch_index=0)], logical_to_block={},
)
reference = compiler.compile([
    BindPatch("D", "P0"), LogicalInit("D", "Z", 3),
    SyndromeExtraction("D", 1), SyndromeExtraction("D", 1), LogicalMeasure("D", "Z"),
], noise_model=NoiseModel.uniform_depolarizing(0.001))
```

The example's `python_knill_reference` explicitly writes all three `KnillEC`
calls, initial and later bindings, post-SE operations and readout, matching source
labels cycle0/1/2. Its reset/relocation history is:

| Cycle | Data input | Resource A | Output B / continuing D |
|---|---|---|---|
| 0 | P0/0 | P1/0 | P2/0 |
| 1 | P2/0 | P0/1 | P1/1 |
| 2 | P1/1 | P2/1 | P0/2 |

The local Linux Python 3.12.7 run above, with Stim 1.15.0, stimflow 1.17.dev0
at ffe0d043, Lark 1.3.1 and PyMatching 2.3.1, produced:

| Source | Qubits | Raw records | Detectors | Observables | Canonical DEM errors | Decoder failures / 32 |
|---|---:|---:|---:|---:|---:|---|
| memory_d3 | 17 | 49 | 40 | 1 | 492 | 0 global, 0 observable-local, 0 strict patch-local |
| three_patch_knill_d3 | 51 | 255 | 192 | 1 | 2698 | 4 restricted Knill (LER 0.125) |

Both canonical DEMs start with probability `0.0019311827343106622` on targets
`D0 D2` for this noise model. Reports retain full Python float values and target
lists for this illustrative error; equality uses full Stim DEM objects. The
script asserts exact ideal/noisy circuits, canonical DEMs, source identities,
same-seed records, and shared-raw offline outputs. It checks that analysis leaves
raw records and canonical DEMs unchanged. Counts are seeded observations on this
platform, with no cross-platform RNG or LER-target claim; within each test process
the two identical experiments must sample bitwise identically.

## Tested matrix and independent checks

| Test group | Verified cases |
|---|---|
| Physical memory (48) | d=3/5; X/Z; initialization 1/d rounds; extra SE; two separate repeated SE(1)s; absent/physical/frame Pauli; noiseless/nonuniform noisy channels |
| Parallel (4) | d=3/5; unequal 3/1 SE rounds, concurrent H/readout, ideal/noisy; exact TICKs and independently counted gate/idle noise |
| H/CNOT and Bell (8) | d=3/5, both H orientations, ordered CX and signed frame; reverse physical patch order for Bell resources, default/explicit rounds, exact once-only noise |
| Knill physics (32) | d=3/5, X/Z, bits 0/1, T=1/3, post-SE 0/1, nonuniform noise; 51/147 fixed wires, 3/7 uses and exact labelled child provenance |
| Reuse/open outputs (6) | d=3/5; independent Z/X epochs with/without active spectator; epoch-local observables, reset frame extinction; open three-cycle outputs without fake readout |
| Ordinary decoder E2E (18) | d=3/5 X/Z, physical/frame signed states, p=0/.003; independent two-observable order/locality; global/local MWPM predictions and reference-relative labels |
| Knill decoder E2E (16) | d=3/5 X/Z bits 0/1, T=3, post-SE=1, p=0/.003; baseline and M7 replacement adapters over one shared raw batch |
| Offline batch replay (2) | X/Z signed cases, 257 shots at p=.01; one batch versus 13/134/110; one static sampler/sample call with quantum execution prohibited afterward |
| Independent physical probes (2) | Untouched encoded reference through all Bell branches, actual correction execution; physical fault before/after reset versus historical Bell feedback |
| Safeguards (28) | Located syntax/semantic failures, lifecycle/overlap/resource errors equal direct Python, impossible layout, mixed-distance CX, corrupted signed H flows, stale epoch/source corrections |

The test-only structural comparator checks every public CompiledCircuit field,
including exact signed chunk/reflow/loop content, maps, record/observable parity,
TimeLayer sites/uses, preparations, Bell records, reset/terminal module IDs,
causal ancestry and composite children. Both artifacts validate metadata and signed
flows. Canonical ideal/noisy DEMs match; exactly decomposable ordinary-memory
models additionally match with `DEMOptions(decompose_errors=True)`.

Separate samplers with the same explicit seed produce identical records and m2d
outputs for matched circuits. Decoder views project one shared batch and retain
all physical faults, canonical source identity, reference samples and global/local
maps. Comments/diagnostic filenames do not enter physical identity. Explicit
labels and authored bindings are matched metadata; legacy M7 helpers with implicit
initial reservations are separate physics regressions, without forced fingerprint
or seed equality across different experiments.

Ordinary-memory E2E uses `examples.memory_offline_decoding.analyze_memory`.
Knill E2E uses unchanged `prepare_compiled`/`analyze_knill`, comparing boundary
targets/DEMs, conditional Bell fault windows/atoms and causal stage inputs, predicted
sectors, CorrectionBatch bits/use/column identities, current interpreted records,
physical X/Z frames, logical outputs, failure vectors, counts and LER. Timings are
excluded from equality. Replacement adapters use existing M7 public-input wrappers
and independently weighted readout matching. Replay never samples ideal boundary
MPP probes or consults hidden quantum truth.

The independent physical checkpoint also reruns both d=3/5 M7-C encoded-reference
tests. New physical probes use actual tableaux, projective measurements, executed
Paulis and FlipSimulator faults, rather than treating decoder agreement as proof.
Reset clears obsolete physical support while legitimate classical Bell corrections
continue with teleported D. Historical MeasurementKeys and correction boundaries
remain distinct across repeated physical uses.

## Boundaries and performance

Tests use finite seeded batches and the existing restricted external decoders.
Correlated two-pass MWPM is heuristic; Bell capacity matching uses approximate
unit-weight per-patch inference. No claim of optimal decoding, arbitrary LER,
threshold, or correctness for every possible v1 program follows from these cases.
Strict noiseless physical proof stays separate from noisy correction hypotheses.

Source loops unroll statically and preserve barriers. Fixed physical-state width
does not bound circuit size, records, metadata or model-building time. d=5 paired
compilation and boundary/conditional setup dominate these small-shot tests;
pytest-xdist uses eight processes, with no wall-time pass/fail threshold.
The installed wheel needs no examples/tests/reference copies or optional decoder/
plotting dependency; both samples compile in an isolated consumer on the existing
Ubuntu/Windows Python 3.11/3.12 CI matrix. The new paired-source example is an
eighth CI command, with bounded 32-shot d=3 inputs.

Resource-creating/labeled REPEAT, automatic allocation, runtime conditionals,
arbitrary code/backend plugins, non-Clifford gates, text-defined noise/decoders
and a language CLI remain deferred. Converter/compiler/decoder runtime sources
and the M7-C runner are unchanged by this certification milestone.
