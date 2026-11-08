# logical_to_stim_converter

**Status (2026-11-08): verified memory, Clifford/Knill circuits, global provenance,
offline decoder views, ordinary/Knill decoding demos, and LSTIM semantic compilation.**

Compile Python logical-operation objects into physical Stim circuits for independent
square rotated surface-code patches, including interacting logical Clifford circuits.
The memory path implements code algebra,
physical layouts, signed stabilizer/logical flows, concurrent syndrome extraction,
destructive readout, decoder-independent metadata, and circuit-level noise.

The package is independent of `knill_bench`. Sampling and decoder/experiment comparison belong to the caller. A development
example demonstrates ordinary-memory logical error rates with PyMatching; the
converter has no production decoder or experiment runner.

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
python -m ruff check src tests examples
python -m build
```

The package pins **Stim 1.15.0** and installs **stimflow 1.17.dev0** directly from
Stim commit `ffe0d043598ed5df0851a3e6b4920359a23fafbd`, subdirectory
`glue/stimflow`. Installation needs network access to GitHub; no local
`external_lib/` copies are required. See [development notes](docs/development.md).

## LSTIM semantic frontend (M8-B)

The language namespace validates `.lstim` text and lowers it to existing Python
operations. Compilation uses the same verified physical compiler:

```python
from logical_to_stim_converter import NoiseModel
from logical_to_stim_converter.language import parse_logical_circuit

source = """FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z(3) D
REPEAT 2 {
    SE(1) D
}
MZ D
"""
program = parse_logical_circuit(source, source_name="memory.lstim")
assert program.blocks[0].block_id == "P0"
operations = program.to_operations()  # Immutable, including the explicit BindPatch.
compiled = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.001))
assert compiled.circuit.num_detectors > 0
```

`parse_ast` remains available for syntax-only inspection. LogicalProgram retains
that AST, the source text, fixed blocks, ordered operations and source spans.
Static checks validate declarations, signatures/options, previously bound names
and repeats before materializing at most 100,000 operations/directives by default
(configurable with `max_operations`). Repeats preserve each operation/barrier;
parallel groups stay tuples. The existing compiler validates physical lifecycle,
geometry and flows and owns all noise/timing. Each compilation starts with an
empty initial mapping and executes every source BIND in order.

Semantic errors carry file/line/column/excerpt/caret. Compiler validation failures
raise `language.errors.LSTIMCompileError` with the original exception as cause;
they report the file without guessing a statement location. Explicit labels map
through `program.label_spans` and existing fragment/composite operation IDs.
The package-root/file API and formatter remain M8-C, and full noisy E2E
certification remains M8-D. See the [v1 language contract](docs/lstim_v1.md).
Lark 1.3.1 and the packaged grammar are unchanged.

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

## Explicit reuse of one physical patch (M7-A)

`BindPatch` reserves an explicitly selected available patch for a fresh logical
name. It adds no gates, reset, measurements, noise or physical time. The following
`LogicalInit` performs the actual reset and starts the next occupancy generation:

```python
from logical_to_stim_converter import (
    BindPatch, BlockUseId, CircuitCompiler, CodeSpec, LogicalBlock,
    LogicalInit, LogicalMeasure,
)

patch = LogicalBlock.placed("P0", CodeSpec.rotated_surface(3))
result = CircuitCompiler([patch], logical_to_block={"first": "P0"}).compile([
    LogicalInit("first", "Z", rounds=3),
    LogicalMeasure("first", "Z"),
    BindPatch("second", "P0"),
    LogicalInit("second", "X", rounds=3),
    LogicalMeasure("second", "X"),
])
assert result.circuit.num_qubits == 17
assert result.circuit.num_observables == 2
assert [u.use_id for u in result.block_uses] == [BlockUseId("P0", 0), BlockUseId("P0", 1)]
```

Physical qubits, layout and `GlobalSiteId` stay fixed. `MeasurementKey.epoch`
distinguishes repeated check and destructive-readout records; check round indices
restart at zero. Global raw-record indices keep increasing. `block_uses` retains
immutable reset/readout module IDs, half-open record/layer intervals and owner
history. `binding_history`, `preparations`, `readouts`, observables and relocation
records remain addressable after retirement. Observable IDs follow sorted logical
names across the complete program, including historical readouts.

An active state or pending reservation prevents rebinding. Retired logical names
cannot execute again; use fresh resource names. `available_blocks` reports patches
eligible for an explicit bind. A measured patch keeps `MEASURED` status until a
binding reserves it as `UNINITIALIZED`; binding itself never advances the epoch.
An explicit partial initial mapping (including `{}`) leaves other patches
unreserved. Closed compilation still requires every registered patch to finish
measured; use `allow_open_outputs=True` for pending reservations and active outputs.

Knill relocation preserves the data logical identity on the output patch use,
retires both temporary resource handles and releases the two measured patches.
Later bindings/composites resolve against that updated mapping. Automatic patch
allocation is outside the package. M7-B adds use-specific offline models below;
the full three-patch repeated-Knill decoding/LER demonstration remains M7-C work.

## Select and interpret one physical occupancy (M7-B)

Physical-block selection includes every epoch at that site. Select a particular
reset-to-readout use explicitly, independently of block/stage filters:

```python
from logical_to_stim_converter import BlockUseId, DetectorSelector, observable_local_views

