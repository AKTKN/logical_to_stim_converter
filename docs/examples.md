# Ordinary memory, Clifford and Knill examples

The [README](../README.md#quick-start) has a standalone installed LSTIM quick start.
The Python blocks here also use installed runtime APIs. Commands under `examples/`
require a checkout/sdist; decoder/plotting commands additionally need `.[dev]`.
Example-layer functions are not installed consumer APIs. Complete installed
consumer tutorials remain Phase 4; see the [API reference](api_reference.md).

## Ordinary memory

Two independent patches can use different bases in the same physical layers:

```python
from logical_to_stim_converter import (
    CircuitCompiler, CodeSpec, LogicalBlock, LogicalInit, LogicalMeasure,
    NoiseModel, SyndromeExtraction,
)

code = CodeSpec.rotated_surface(3)
blocks = [LogicalBlock.placed(f"P{i}", code, patch_index=i) for i in range(2)]
compiled = CircuitCompiler(
    blocks, logical_to_block={"A": "P0", "B": "P1"},
).compile([
    [LogicalInit("A", "Z", rounds=1), LogicalInit("B", "X", rounds=1)],
    SyndromeExtraction(("A", "B"), rounds=3),
    [LogicalMeasure("A", "Z"), LogicalMeasure("B", "X")],
], noise_model=NoiseModel.uniform_depolarizing(.001))
compiled.validate_metadata()
assert compiled.circuit.num_qubits == 34
assert compiled.circuit.num_detectors == 64
events, flips = compiled.ideal_circuit.compile_detector_sampler(seed=7).sample(
    shots=8, separate_observables=True,
)
assert not events.any() and not flips.any()
```

Initialization includes its requested SE rounds; the subsequent SE adds rounds.
A nested list/tuple is one parallel logical layer. Physical layers align disjoint
operations and include waiting live patches for idle noise. Consecutive entries
are barriers. See [time and noise](architecture.md#parallel-assembly-and-time).

The source demonstration samples once, compares global/observable-local/strict
patch views, and lets external PyMatching predict reference-relative observable
flips in each view's local order:

```sh
python examples/two_patch_memory.py
python examples/memory_offline_decoding.py --suite --shots 128 --p .001 --seed 731
python examples/memory_offline_decoding.py --suite --shots 20000 --p .003 --seed 20261108 --output-dir implementation_files/e2etest
```

For these external predictions, shot failures are predicted XOR actual
reference-relative observable flips. Report any-observable and per-observable
counts separately; a finite failure rate is not a threshold estimate. Keep the
canonical undecomposed DEM. Explicitly requested graph decomposition retains
correlated `^` components, and the example rejects unsupported remaining
hyperedges. Correlated MWPM remains a heuristic, including parallel-edge fault-ID
ambiguities. Signed intended readout bits are specified in
[observable metadata](api_reference.md#measurement-and-protocol-metadata).

Old ordinary-memory figures/reports are available at their
[historical commit](https://github.com/AKTKN/logical_to_stim_converter/blob/d8654898e22248ba23afa9a65032eb7a9d83d075/implementation_files/e2etest/README.md).
The command above regenerates local aggregates. Report paths are output
destinations, not files promised to exist in a fresh checkout or wheel.

## Logical Clifford and Bell round trip

Logical H changes code orientation; CNOT pairs physical data according to both
orientations. Verified signed flows establish the intended logical action,
including mixed-orientation operands. H does not silently rename physical sites.
The current convention is southern-row logical X and western-column logical Z.
See [orientation and gates](architecture.md#m3-code-orientation-and-multi-block-gate-contract).

The [Bell round-trip example](../examples/two_patch_bell_roundtrip.py) prepares Z
on two patches, applies H(A), CNOT(A,B), then inverse gates and final Z readout.
It independently checks intermediate XX/ZZ and local expectations; a round trip
alone would not establish the logical action. Run:

```sh
python examples/two_patch_bell_roundtrip.py
```

`LogicalPauli(..., mode="physical")` executes the current data representative
with ordinary gate noise. `mode="frame"` changes the affine logical frame with
no physical gate, TICK or fault location. Y combines X/Z support up to global phase.
Readout interpretation must include affine constants and preparation-dependent
terms; detector-sampler flips alone are not absolute intended logical bits.

## Knill relocation and open continuation

This independent installed-API example leaves a verified output open, then appends
ordinary SE and readout:

```python
from logical_to_stim_converter import (
    CircuitCompiler, CodeSpec, KnillEC, LogicalBlock, LogicalInit,
    LogicalMeasure, SyndromeExtraction,
)

code = CodeSpec.rotated_surface(3)
blocks = [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate("DAB")]
opened = CircuitCompiler(blocks).compile([
    LogicalInit("D", "X", rounds=1),
    KnillEC("D", "A", "B"),
], allow_open_outputs=True)
assert opened.open_logical_outputs == {"D": "B"}
closed = opened.append([SyndromeExtraction("D", rounds=2), LogicalMeasure("D", "X")])
closed.validate_metadata()
closed.ideal_circuit.detector_error_model()
```

Knill prepares X(A)/Z(B), applies CNOT(A,B), CNOT(D,A), then X(D)/Z(A)
destructive readout. Persistent logical D moves to B's still-active use; A/B
temporary handles retire. `prepare_resource=False` consumes an existing verified
Bell resource. `BellStatePrep` defaults to d complete SE rounds per resource.
Append recompiles the prefix and continuation; it never physically executes a
stage again. Open export adds neither readout nor sampled MPP probes.

Raw Bell values are random records, not deterministic observables. Physical
preparation corrections are externally chosen; noiseless sector proofs and noisy
hypotheses have distinct validation modes in the
[frame API](api_reference.md#offline-frame-plans-and-corrections).

## External Knill decoding demonstrations

```sh
python examples/knill_ec_single_round.py
python examples/offline_dem_views.py
python examples/knill_memory_offline_decoding.py --suite --shots 64 --p .001 --seed 732
python examples/knill_memory_three_patch_reuse.py --suite --shots 32 --batch-size 13 --p .001 --seed 733
python examples/knill_resource_preparation_noise.py --shots 32 --p .001 --p-st .003
```

The fresh-resource M6-D example and repeated-use M7-C example remain separate.
The [three-patch guide](three_patch_knill.md) documents the authored cycle/use table,
bounded physical width, same-raw decoder replay and measured timing phases.
Temporal models estimate final-record errors; a capacity solver selects a physical
sector representative. Bell readout uses separate unit-weight patch matching.
These restricted adapters omit joint inference over correlated Bell/survivor
actions and cross-boundary SE offsets; incoming-sector mistakes and ambiguous
parallel-edge targets can fail. A single ordinary SE round has no internal temporal
detectors. Decoder inputs never include model-only probe truth or hidden errors.

`prepare_experiment` / `prepare_compiled` and `analyze_knill` in the source example
accept replacement `boundary_decoders` / `readout_decoders` by module ID. Replay
uses the same stored physical batch. Installed consumers should instead implement
the public [StageDecoder contract](api_reference.md#temporal-and-readout-stage-requests).
Final modular failure compares corrected physical readout XOR intended state,
which need not equal the uncorrected canonical observable flip label.

Setup/model construction is outside shot loops. Reports separate compilation,
DEM/frame/stage/conditional setup, sampling, event conversion, decoding, frame
updates, final evaluation and report wall time. Larger local report commands are
demonstrations, not throughput or numerical LER guarantees. Production orchestration,
factory policies and adaptive execution belong downstream.

## Physical text inspection

The [Japanese circuit/operation guide](../examples/stim_circuit_guide_ja.md),
[line map](../examples/stim_line_map.csv) and six checked-in ideal/noisy Stim
snapshots cover ordinary memory and open/closed Knill. The
[exporter](../examples/export_stim_circuits.py) regenerates them:

```sh
python examples/export_stim_circuits.py
```

For exact noise placement and M9 model ownership, use the
[resource-preparation guide](resource_preparation_noise.md). Stim text is an
inspection format; exact fingerprints/models retain immutable instructions and
full-precision arguments instead of relying on text round trips.
