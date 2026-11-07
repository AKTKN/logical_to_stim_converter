# logical_to_stim_converter

**Status (2026-11-07): verified memory and multi-block H/CNOT/Pauli circuits.**

Compile Python logical-operation objects into physical Stim circuits for independent
square rotated surface-code patches, including interacting logical Clifford circuits.
The memory path implements code algebra,
physical layouts, signed stabilizer/logical flows, concurrent syndrome extraction,
destructive readout, decoder-independent metadata, and circuit-level noise.

The package is independent of `knill_bench`. Sampling and later decoder/experiment
comparison belong to the caller. No decoder or logical error-rate benchmark is
implemented here.

## Installation

Requires Git and Python 3.11 or later with a compatible Stim wheel. From this
project directory:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
python -m build
```

The package pins **Stim 1.15.0** and installs **stimflow 1.17.dev0** directly from
Stim commit `ffe0d043598ed5df0851a3e6b4920359a23fafbd`, subdirectory
`glue/stimflow`. Installation needs network access to GitHub; no local
`external_lib/` copies are required. See [development notes](docs/development.md).

## Two independent patches

```python
from logical_to_stim_converter import (
    CircuitCompiler, CodeSpec, LogicalBlock, LogicalInit, LogicalMeasure,
    NoiseModel, SyndromeExtraction,
)

code = CodeSpec.rotated_surface(3)
blocks = [LogicalBlock.placed(f"patch{i}", code, patch_index=i) for i in range(2)]
compiler = CircuitCompiler(
    blocks, logical_to_block={"data0": "patch0", "data1": "patch1"},
)
result = compiler.compile([
    [LogicalInit("data0", basis="Z", rounds=1),
     LogicalInit("data1", basis="X", rounds=1)],
    SyndromeExtraction(("data0", "data1"), rounds=3),
    [LogicalMeasure("data0", basis="Z"), LogicalMeasure("data1", basis="X")],
], noise_model=NoiseModel.uniform_depolarizing(0.001))

ideal = result.ideal_circuit
noisy = result.noisy_circuit
ideal_dets, ideal_obs = ideal.compile_detector_sampler(seed=7).sample(
    shots=100, separate_observables=True,
)
assert not ideal_dets.any() and not ideal_obs.any()
dem = noisy.detector_error_model()
dets, obs = noisy.compile_detector_sampler(seed=8).sample(
    shots=100, separate_observables=True,
)
```

Run the complete example with `python examples/two_patch_memory.py`. It produces
34 physical qubits, 64 detectors, two observables, and 26 physical layers.
Initialization contributes one SE round; the subsequent operation adds three.

A list/tuple of operations forms an explicit parallel layer. An operation with
multiple targets also acts concurrently. Consecutive entries form barriers; the
compiler does not automatically move operations across them. Mixed X/Z bases,
different SE round counts, and waiting patches are supported. A memory experiment
is a composition of these three primitives; there is no dedicated experiment class.

## Interfaces and metadata

- `CodeSpec(name, n, k, d, H_X, H_Z, L_X, L_Z, metadata=...)` validates binary CSS
  algebra, GF(2) ranks, and logical pairing. Matrices have immutable byte backing.
  `CodeSpec.rotated_surface(d)` defines odd square distances `d >= 3`.
- `PhysicalLayout.rotated_surface(code)` defines local data/check keys, coordinates,
  check supports, connectivity, and the collision-free N/Z four-layer CNOT order.
  Code columns follow `layout.data_ids`.
- `LogicalBlock.placed(block_id, code, patch_index=...)` places equal-distance
  patches deterministically. Construct `LogicalBlock(block_id, code, layout, origin)`
  for explicit placement. Overlapping registered coordinates are rejected.
- `CodeBackend` and `RotatedSurfaceCodeBackend` generate ideal physical chunks.
  `OperationModule` subclasses build `ModuleFragment` objects with ordered
  `logical_ids`/`block_ids`, verified chunks/reflows/loops, logical/frame actions,
  code orientations, and noise provenance. `physical_positions` lists sites with
  actual gates; `interface_positions` includes sites declared by flow ports.
  `TransversalCNOT(control, target)` is
  one shared two-block fragment. Independent multi-target memory operations retain
  the original concurrent one-block fragments and scalar compatibility accessors.
- `CircuitCompiler(blocks, logical_to_block=...)` uses fresh `CompilerContext`
  state for each compilation. If bindings are omitted, logical IDs default to
  block IDs. IDs remain separate concepts and namespaces.
- `CompiledCircuit.physical_qubit_map[(block_id, local_id)]` gives the **final**
  Stim index recovered after stimflow assembly. `logical_to_block`, `measurements`,
  `detectors`, `observables`, `frames`, `block_status`, `time_layers`, and
  `fragments` preserve record provenance and physical-time metadata. `orientations`
  exports the final code frames; physical site identities do not change.
  Exported measurement indices are absolute zero-based raw-record indices.
  `result.circuit` selects the noisy circuit when present, otherwise the ideal one.

Logical X is the southern data row; logical Z is the western data column.
Initialization prepares the chosen **logical** +1 eigenstate. Conjugate-basis
stabilizer signs in the first SE round are random: their symbolic measurement keys
are retained in `frames[logical_id].preparation_syndromes`. No decoder-dependent correction is assumed. Memory preserves empty logical Pauli
correction terms. H code-frame changes can add symbolic sector-dependent terms;
virtual Paulis add binary affine constants. Neither requires guessed shot values.

## Noise

`NoiseModel()` preserves the exact ideal circuit. Omitting `noise_model` leaves
`noisy_circuit=None`. `NoiseParameters` specifies reset errors, one-/two-qubit
Clifford depolarization, measurement-result flips, and idle depolarization.

```python
from logical_to_stim_converter import NoiseModel, NoiseOverride, NoiseParameters

