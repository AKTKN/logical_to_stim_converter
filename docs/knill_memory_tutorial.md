# Installed three-patch Knill consumer

This is a reproducible public-only **0.0.1** integration workflow, with an explicit
P0/P1/P2 schedule and one physical batch per case. The copied consumer resolves
random noiseless preparation sectors, propagates source-bound frame hypotheses
and reports final readout failures. Its **observed-last-sector / identity-readout**
adapter assumes last results are correct and does no temporal or joint Bell
inference. Noisy results demonstrate interface validity, not recovery accuracy.
No optional PyMatching/Matplotlib dependency is required.

## Supply the consumer and source

Follow the [external-directory installation instructions](ordinary_memory_tutorial.md#prepare-an-external-directory).
Copy the same [self-contained script](../examples/installed_consumer.py) beside your
input as `installed_consumer.py`; record its documentation commit SHA. It imports
only public converter APIs, NumPy and the standard library. Neither script nor
inputs are installed in the converter wheel, and no checkout is needed after
copying them. The input below is exactly the
[existing three-cycle source](../examples/lstim/three_patch_knill_d3.lstim).
Save it as **`three_patch_knill_d3.lstim`**:

```text
FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
PATCH P1 sc index=1
PATCH P2 sc index=2
BIND D P0
BIND A0 P1
BIND B0 P2
INIT_Z(3) D
KNILL_EC[cycle0](3) D A0 B0
SE(1) D
BIND A1 P0
BIND B1 P1
KNILL_EC[cycle1](3) D A1 B1
SE(1) D
BIND A2 P2
BIND B2 P0
KNILL_EC[cycle2](3) D A2 B2
SE(1) D
MZ D
```

D is the persistent logical state. Labels cycle0/1/2 identify composites;
source spans are provenance, not physical time. BIND reserves an explicitly named
available patch with no physical gates/time/noise. Only INIT starts a new epoch.
Each Knill resource uses three full SE rounds, and each following SE adds one.

| Cycle | Input D use | First resource use | Output use carrying D |
| --- | --- | --- | --- |
| 0 | P0/0 | P1/0 | P2/0 |
| 1 | P2/0 | P0/1 | P1/1 |
| 2 | P1/1 | P2/1 | P0/2 |

Seven `BlockUseId`s share three fixed patches and 51 physical wires; D ends on
P0/epoch2. Records/history grow with cycles; this bounds physical width only.
Preparation/readout/module IDs and use history retain retired resource handles.
See [physical identities](three_patch_knill.md#physical-identities-and-cycles).

## Run the four bounded cases

In your external directory, with the runtime-only environment active:

```sh
python -I installed_consumer.py knill three_patch_knill_d3.lstim --p 0 --shots 32 --seed 41
python -I installed_consumer.py knill three_patch_knill_d3.lstim --p .001 --shots 32 --seed 41
python -I installed_consumer.py knill three_patch_knill_d3.lstim --p 0 --m9 --p-st .003 --shots 32 --seed 41
python -I installed_consumer.py knill three_patch_knill_d3.lstim --p .001 --m9 --p-st .003 --shots 32 --seed 41
```

Each command builds native canonical DEMs and static maps/models, then samples
**once**. All subsequent offline hypotheses use the same immutable raw batch.
Shapes are bool raw [32,255], global events [32,192], final logical values/failures
[32,1] and residual physical X/Z maps [32,51] in global wire order. There are
10 boundary requests and seven destructive readout requests. A preparation has
24 selected raw records, eight ordered check targets and one prepared-logical
prediction target; its model-only probe measurements are not canonical records.

The ideal control resolves random nonzero gauge sectors and has zero final
failures in the verified 32-shot batch. Do not substitute zero physical
corrections merely because gate noise is zero. The ordinary noisy baseline has
13 failures in that same specified Linux/Python 3.12.7 smoke; a small observed
rate under this intentionally weak adapter has no threshold/accuracy implication.
All case-specific output counts are recorded in the [Phase 4 ledger](research_beta_0.0.1_plan_and_verification.md#phase-4--installed-consumers-and-tutorials-2026-11-09).

## Models, noise and the incoming hypothesis

M9 is configured through `NoiseModel(resource_preparation=ResourcePreparationNoise(...))`,
not through LSTIM syntax. `p_st_transversal` is finite, numeric, non-boolean in
**[0,.75]**, even disabled. Enabled zero still suppresses Bell-owned initialization
noise. Other active/waiting/gate noise uses ordinary rules.

The six exported `resource_preparation_boundaries` identify actual resource uses,
reset/final-SE layers, data sites and optional channel instruction indices. Each
nonzero channel is DEPOLARIZE1 on nine layout data sites, after final SE idle/TICK
accounting and before resource CNOT; concurrent resources can place adjacent
channels after the same TICK. No new TICK or ancilla target is added. Preparation
model-only probes end before their own post-SE faults. Later prefixes can retain
legitimate faults from earlier cycles; do not erase their physical history.

`make_conditional_readout_model(compiled, bell)` retains joint raw readout,
syndrome/logical and survivor-X/Z actions. Its incoming sector/frame hypothesis is
immediately before resource CNOT ordinarily, or immediately before the earliest
emitted resource post-SE channel in M9. Earlier residual errors are represented
only by the external hypothesis. With M9-only noise, each d=3 Bell window has
18 independent target locations and **54** categorical X/Y/Z atoms (three exclusive
alternatives per target at p/3). With ordinary background noise there are additional
atoms: never assert a total of 54 for that case. `exclusive_group` keeps alternatives
mutually exclusive. This is not a deterministic Stim DEM for random Bell bits and
it does not itself select corrections or propagate them through later program gates.

The script preserves exact models; its baseline deliberately ignores their fault
likelihoods. Preparation target MPPs remain model-only and are never sampled or
passed as decoder truth. Enabled nonzero widened windows crossing an intermediate
preparation/SE measurement on a Bell operand raise `UnsupportedProjectionError`.
Pure gate/idle waiting is supported, and the canonical circuit/global DEM remains
available even if that modular conditional cut is unsupported. The supplied source
avoids that cut. This tutorial does not implement the deferred #23 enhancement.
See [exact M9 boundaries](resource_preparation_noise.md#boundary-provenance-and-offline-decoding).

## Plug in your own StageDecoder

`prepare_knill(compiled)` in the copied consumer builds an immutable frame plan,
stage requests and conditional models once. `analyze_knill(setup, raw, decoder=...)`
accepts a consumer-owned object implementing `StageDecoder.decode_batch` and never
samples. It calls requests in `StageRequests.order` and supplies current local
events/records plus predicted readout sectors, never hidden physical faults or
sampled probe truth. A replacement can route by module ID to different adapters.

The included `ObservedSectorAdapter` reads the current last recorded check values.
It solves CSS equations over GF(2) for one physical sector representative, adding
a known prepared-logical constraint at initialization. It predicts zero last-result
errors and leaves readout records uncorrected. Its arbitrary free-variable-zero
representative is not minimum weight or a noisy preparation decoder. The baseline
still demonstrates correct handling of random preparation sectors at zero noise.

Each boundary returns `StageResult(CorrectionBatch(...), predicted_record_errors,
net_sector)`. Physical correction bits are X(data_ids), then Z(data_ids), shape
[shots,18]; readout hypotheses flip records in declared readout order, shape
[shots,9]. Results include source fingerprint, unique module boundary, BlockUseId
and explicit input column IDs. `net_sector` and predicted last-result errors are
[shots,8] in check order. Readout expected sectors use `sector_map` over the
request-set's ordered net sectors XOR `sector_constant`; do not subtract carried
physical frame anticommutation a second time.

`OfflineFrameBatch.apply` edits only interpreted copies and updates later Bell
feedback by XOR delta exactly once. Real resets clear old physical support;
legitimate teleported/classical dependencies survive reuse. Recompute events from
current records for each stage. The canonical full DEM and physical raw arrays
remain available and unchanged. A marginal DEM does not automatically become a
posterior after applying software frames. This external snippet replays one batch:

```python
import numpy as np
from installed_consumer import analyze_knill, prepare_knill
from logical_to_stim_converter import NoiseModel, parse_logical_file

compiled = parse_logical_file("three_patch_knill_d3.lstim").compile(noise_model=NoiseModel())
setup = prepare_knill(compiled)
raw = compiled.circuit.compile_sampler(seed=41).sample(shots=32)
raw.flags.writeable = False
first = analyze_knill(setup, raw)  # Replace decoder= with your StageDecoder.
second = analyze_knill(setup, raw)
assert np.array_equal(first["values"], second["values"])
assert np.array_equal(raw, first["batch"].raw_measurements)
assert not first["failures"].any()  # This assertion is for the noiseless control only.
```

Run saved application snippets with ordinary `python your_script.py` so Python
can import the copied consumer next to them. The CLI's `-I` command works because
that file executes directly and needs no sibling-module imports.

## Failure convention and supported rejections

After all chosen frame/readout hypotheses, the consumer XORs interpreted records
at each observable's **physical readout support**, then compares with its intended
`expected_value`. The frame plan already includes virtual Paulis and Bell feedback;
do not reapply the artifact's symbolic affine frame. Shot failures are corrected
physical readout XOR intent. Count `failures.any(axis=1).sum()` and divide by shots
for this strategy's empirical failure rate. Uncorrected canonical observable flips
are separate reference-relative labels, not automatically equal to the residual
failure of a modular decoder. Both remain available for external evaluation.

Explicit stale source/model fingerprints, wrong raw/correction shapes, old epochs,
swapped X/Z column labels and duplicate application fail in the documented APIs
or the consumer's source checks. Arrays cannot prove provenance by shape alone;
keep the fingerprint with data and rebuild all derived models when source changes.
Tests include these failures plus the unsupported intermediate operand SE cut.

Independent tests compare LSTIM with separately authored Python operations, verify
physical conditional atom propagation with Stim outside consumer inputs, and compare
noiseless sparse frame replay with strict physical-frame evaluation. This certifies
bounded wiring/mapping behavior, not noisy inference quality. For optional external
MWPM demonstrations and their approximations, see [examples](examples.md#external-knill-decoding-demonstrations);
production decoders, experiment sweeps and adaptive scheduling stay downstream.