use = BlockUseId("P0", 1)
view = result.make_decoder_view(
    detector_selector=DetectorSelector(use_ids=(use,), use_membership="strict"),
    observable_selector=("second",),
    measurement_selector=lambda m: m.key.block_use_id == use,
)
assert view.audit.region_use_ids == (use,)
local_views = observable_local_views(result)
```

`use_membership="anchor"` selects the anchored check's use; `"touching"` selects
any contributing use; `"strict"` requires every source use in the selected set.
Pass several BlockUseIds to form a joint region. The filters intersect with
existing block, stage and basis filters. Observable and measurement selections
remain independent; detector selection never implicitly removes physical records
or faults. Audit metadata distinguishes requested uses from actual source uses.

`DetectorInfo.anchor_use_id` and `source_use_ids` distinguish detector history
without changing `(x,y,t)` coordinates or `physical_support` site IDs.
`TimeLayer.active_use_ids` audits reset-through-readout idle eligibility; pending
reservations and measured gaps have no idle exposure. Historical
`use_preparation_dependencies[use]` retains that use's latest causal ancestry;
`ancestry_events` additionally records use-specific input/output edges at each
boundary. New resets start independent ancestry, while a previously teleported
state retains its real earlier sources on another use.

Default observable-local regions use actual CNOT/relocation/check-flow connections
between BlockUseIds. Reusing coordinates alone does not connect independent
memories. A caller may still supply `region_selector(observable_info)` explicitly.
Every view keeps the full physical gates, resets, measurements and exact noise;
Stim re-extracts its DEM with correlations/hyperedges intact.

```python
import numpy as np
from logical_to_stim_converter.decoding import CorrectionBatch, make_stage_requests

requests = make_stage_requests(result)
request = next(r for r in requests.boundaries
               if r.block_use_id == use and r.preparation is not None)
assert request.source_preparation.block_use_id == use
plan = result.make_frame_plan()
raw = result.circuit.compile_sampler(seed=71).sample(8)
state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
boundary = plan.boundary_by_id[request.module_id]
# Identity hypothesis illustrates the declared X(data), then Z(data) ordering.
bits = np.zeros((len(raw), len(boundary.input_ids)), dtype=bool)
state.apply(CorrectionBatch(plan.source_fingerprint, boundary.boundary_id, bits,
                            block_use_id=use, input_ids=boundary.input_ids))
current_events = state.events(view)
```

Boundary/readout requests identify their actual use and `source_preparation`.
`preparation` remains the optional prepared-logical target on initialization
requests; ordinary SE has no such target. `StageRequests.order` is causal offline
module order. Boundary MPP probes occur only in temporal models, never canonical
samples or decoder inputs. Conditional Bell models expose `data_use_id`,
`first_resource_use_id`, `output_use_id`, `output_preparation_module_id` and the
actual `resource_entangling_module_id`; each model retains its own fault window,
exclusive noise alternatives and physical survivor actions, including existing
Bell resources prepared before KnillEC.

Frame boundaries are unique module IDs even when sites are reused. Optional
CorrectionBatch use/column labels reject stale epochs and swapped X/Z ordering;
the original three-argument API keeps the plan's declared order. Each boundary
can be applied once. Actual reset removes old physical X/Z support; earlier Bell
records can still affect the surviving logical state's later interpretation.
Raw batches stay immutable, and `events(view)` always uses current records.

`DecoderView.schema_version` is now **`decoder-view-v3`**. Regenerate v1/v2
fingerprints, cached views and frame plans: v3 includes exact use, ownership,
ancestry and timing metadata. Lossless instruction snapshots and exact double
probabilities remain unchanged. This API supplies no decoder or adaptive gates.

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

Current restrictions: one live logical slot per block; patch reuse requires an
explicit BindPatch and a fresh logical name before initialization.
Readouts default to deterministic X/Z under the intended logical circuit. Use
`LogicalMeasure(..., mode="random")` for a random classical outcome without a
deterministic observable. Use `compile(..., allow_open_outputs=True)` to retain
active outputs or unused registered blocks. The default closed-memory check is
preserved for compatibility. H may change the valid readout basis.
Repeated rounds are represented as `ChunkLoop` in fragments, then expanded to
export explicit physical layers and per-record metadata. There is no large-round
compression or general scheduling optimizer.

Other code families, S/other logical Clifford gates, LSTIM package-root/file APIs
and formatting, a CLI, production decoder adapters, and adaptive operations remain
unimplemented. Explicit physical block reuse is supported through BindPatch.
`surface-sim` is a pinned geometry/schedule reference, not a runtime
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

## Bell resources and Knill EC

```python
from logical_to_stim_converter import BellStatePrep, KnillEC