noise = NoiseModel(
    default=NoiseParameters(reset=0.001, two_qubit=0.002,
                            measurement=0.003, idle=0.0001),
    operation_overrides={"SyndromeExtraction": NoiseOverride(two_qubit=0.004)},
)
# Pass noise_model=noise to compile; an operation can also specify:
operation = SyndromeExtraction("data0", rounds=2, noise=NoiseOverride(two_qubit=0))
```

Instance override > primitive-type override > global default, channel by channel.
`None` inherits; explicit zero disables an inherited channel. Reset errors use an
anticommuting Pauli after the reset. Measurement errors flip the reported bit.
Gate noise uses upstream stimflow rules. Idle noise is computed once from the
composed schedule: all sites in a block are eligible from its initialization layer
through its destructive-measurement layer. Waiting initialized blocks use global
idle defaults; uninitialized and retired blocks receive no idle noise. These are
modeling conventions, including ancilla idle periods before the next reset.

## Scope and verification

Tests cover distances 3 and 5, one/two/three patches, both memory bases, unequal
round counts, signed flows, corrupted-gate/flow rejection, exact measurement
parities, circuit distance, final mappings, lifecycle rules, and exact noise sites.
See [STATUS.md](STATUS.md) for executed checks and platform coverage.

Current restrictions: one logical slot per block; every registered block initialized
and destructively measured once; individual final X/Z readouts must be deterministic
under the intended logical circuit. H may change the valid readout basis. An
entangled Bell state's random individual readouts are rejected instead of being
labelled deterministic observables.
Repeated rounds are represented as `ChunkLoop` in fragments, then expanded to
export explicit physical layers and per-record metadata. There is no large-round
compression or general scheduling optimizer.

Dedicated Bell/Knill operations, other code families, S/other logical Clifford
gates, a text parser/CLI, decoder adapters, relocation, and adaptive operations remain
unimplemented. `surface-sim` is a pinned geometry/schedule reference, not a runtime
dependency; Hex and lomatching are not integrated. External copies remain ignored
by Git. No license has been selected.


## H, CNOT, and an encoded Bell round trip

```python
from logical_to_stim_converter import TransversalH, TransversalCNOT

