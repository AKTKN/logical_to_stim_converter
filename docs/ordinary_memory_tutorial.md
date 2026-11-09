# Installed ordinary-memory consumer

This workflow uses the installed **0.0.1** package and runtime dependencies only.
It samples one physical batch, retains the full canonical DEM and exact selected
view, and evaluates a caller-owned **zero-observable-flip prediction**. It is a
wiring/label example, not an effective noisy decoder or a threshold experiment.
No PyMatching, plotting, source checkout imports or extra decoder package is needed.

## Prepare an external directory

Install the runtime as described in [development](development.md#install-the-001-internal-research-beta),
using the reachable runtime baseline (the Phase 4 consumer changes no runtime):

```sh
python -m venv .venv
```

Activate it using `source .venv/bin/activate` (Linux/macOS), or
`.\.venv\Scripts\Activate.ps1` (Windows PowerShell), then:

```sh
python -m pip install "logical-to-stim-converter @ git+https://github.com/AKTKN/logical_to_stim_converter.git@8a409593ab09441c189ec3fe8742ab3f64055cce"
```

Use a new directory outside the repository as the working directory. Save the
linked [standalone consumer script](../examples/installed_consumer.py) from the
same documentation revision as this page as **`installed_consumer.py`** there.
The script is self-contained; do not import it as `examples.installed_consumer`.
Its public imports resolve to the installed converter; its small adapter belongs
to this external consumer, not the converter runtime. Retain the documentation
commit SHA with your copied script for reproducibility.

Save this complete input as **`memory_d3.lstim`** in that same external directory:

```text
FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z(3) D
REPEAT 2 {
    SE(1) D
}
MZ D
```

This is exactly the [checked-in input](../examples/lstim/memory_d3.lstim). Neither
this input nor the consumer script is installed by the wheel: you supply both.
They also ship in the source distribution. Subsequent commands need only your
copies and the installed environment, with no repository on `PYTHONPATH`.

## Execute ideal and noisy cases

From that external directory, with the environment active:

```sh
python -I installed_consumer.py memory memory_d3.lstim --p 0 --shots 32 --seed 41
python -I installed_consumer.py memory memory_d3.lstim --p .001 --shots 32 --seed 41
```

Each command compiles independently and samples exactly once. Within a case,
views, labels and alternative hypotheses all use that one batch. The observed
Linux/Python 3.12.7 smoke gave:

| p | Raw bool shape | Global events shape | Intended-bit shape | Zero-prediction failures / shots |
| --- | --- | --- | --- | --- |
| 0 | [32,49] | [32,40] | [32,1] | 0/32 |
| .001 | [32,49] | [32,40] | [32,1] | 3/32 |

Counts depend on the specified RNG/environment and tiny batch; they are not a
numeric LER accuracy claim. Both cases have 17 physical wires and one physical
use. Noisy canonical DEM extraction and metadata validation are native public APIs.

## What the script does

`parse_logical_file(...).compile(noise_model=...)` returns the standard artifact;
`validate_metadata()` checks provenance. `compiled.circuit.detector_error_model()`
retains every canonical detector/physical fault. `compiled.make_decoder_view()`
creates a full view; a second view deliberately uses detector IDs
`(39,37,...,1)`, observable `(0,)` and raw records `(48,47,46,45)` to demonstrate
selection and permutation. `IndexMap.local_to_global` and `global_to_local` state
the exact ordering; local arrays have shapes [32,20], [32,1] and [32,4].
The local circuit still contains all 49 physical measurements and noise channels.
Record projection does not limit the full raw columns needed for event parity.

The single canonical raw batch has columns in `compiled.measurements` order.
Full `inputs_from_raw` derives detector events and observable flips relative to
the view's noiseless reference sample; tests independently compare Stim's m2d
converter. The local arrays project/reconstruct the same physical results.
Canonical and selected DEMs remain exact physical models, with hyperedges and
correlated `^` components retained. The zero predictor ignores those models;
it does not silently convert them to graphlike matching or discard faults.

An application can import the copied file locally (without `-I`, which excludes
script-directory imports) to replace its prediction step:

```python
import numpy as np
from installed_consumer import analyze_memory
from logical_to_stim_converter import NoiseModel, parse_logical_file

compiled = parse_logical_file("memory_d3.lstim").compile(
    noise_model=NoiseModel.uniform_depolarizing(.001),
)
raw = compiled.circuit.compile_sampler(seed=41).sample(shots=32)
raw.flags.writeable = False

def my_predictor(view, current_events):
    # Replace with your inference using view.detector_error_model and maps.
    # This explicit baseline predicts no reference-relative observable flips.
    return np.zeros((len(current_events), len(view.observables)), dtype=bool)

first = analyze_memory(compiled, raw, predictor=my_predictor)
second = analyze_memory(compiled, raw)  # Replay the SAME batch; no sampling inside.
assert np.array_equal(first["failures"], second["failures"])
print(int(first["failures"].any(axis=1).sum()))
```

The predictor receives selected current detector events, never actual observable
labels or hidden fault data. It returns bool [shots, selected observables] in the
view's observable order. Array shape/dtype and source/index mistakes fail explicitly.
The installed-wheel test also checks a signed two-observable memory with reversed
observable order; do not infer global IDs from physical patch order.

## Failure labels and decoder responsibility

For ordinary memory, `actual_flips = view.observable_flips_from_raw(raw)` is
reference-relative truth. A prediction `predicted_flips` gives
`failures = predicted_flips XOR actual_flips`. Independently, the code computes
absolute intended bits using `compiled.interpreted_measurements(raw)`, applies the
external prediction and XORs `ObservableInfo.expected_value`; the results agree.
A physical/virtual Pauli can make the intended bit 1 while noiseless flips remain
zero. Raw final data parity alone can miss affine frame terms/constants.

For multiple observables, count `failures.any(axis=1).sum()` for any-observable
shot failures, or `failures.sum(axis=0)` per observable; divide each by shots.
These are empirical rates under the stated external predictor and label convention.
This example applies no physical correction or adaptive gate. A consumer choosing
record/frame hypotheses must edit copies and recompute events after each edit;
see the [Knill tutorial](knill_memory_tutorial.md) and
[API record/frame contracts](api_reference.md#offline-frame-plans-and-corrections).
Optional [PyMatching source examples](examples.md#ordinary-memory) remain separate
from the installed runtime and must reject unsupported matching projections.