blocks = [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate("DAB")]
compiler = CircuitCompiler(blocks)
opened = compiler.compile([
    LogicalInit("D", "X", rounds=1),
    KnillEC(data="D", first_resource="A", output_resource="B"),
], allow_open_outputs=True)
assert opened.open_logical_outputs == {"D": "B"}
assert opened.logical_to_block == {"D": "B"}

# Address the persistent logical identity D after its relocation to physical B.
closed = opened.append([SyndromeExtraction("D", rounds=2), LogicalMeasure("D", "X")])
closed.ideal_circuit.detector_error_model()
```

`BellStatePrep("A", "B", rounds=None)` prepares A in X and B in Z concurrently,
with exactly `code.d` complete SE rounds each by default, then applies CNOT A→B.
`KnillEC` builds that resource, applies CNOT D→A, destructively measures X(D)
and Z(A), and transfers the identity D to B. A and the old D block retire;
the A/B resource identities leave the location mapping. `relocation_history`
preserves that transition. To consume an existing verified Bell resource, pass
`prepare_resource=False`. `rounds` overrides the resource preparation duration.

Composites expand into the same primitive operations used by ordinary programs.
Fragments retain primitive noise selection, child operation IDs, composite IDs,
and stage provenance. No parent injects a second noise rule. Independent composites
and spectator work can run in parallel. Open artifacts preserve their verified
`open_interface`; export adds no MPP or terminal data readout. `append` recompiles
the complete prefix and continuation with flow verification.

`preparations` exports each check's complete record history, final syndrome,
gauge keys, physical data ordering, and an unresolved `PhysicalPauliFrame`.
`readouts` and `bell_measurements` export raw data keys, local check matrices,
logical parities, frame dependencies, and symbolic byproducts. Bell outcomes are
random classical values, with no deterministic observable assigned to them.
`bell_measurements[i].physical_output_frame` remains unresolved until corrections
are supplied. The symbolic affine `logical_output_frame` and final `frames`
also remain available for auditing the ideal transport relations.

Physical preparation corrections require external selection. A frame uses X/Z
supports in stable physical data IDs and carries its preparation boundary and
source syndrome keys. Supply one resolved frame per shot and preparation module:

```python
# corrections[module_id] is a sequence of prep.resolve(x_vector, z_vector).
# The vectors are externally selected; the runtime package contains no decoder.
evaluation = closed.evaluate_frames(raw_samples, corrections)
logical_bits = evaluation.logical_outputs
bell_values = evaluation.bell_measurements
```

The default `validation="noiseless"` checks final raw syndrome equations and the
prepared logical eigenvalue, preserving the M5 test contract. The explicit
`validate_noiseless_preparation_corrections(raw_samples, corrections)` method
performs this proof without replay. For externally inferred noisy corrections, use
`evaluate_frames(raw_samples, corrections, validation="hypothesis")`: it checks
identity, orientation, physical support, source boundary, and logical commutation
metadata, without requiring a hypothesis to reproduce potentially faulty final
checks or preserve the prepared logical eigenvalue. Acceptance does not establish
decoder correctness. Both modes propagate physical vectors through actual H/CX
pairings, interpret each measurement once, then insert the Bell byproduct into the
output frame. `interpreted_measurements` accepts the same validation option.
It returns corrected records, Bell values, logical outputs, and residual open
physical frames. `interpreted_measurements` on a Knill result requires
`preparation_corrections=corrections`; it never assumes unresolved vectors vanish.
The primary physical circuit contains no adaptive correction gates.

### M6-A canonical circuit and metadata migration

`ideal_circuit`, `noisy_circuit`, `circuit`, and `detectors` now refer to the
**complete physical detector circuit**, including valid cross-stage relations.
Quantum gates, noise locations, raw record order, qubit indices, and observable
semantics are preserved. Individual random Bell bits remain raw records.
For the d=3 Knill example the open circuit has **52 detectors** (M5: 44);
after two SE rounds, H and readout it has **72** (M5: 56).

- `measurements[i]` describes global raw record `i`, including its `MeasurementKey`,
  block/local site, round, logical identity, basis, module, layer and stage.
  `measurement_index_by_key` provides the immutable reverse mapping.
- `detectors[i]` describes global detector `i`: exact raw parity indices/keys,
  physical coordinates `(x, y, t)`, check/block anchor, `anchor_module_id`, and
  `supporting_block_ids`. `stage_id` is the primary anchor stage;
  `source_stage_ids` is the stable ordered set of **all** source stages (including
  `None` for ordinary un-staged records). `crosses_decoder_boundary` marks a
  proposed stage boundary, without removing the physical detector.
- `observables[i]` retains global observable ID and full parity, canonical data
  readout support, affine frame and intended value. `readouts` includes random
  readouts with no deterministic observable ID.
- `detector_boundary_candidates` identifies present global detectors crossing a
  proposed boundary, with `global_index`, raw parity and `source_stage_ids`.
  The M5 name `suppressed_detectors` remains a read-only compatibility alias;
  its entries are no longer absent from the canonical circuit.
- `stage_separated_circuit(noisy=False)` explicitly derives the old annotation
  view. Set `noisy=True` for the identical physical noisy circuit with the same
  detector selection. `stage_separated_detector_indices[local_id]` maps view IDs
  back to canonical global IDs. These views do not create independent stage DEMs.
- `preparation_dependencies[logical_id]` identifies the causal preparation modules
  for each initialized, currently bound logical identity. `block_preparation_dependencies`
  retains physical-block history, including retired blocks; `ancestry_events`
  records typed primitive/relocation edges. CNOT unions its actual operand
  histories; relocation transfers the relevant input/resource histories to the
  survivor. Independent spectators and parallel gadgets stay separate. Physical
  output-frame source syndromes agree with those histories, independently of
  per-shot correction values.
- `validate_metadata()` checks canonical record/annotation indices, stages,
  coordinates, and ancestry edges against physical fragments and relocations.

These metadata types are public package exports. Global detector IDs and raw
record indices remain unchanged when deriving a view. M6-B provides the general
offline selections and exact marginal DEM construction described below.

Run `python examples/knill_ec_single_round.py` for decoder-independent ideal/noisy
circuit generation and metadata. The required tests use **PyMatching 2.3.1** only
from `tests/helpers/preparation_matching.py`, installed by `.[dev]`. They resolve
noiseless final preparation sectors and independently verify state recovery and
reference entanglement on physical Stim tableaux. This helper does not infer
circuit-level faults or establish noisy logical error rates. Future decoder and
DEM work is tracked in [deferred work](docs/deferred_work.md).

## Offline decoder views (M6-B)

A view selects decoder inputs from the same physical experiment. It samples
nothing and leaves `compiled.circuit` unchanged. For an external consumer:

```python
from logical_to_stim_converter import DetectorSelector, observable_local_views

