# logical_to_stim_converter

**Status (2026-11-07): verified rotated-surface memory-circuit foundation.**

Compile Python logical-operation objects into physical Stim circuits for independent
square rotated surface-code patches. The memory path implements code algebra,
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
  `OperationModule` subclasses `LogicalInit`, `SyndromeExtraction`, and
  `LogicalMeasure` build `ModuleFragment` objects containing verified stimflow
  chunks/loops and logical/lifecycle metadata.
- `CircuitCompiler(blocks, logical_to_block=...)` uses fresh `CompilerContext`
  state for each compilation. If bindings are omitted, logical IDs default to
  block IDs. IDs remain separate concepts and namespaces.
- `CompiledCircuit.physical_qubit_map[(block_id, local_id)]` gives the **final**
  Stim index recovered after stimflow assembly. `logical_to_block`, `measurements`,
  `detectors`, `observables`, `frames`, `block_status`, `time_layers`, and
  `fragments` preserve record provenance and physical-time metadata.
  Exported measurement indices are absolute zero-based raw-record indices.
  `result.circuit` selects the noisy circuit when present, otherwise the ideal one.

Logical X is the southern data row; logical Z is the western data column.
Initialization prepares the chosen **logical** +1 eigenstate. Conjugate-basis
stabilizer signs in the first SE round are random: their symbolic measurement keys
are retained in `frames[logical_id].preparation_syndromes`. No physical correction
or decoder-dependent canonical stabilizer-sector correction is assumed. Memory
preserves empty logical Pauli correction terms.

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

Current restrictions: one logical slot per block; matching preparation/readout
basis; every registered block initialized and destructively measured once.
Repeated rounds are represented as `ChunkLoop` in fragments, then expanded to
export explicit physical layers and per-record metadata. There is no large-round
compression or general scheduling optimizer.

Transversal H/CNOT, logical Paulis, Bell/Knill operations, other code families,
a text parser/CLI, decoder adapters, and general Clifford/frame propagation remain
unimplemented. `surface-sim` is a pinned geometry/schedule reference, not a runtime
dependency; Hex and lomatching are not integrated. External copies remain ignored
by Git. No license has been selected.