# A and B are initialized in logical Z; construct the Bell resource from primitives.
program = [
    LogicalInit(("A", "B"), basis="Z", rounds=1),
    TransversalH("A"),
    TransversalCNOT(control="A", target="B"),
    SyndromeExtraction(("A", "B"), rounds=3),
    TransversalCNOT(control="A", target="B"),
    TransversalH("A"),
    LogicalMeasure(("A", "B"), basis="Z"),
]
blocks = [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate(("A", "B"))]
result = CircuitCompiler(blocks).compile(program,
    noise_model=NoiseModel.uniform_depolarizing(0.001))
raw = result.ideal_circuit.compile_sampler(seed=7).sample(100)
assert not result.interpreted_measurements(raw).any()
```

Run `python examples/two_patch_bell_roundtrip.py`. At distance 3, three additional
SE rounds give 34 qubits, 64 detectors, two observables, and 30 physical layers.
The example independently verifies intermediate logical XX/ZZ expectations of +1
and zero individual logical X/Z expectations using an actual physical tableau.
It also reconstructs final raw logical Z parities `(0, 0)` directly from data records.

**H convention:** physical H acts once on every data qubit; no data/ancilla state
is physically permuted. Orientation toggles 0 ↔ 1. Frame 1 uses a clockwise
quarter-rotated template: logical X is the western column and logical Z the
northern row. All check bases flip at their fixed ancillas, and subsequent SE
uses the H-conjugated physical cycle (same four edge layers, reversed CX direction,
flipped reset/readout bases). H realizes logical X/Z interchange modulo checks;
the associated random-sector parity is retained in the logical Pauli frame.
Two H operations restore the original orientation and implement identity.

CNOT pairs the same canonical data coordinates through the two current frames.
Different orientations therefore require a different **physical CX pairing**.
Those gates are explicit; the simulation assumes the required inter-block links
are available. No connectivity-routing or omitted SWAP operation is claimed.
All check and logical transformations are physically conjugated and verified;
stimflow ChunkReflow restores the local check-generator basis without discarding
cross-block syndrome correlations.

## Pauli frames and interacting metadata

```python
from logical_to_stim_converter import LogicalPauli

physical_x = LogicalPauli("A", pauli="X", mode="physical")
virtual_y = LogicalPauli("A", pauli="Y", mode="frame")
```

Physical X/Y/Z executes the current representative on data and uses the configured
single-qubit Clifford noise per executed physical gate. Y combines X/Z supports
with physical Y on their intersection, up to an irrelevant global phase. Frame
mode emits no gate, TICK, idle interval, or fault location. It changes the affine
logical frame, propagated by H and CNOT. Noise-type overrides also accept
`TransversalH`, `TransversalCNOT`, and `LogicalPauli`; a shared CNOT fragment applies
one two-qubit noise rule per physical pair, once.

`PauliFrame.x`/`.z` are `ParityExpression` values (measurement-key terms plus a
binary constant). Existing `.x_terms`/`.z_terms` and preparation provenance remain.
`ObservableInfo.readout_measurement_indices` identifies the canonical final data
parity; `.frame_correction` gives its affine interpretation. Use
`result.interpreted_measurements(raw)` to obtain intended logical output bits.
`measurement_indices` describes the actual Stim observable parity, including
measurement-dependent frame terms. Stim omits affine constants; XOR its parity
with `frame_correction.constant` for the same interpreted output.
`expected_value` is the ideal intended output, which may be 1 after a Pauli.
Detector-sampler flips alone do not establish a raw logical output value.

Cross-block `DetectorInfo.supporting_block_ids` lists **all contributing record
blocks**. `anchor_block_id`/`anchor_check_id` give semantic check identity; legacy
`block_id`/`check_id` remain anchor accessors, not decoder-region assignments.
The check key names its fixed physical ancilla, whose basis may change after H.
Record indices, registered anchors, and causal interaction support are validated.

The multi-block build API is `operation.build(backend, ordered_operands,
OperationContext(module_id, orientations))`; operand order is significant for CNOT.
The original `build(backend, block, logical_id, module_id)` form remains supported
for single-block memory use. Lifecycle/frame updates are staged atomically, and
parallel operations on overlapping operands are rejected even for virtual gates.