full = compiled.make_decoder_view()
patch = compiled.make_decoder_view(
    detector_selector=DetectorSelector(
        block_ids=(compiled.observables[1].block_id,), block_membership="strict"),
    observable_selector=(1,),  # global observable 1 becomes local observable 0
)
raw = compiled.circuit.compile_sampler(seed=7).sample(1000)  # sample once
full_inputs = full.inputs_from_raw(raw)
patch_inputs = patch.inputs_from_raw(
    raw, source_fingerprint=full_inputs.source_fingerprint)
assert (patch_inputs.detection_events ==
        patch.project_detection_events(full_inputs.detection_events)).all()
local_dem = patch.detector_error_model
per_observable = observable_local_views(compiled)
```

Use your artifact's actual block and observable IDs. The runnable
`python examples/offline_dem_views.py` constructs a complete two-patch example.
No decoder or experiment runner is required.

`DecoderView`, `DetectorSelector`, `DEMOptions`, `GF2Map`, `RecordFlipMap`,
`apply_record_flips`, `make_decoder_view` and `observable_local_views` are package
exports. Additional mapping/input/audit/error types and `source_fingerprint` are
public in `logical_to_stim_converter.decoding`.

- `detector_map`, `observable_map`, and `measurement_map` expose `global_ids`
  (also `local_to_global`), `global_to_local`, `local_ids`, and `global_size`.
  An explicit ID sequence sets the exact local order, including permutations;
  callbacks and semantic selectors retain canonical order. Selected metadata
  objects keep their global `index`. `measurements` retains selected semantic keys.
- `detector_selector` accepts global IDs, a `DetectorSelector`, or a callback on
  public `DetectorInfo`. Select blocks by `anchor` (default), `touching` (any
  contributing block), or `strict` (all contributing blocks are in the set).
  Select `stage_ids` by `touching` (default), `anchor`, or `strict`, and optionally
  restrict `basis="X"`/`"Z"`. Fields combine by AND; IDs within a block/stage tuple
  form a union. `selector_a | selector_b` forms an arbitrary region union.
  `DetectorInfo.basis` is the physical anchor check basis, including H; its
  `physical_support` contains stable `(block_id, data_id)` sites underlying all
  contributing records. Check ID prefixes are not used to guess the basis.
- `observable_selector` accepts reliable global observable IDs, logical names,
  or a callback on `ObservableInfo`. Random Bell readout module IDs have no
  reliable observable and raise `UndefinedObservableError`. Default selection is
  all reliable observables. `measurement_selector` accepts global raw indices,
  `MeasurementKey` values or a callback; its default is all raw records.
- `cross_region_policy="retain"` keeps selected cross-region detectors;
  `"omit"` drops any selected detector spanning multiple blocks or source stages;
  `"joint"` keeps them and records the combined region. The immutable `audit`
  records requested, omitted and crossing IDs plus the actual region blocks/stages.
  Membership alone never implies independent fault models.
- `observable_local_views` constructs one view per reliable observable. Default
  regions use physical interaction components seeded by the observable's output
  and parity support, including CNOTs and relocations. They include real cross-block
  correlations even after a later inverse gate. Override with
  `region_selector=lambda observable: your_detector_selector`. This is a reusable
  observable-local selection example, not the lomatching algorithm or an optimizer.

Each local circuit retains the full physical gate/noise/measurement sequence,
`TICK`s, qubit coordinates and `SHIFT_COORDS`. Selected detectors are placed at the
end with rewritten absolute-record references and preserved coordinates, allowing
arbitrary local order. Repeat occurrences are expanded for selection. Selected
observable annotations retain their positions with contiguous local IDs. Stim
re-extracts the DEM, so an error touching a removed detector keeps all remaining
selected effects. No DEM line filtering or manual `^` rewriting occurs.

`DEMOptions()` preserves hyperedges and correlated errors. Explicit
`DEMOptions(decompose_errors=True)` requests Stim's correlated decomposition;
`flatten_loops=True` requests a flattened output DEM. Unsupported decompositions
or noise requiring disjoint-error approximation raise `DEMConstructionError`.
Gauge elimination, silent MWPM approximation and direct global-DEM rewriting are
unsupported. Public circuit/DEM properties return independent copies. Exact
instruction snapshots preserve full floating-point arguments, tags and repeats
on Linux and Windows; `schema_version` is now `decoder-view-v3`. Fingerprints
include full argument precision and use histories; regenerate v1/v2 fingerprints.

`project_detection_events`, `project_observable_flips`, and
`project_raw_measurements` slice already sampled global batches. `events_from_raw`
and `observable_flips_from_raw` recompute parities with Stim's noiseless reference
alignment; these are observable *flips*, separate from interpreted logical values.
An optional `reference_sample` must reproduce the selected noiseless parity signs.
All sample methods require unpacked binary matrices with global shot widths and
return fresh arrays; `inputs_from_raw` returns a `DecoderInputs` batch with read-only
arrays. Selecting fewer records does not restrict the full raw records required
for event reconstruction.

Software record frames can be applied without changing the sample:

```python
from logical_to_stim_converter import apply_record_flips

