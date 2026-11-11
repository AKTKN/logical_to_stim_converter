# logical_to_stim_converter

Compile Python logical operations or `.lstim` source into verified physical
[Stim](https://github.com/quantumlib/Stim) circuits for supported rotated-surface-code
programs. The compiler composes signed stabilizer and logical flows with stimflow,
then exports physical circuits, measurement provenance and decoder-neutral models.

**Internal research beta · version 0.0.1.** Intended for trusted collaborators and
downstream research simulations such as `knill_bench` and `lomatching`. GitHub
installation uses a pinned commit. APIs may evolve; this is not a stable production
API or a general quantum-programming frontend.

## Capabilities and scope

- Mathematical CSS code specifications and fixed physical rotated-surface layouts.
- Signed flows, initialization, concurrent syndrome extraction and X/Z readout.
- Logical H, CNOT and physical/virtual X/Y/Z; Bell preparation and Knill teleportation.
- Explicit patch binding/reuse, including repeated Knill cycles on three patches.
- Canonical global detector/observable metadata, relocation and physical-use history.
- Operation-aware gate/result/idle noise on composed physical time layers.
- Decoder-neutral views, temporal/conditional models and offline record/Pauli frames.
- Opt-in M9 ideal Bell-owned initialization plus post-SE data depolarization.
- Parallel Knill/Bell LSTIM, transversal X/Y/Z and primitive `noise=ideal`.
- Explicit per-init data noise, signed terminal stabilizer probes and metadata export.

The verified physical/test envelope emphasizes odd distances 3 and 5. Other code
families, non-Clifford gates, automatic allocation and adaptive execution remain
unsupported. No production decoder or experiment runner ships inside the converter.
See the [implementation and limitations matrix](docs/index.md#current-implementation-and-limitations).
The separate [research validators](validation/README.md) record exact d=3/5
one-layer code-capacity counts, an ordinary-circuit physical fault census, and
complete d=3 weight-two M9 Knill fault assignments with eight-worker MWPM
sampling. The [independent golden-memory suite](validation/golden_memory/README.md)
also certifies three-round d=3/5 X/Z ideal semantics, shared reset/readout fault
responses, and exact independently authored physical/noise schedules.
The [independent Knill suite](validation/golden_knill/README.md) compares corrected
ideal three-patch semantics with pinned Hex and exact physical, ordinary-noise
and M9 schedules with a separate direct-Stim oracle.

## Installation

Use Python 3.11+ with a compatible Stim wheel, Git on PATH and network access to
GitHub and the package index. Configure Git credentials separately if needed.
Use a checkout containing this dependency-policy revision. Create an environment:

```sh
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS or
`.\.venv\Scripts\Activate.ps1` in Windows PowerShell, then install:

```sh
python -m pip install .
python -c "from importlib.metadata import version; print(version('logical-to-stim-converter'))"
```

The version command prints `0.0.1`. There is no published version tag or PyPI
release. Current runtime minimums include `stim>=1.15.0` and `lark>=1.3.1`;
stimflow's upstream Git source remains pinned at
`ffe0d043598ed5df0851a3e6b4920359a23fafbd` (`glue/stimflow`). Git/network access
is needed for that source dependency; local reference clones are not required.
Older source commits retain their original dependency declarations. For a Git
installation, select a full commit containing this change. See the
[dependency compatibility record](docs/dependency_compatibility.md) for tested versions.
Full prerequisites, dependency details and offline constraints are in
[installation and development](docs/development.md).

## Quick start

This standalone program uses only installed runtime dependencies:

```python
from logical_to_stim_converter import NoiseModel, parse_logical_circuit

source = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z(3) D
SE(2) D
MZ D
"""
compiled = parse_logical_circuit(source).compile(
    noise_model=NoiseModel.uniform_depolarizing(0.001),
)
compiled.validate_metadata()
dem = compiled.circuit.detector_error_model()
raw = compiled.circuit.compile_sampler(seed=11).sample(shots=4)
assert raw.shape == (4, 49)
print(compiled.circuit.num_qubits, dem.num_detectors, dem.num_observables)
```

It prints `17 40 1`. `compiled.circuit` selects the noisy circuit when requested;
`compiled.ideal_circuit` retains the verified ideal circuit. `raw` contains global
physical measurements, not decoded logical bits. Sampling and correction selection
belong to the caller. The [API reference](docs/api_reference.md) specifies array
orders, reference-relative labels and source-bound offline correction contracts.

For four-qubit deep Clifford circuits with parallel Knill and three patches per
logical qubit, run `python examples/deep_clifford.py --shots 16`. Add
`--noisy-resource` for ordinary d-round preparation, or `--output outputs/deep`
for LSTIM/Stim/metadata export. The example verifies noiseless frame-corrected
stabilizers and samples noisy circuits; noisy decoding remains external. See the
[public API additions](docs/api_reference.md#parallel-knill-and-deep-clifford-additions-2026-11-11).

## Documentation

- [Documentation index and current scope](docs/index.md)
- [Installation, development and dependency pins](docs/development.md)
- [Public consumer API reference and glossary](docs/api_reference.md)
- [Parallel Knill / deep Clifford implementation and verification](docs/parallel_knill_deep_clifford.md)
- Installed workflows: [ordinary memory](docs/ordinary_memory_tutorial.md) and
  [three-patch Knill with M9](docs/knill_memory_tutorial.md)
- [LSTIM guide](docs/lstim.md), [v1 specification](docs/lstim_v1.md) and
  [certification matrix](docs/lstim_certification.md)
- [Ordinary memory and Clifford/Knill examples](docs/examples.md) and
  [explicit three-patch Knill guide](docs/three_patch_knill.md)
- [Physical identity, timing, noise and decoder contracts](docs/architecture.md)
- [M9 resource-preparation noise and conditional boundaries](docs/resource_preparation_noise.md)
- [Physical Stim circuit inspection guide (Japanese)](examples/stim_circuit_guide_ja.md)
- [Deferred work](docs/deferred_work.md) and [verification ledger](STATUS.md)

## Development

From a checkout, install `python -m pip install -e ".[dev]"`, then run
`python -m pytest -n 8`, `python -m ruff check src tests examples` and
`python -m build`. The dev extra supplies pytest-xdist and optional example
PyMatching/plotting dependencies. They are not required for the quick start.
See [development instructions](docs/development.md) for CI and physics checks.

License decision pending.