interpreted = apply_record_flips(raw, caller_supplied_record_masks)
updated_events = patch.events_from_raw(interpreted)
# Equivalently, update the original events through the stored GF(2) incidence map:
updated_events = patch.update_detection_events(
    full_inputs.detection_events, caller_supplied_record_masks)
```

`GF2Map(input_size, supports)` provides a sparse batched map; each output support
lists its contributing input indices. `incidence_matrix` returns a copy with
shape `(input_bits, output_bits)`. `view.record_flip_map(input_ids, matrix)` binds
an external binary `(correction_bits, global_records)` map to the physical source;
`map.apply(raw, correction_bits, source_fingerprint=view.source_fingerprint)`
returns interpreted records. The caller supplies the physical interpretation of
these correction bits. CompiledCircuit.make_frame_plan now generates physical correction maps from the
verified assembly, as described under M6-D below. A RecordFlipMap still accepts
caller-supplied maps; its operations choose no correction.

`schema_version` and `source_fingerprint` identify immutable model/metadata
snapshots, covering ideal/noisy circuits and semantic metadata. Use
`view.assert_source(compiled)` or pass the recorded fingerprint to projection
methods when exchanging batches. Bare NumPy arrays carry no source identity;
matching widths alone cannot detect a batch from a different experiment.


## Ordinary memory decoding demonstration (M6-C)

With `.[dev]` installed (PyMatching 2.3.1 and Matplotlib), run:

```bash
python examples/memory_offline_decoding.py --distance 5 --rounds 5 --basis X --p 0.003 --shots 20000 --seed 7
python examples/memory_offline_decoding.py --two-patch --shots 1000 --seed 8
python examples/memory_offline_decoding.py --suite --shots 20000 --p 0.003 --seed 20261108 --output-dir implementation_files/e2etest
```

`R` counts **all** syndrome rounds: one in `LogicalInit` and `R-1` in
`SyndromeExtraction`. Distance and round count are independent. The fixed suite
runs X/Z memory at d=3/5, R=d, and concurrent independent X/Z patches at d=3.
It writes aggregate JSON/CSV and PNG/SVG figures when an output directory is
specified. Each experiment samples exactly once; all decoding strategies reuse
that raw batch. The figures show 95% Wilson intervals, with no threshold claim.
Full-suite verification results and figures from this task are in
[`implementation_files/e2etest`](implementation_files/e2etest).

The importable source example exposes `run_memory`, `build_memory` and
`analyze_memory`. `run_memory(noise_model=your_noise, shots=..., seed=...)` accepts
an explicit `NoiseModel` instead of `p`; custom models report `p=None` and their
actual rules. Its result retains the compiled ideal/noisy circuits and metadata,
canonical undecomposed global DEM, immutable raw records, events, true flips,
predictions, failure masks and sampling/decoding times. `analyze_memory` accepts
an already sampled batch and does no sampling. These functions belong to the
example, not the installed converter's API.

A separate consumer needs only public package APIs. For example, after compiling
the two-patch `program` above with your `compiler`:

```python
from logical_to_stim_converter import DEMOptions, observable_local_views

compiled = result  # CircuitCompiler.compile(...) from the two-patch example
raw = compiled.noisy_circuit.compile_sampler(seed=7).sample(shots=1000)
events, actual_flips = compiled.noisy_circuit.compile_m2d_converter().convert(
    measurements=raw, separate_observables=True)
canonical_dem = compiled.noisy_circuit.detector_error_model()
options = DEMOptions(decompose_errors=True)
full = compiled.make_decoder_view(dem_options=options)
local = observable_local_views(compiled, dem_options=options)[1]
full_events = full.project_detection_events(events)
local_events = local.project_detection_events(
    events, source_fingerprint=full.source_fingerprint)
full_dem = full.detector_error_model
local_dem = local.detector_error_model
local_truth = local.project_observable_flips(actual_flips)
assert local.observable_map.global_ids == (1,)  # local output column 0
assert (local.events_from_raw(raw) == local_events).all()
```

Supply each DEM and its event matrix to an external decoder; its prediction
columns must follow that view's `observable_map`. The runnable demo validates
models with `make_matching` before calling `decode_batch`. For predictions in
local order, `failures = predicted_flips ^ local_truth`, and
`logical_errors = failures.any(axis=1).sum()`. Divide by the number of shots for
LER. For a multi-observable view this counts shots with **any** wrong output;
per-observable rates use the corresponding failure column. The mixed-patch
figure compares the same observable scope across strategies. Logical names
intentionally sort differently from physical patch IDs to exercise remapping.

Observable flip labels are reference-relative errors, not raw logical outcomes.
Independently, the final raw readout parity XOR the full declared affine frame
correction gives the interpreted logical bit; XOR `ObservableInfo.expected_value`
to obtain the Stim flip label. A noiseless deterministic -1 input therefore has
bit 1 and flip label 0. Tests cover both signs and physical/virtual logical Paulis,
random preparation gauges, raw detector reconstruction, and known injected faults.

Only derived decoder views request Stim graphlike decomposition. The canonical
DEM remains unchanged, including hyperedges and correlated `^` mechanisms. The
adapter rejects any component with more than two detectors before PyMatching can
silently ignore it, and reports Stim decomposition failures explicitly.
PyMatching's two-pass correlated MWPM (`enable_correlations=True` for construction
and decoding) is a heuristic approximation to maximum-likelihood decoding; `^`
components are parts of one correlated mechanism. No fault is deleted to make a
model graphlike. Uniform circuit-level depolarizing memory noise is tested.

Fixed seeds reproduce results for the same circuit, Stim version, machine and
sampling call structure; Stim does not promise identical samples across versions,
SIMD architectures or different batch sizes. Offline decoding of the stored batch
is tested to agree when split into consecutive chunks. Raw records are retained
in canonical order. The restricted Knill baseline and conditional fault-action requests below extend
this demonstration. `knill_bench` remains an independent future consumer.


## Static Knill memory and offline stages (M6-D)

```bash
python examples/knill_memory_offline_decoding.py --distance 3 --basis X --bit 1 --teleportations 2 --resource-rounds 3 --post-rounds 2 --shots 1000 --p 0.001 --seed 7
python examples/knill_memory_offline_decoding.py --suite --shots 20000 --p 0.001 --seed 20261108 --output-dir implementation_files/e2etest/m6d_knill
```

The fixed suite runs X/Z at d=3/5, T=1/2, with 20,000 shots per case in the
command above. Resource and input preparation each use d full syndrome rounds
by default; post-teleportation SE defaults to one round and is independently
selectable. Logical identity `D` persists while fresh `physical_A0/B0`, then
`physical_A1/B1` blocks are allocated. There is no block reuse or adaptive gate.
All gates and noise are static. Each case compiles once, samples one global raw
batch, and decodes preparations, Bell readouts and ordinary SE sequentially in
software. All canonical deterministic cross-stage detectors remain present.

The source example exposes `build_knill`, `prepare_experiment`, `prepare_compiled`,
`analyze_knill`, `run_knill` and `save_report`. Its PyMatching adapters are optional
consumer code. To replay the same data with another readout decoder:

```python
from examples.knill_memory_offline_decoding import (
    prepare_experiment, analyze_knill, ReadoutMatching,
)

experiment = prepare_experiment(distance=3, teleportations=2, p=0.001)
raw = experiment.compiled.circuit.compile_sampler(seed=7).sample(shots=1000)
first = analyze_knill(experiment, raw)
alternative = {
    r.readout.module_id: ReadoutMatching(r, weights=[1.2] * len(r.record_ids))
    for r in experiment.requests.readouts
}
second = analyze_knill(experiment, raw, readout_decoders=alternative)
```

`boundary_decoders` independently replaces preparation/ordinary-SE adapters by
module ID. These source-example functions are not installed converter APIs. An
external package can instead consume public `logical_to_stim_converter.decoding`
contracts and supply its own adapters without importing PyMatching:

- `compiled.make_frame_plan()` builds an immutable `OfflineFramePlan` once.
  `plan.start(raw, source_fingerprint=plan.source_fingerprint)` creates isolated
  caller-owned batch state. It retains original records and applies virtual
  Paulis/Bell feedback as an affine GF(2) transform, including later teleportations.
- `make_stage_requests(compiled)` returns typed `BoundaryRequest`, `ReadoutRequest`
  and causal `StageRequests.order`. Each request exposes a M6-B view, exact
  global/local record/detector IDs, check support, physical ordering/orientation,
  and boundary-model or conditional-sector information.
- `StageDecoder.decode_batch(request, StageInputs)` returns `StageResult` with a
  source-bound `CorrectionBatch`. Physical boundary bits are X(data_ids), then
  Z(data_ids). Readout bits flip records in `LogicalReadout.records` order.
  The boundary ID and source fingerprint validate provenance; shapes/binary values
  are checked. Boundary results also declare predicted last-record errors and
  net post-correction sectors. They are hypotheses, not a proof of recovery.
- `batch.apply(result.correction)` applies each boundary once, including the
  delta to later Bell byproducts. `batch.events(view)` recomputes events from
  current interpreted records. Original raw samples and physical global events
  remain unchanged. Directly slicing initial events after a frame edit is unsafe.
- Readout expected sectors come from `request.sector_map` applied to prior decoded
  net boundary sectors, plus `sector_constant`. The map is derived by exact signed
  Pauli conjugation through actual physical H/CNOT pairs, not code-name assumptions.
  Carried physical-frame anticommutation is already in the interpreted records.
  Never subtract it a second time.

Preparation inference has two separate steps. A circuit-level temporal DEM predicts
**last recorded check XOR actual boundary check**, plus the prepared logical error.
The model copies the actual noisy physical prefix and selected strict stage
annotations, then appends ideal boundary MPP probes with observable targets. These
probes exist **only in the model**: no experiment samples them, and the decoder
never receives their truth. Their parities are verified deterministic ideal flows.
CSS capacity matching then finds a physical sector representative using the
predicted final syndrome; the known prepared eigenvalue fixes its logical
ambiguity. The physical correction-to-record map is independently verified against
actual correction execution. This is different from capacity-decoding a noisy raw
last syndrome. Early/late result faults are tested in a measurement-noise regime.

Ordinary SE uses strict within-module M6-B regions and corresponding boundary
check-error targets. A single post-SE round has no internal temporal detectors;
its final-result error is not independently identifiable. Cross-boundary models
with shot-specific frame reference offsets are left to an external joint strategy.
The baseline keeps cross-stage detectors in the canonical artifact but does not
use them as if unchanged after inserting software frames.

For Bell readout, per-patch capacity matching receives
`H_P @ interpreted_data XOR predicted_sector`, with the current physical check and
logical representatives. Raw gauge-dependent parities are never inserted as
zero-expected detectors. `make_conditional_readout_model(compiled, bell)` exports
an explicit `ConditionalReadoutModel` from immediately before resource CNOT through
destructive Bell readout: physical noise atoms, probabilities and exclusive channel
groups, joint readout flips, X/Z syndrome/logical effects, and survivor physical X/Z
actions. It includes resource-CNOT, Bell-CNOT, measurement and idle faults. The
boundary assumes prior sector/frame hypotheses; unrecognized earlier residual
errors remain possible. It is **not** a conditional deterministic Stim DEM.
Every atom's readout and survivor action is tested against Stim's Pauli propagator.

The Bell adapter uses unit-weight per-patch capacity matching and does not perform
joint inference using those correlated atoms. Temporal correlated MWPM is also a
heuristic: PyMatching merges parallel edges and can retain one representative's
fault IDs, so ambiguous boundary targets may be mispredicted. Unsupported graph
hyperedges or physical noise channels raise explicit errors. Exact canonical
physical noise/DEMs and the conditional action model retain all mechanisms;
these algorithmic approximations are confined to the example. Nonzero-noise
recovery is allowed to fail, and no optimality or threshold claim is made.

Final failure compares the corrected final logical bit to the known intended
`ObservableInfo.expected_value`, independently of the decoder's belief. Raw
physical observable flips remain available for separate global-decoder analyses;
they are not assumed equal to this modular strategy's residual failures. Tests
cover both signs, all Bell branches, physical d=3/5 reference entanglement after
T=1/2, physical/virtual Paulis and H, selected faults, independent parallel gadgets,
immutable replay and chunk-independent predictions. No normal decoder request
contains hidden faults or tableau state. The M5 noiseless helper is not imported
by the example.

The separate [M6-D results](implementation_files/e2etest/m6d_knill/README.md) contain
JSON/CSV aggregates, a LER/timing PNG/SVG, full test results and wall-time analysis.
`timings_seconds` measures exclusive `perf_counter` phases: compile (including
internal physical/flow validation), exported global DEM, frame maps, stage models,
conditional actions, matching setup, sampler setup, sampling, m2d, current-event
inputs, temporal/capacity decoding, frame updates and final evaluation. Total wall
and remaining overhead are included; model/map construction occurs outside the
shot loop. The execution report additionally measures full CLI startup/imports,
report/figure generation and exit. Timings are observations of the recorded
machine/load, not CI performance assertions. Production decoder optimization,
conditional joint inference, scheduling and runner integration remain future work.

## Knill memory on three explicitly reused patches (M7-C)

```bash
python examples/knill_memory_three_patch_reuse.py --distance 5 --basis X --bit 1 --teleportations 4 --resource-rounds 5 --post-rounds 1 --shots 1000 --batch-size 128 --seed 7
python examples/knill_memory_three_patch_reuse.py --suite --shots 2048 --batch-size 256 --p 0.003 --seed 20261108 --output-dir implementation_files/e2etest/m7c_three_patch
```

The example explicitly declares `(D input, A, B output)` physical assignments
P0/P1/P2, P2/P0/P1, P1/P2/P0 and repeats that caller-authored list. Fresh A_t/B_t
names bind to specifically named measured patches before each later KnillEC.
The compiler validates those directives. Persistent D returns to P0 after three
cycles, on P0's third use (epoch 2). Physical wires stay fixed: 51 qubits at d=3
or 147 at d=5, for any number of cycles. Circuit, detector, history and raw-record
sizes grow with duration; batches bound the number of shot rows kept in memory.

```python
from examples.knill_memory_three_patch_reuse import build_explicit_three_patch_knill
from examples.knill_memory_offline_decoding import prepare_compiled, analyze_knill

compiled = build_explicit_three_patch_knill(distance=3, teleportations=3)
experiment = prepare_compiled(compiled)
raw = compiled.circuit.compile_sampler(seed=7).sample(shots=64)
baseline = analyze_knill(experiment, raw)
# Reuse raw and experiment with your boundary_decoders/readout_decoders mappings.
assert baseline.errors == 0
```

`explicit_three_patch_program` also accepts a caller-supplied per-cycle schedule;
manually written BindPatch/KnillEC sequences work with the standard compiler.
Open outputs use `allow_open_outputs=True`; LER runs require final readout.
The original M6-D fresh-resource example remains separate. Both use the same
restricted external MWPM/capacity adapters, with no decoder in the converter.
Reports include actual use tables, epoch/stage/view provenance, canonical DEM
identity, honest final-readout failure labels and separate wall phases.
See [the physical-use and verification guide](docs/three_patch_knill.md).
