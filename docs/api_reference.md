# Public consumer API reference

This reference describes the **0.0.1 internal research integration**, reviewed
2026-11-09 against runtime baseline `8a409593ab09441c189ec3fe8742ab3f64055cce`.
The [installation guide](development.md) pins that reachable revision. Documented
consumer paths are intended for this integration; there is no durable semantic
versioning guarantee for every root-exported low-level object. Preserve the commit
SHA with results. No runtime behavior changes in this documentation phase.

Use root imports for compilation, operations, language and noise policy;
`logical_to_stim_converter.decoding` for offline contracts; and
`logical_to_stim_converter.noise` for `ResourcePreparationBoundary`. Root and
[decoding exports](../src/logical_to_stim_converter/decoding/__init__.py) are not
identical. Classes returned by factories are normally inspected, not manually
constructed. Private `compiler/_*.py` modules, underscored snapshot fields and
example-layer decoder adapters are implementation details. The converter owns
static physical compilation/provenance/models and linear frame propagation;
callers own sampling, inference, correction selection and experiment orchestration.

## Navigation

- [Identities and physical meaning](#identities-and-physical-meaning)
- [Array and source conventions](#array-and-source-conventions)
- [Language entry points](#language-entry-points)
- [Compiler and compiled artifacts](#compiler-and-compiled-artifacts)
- [Measurement and protocol metadata](#measurement-and-protocol-metadata)
- [Noise policy](#noise-policy)
- [Decoder views and index maps](#decoder-views-and-index-maps)
- [Temporal and readout stage requests](#temporal-and-readout-stage-requests)
- [Offline frame plans and corrections](#offline-frame-plans-and-corrections)
- [Conditional Bell fault actions](#conditional-bell-fault-actions)
- [Exceptions and verification](#exceptions-and-verification)

## Identities and physical meaning

| Term / public type | Contract and concrete example |
| --- | --- |
| Logical handle (`str`) | A state identity, e.g. `D`. Knill moves D from P0 to P2 without changing D. Temporary A/B handles retire. |
| Physical block (`LogicalBlock`) | Fixed placed data/ancilla sites and layout, e.g. P0. Coordinates and wires stay fixed on reuse. |
| Local qubit key (`str`) | Layout-local data/ancilla identifier, e.g. an element of `block.layout.data_ids`; not a global wire or logical handle. |
| Global site (`tuple[str, str]`) | `(block_id, local_key)`, e.g. `("P0", block.layout.data_ids[0])`, stable across resets. |
| Stim global qubit index (`int`) | `compiled.physical_qubit_map[site]`; assigned by final assembly, not necessarily block registration order. |
| `BlockUseId(block_id: str, epoch: int = 0)` | Frozen, ordered reset-to-release occupancy. `BlockUseId("P0", 1)` is P0's second actual initialization. Empty IDs, booleans/negative epochs raise ValueError. |
| Epoch | Per-physical-patch generation, initially zero. Only LogicalInit starts/increments it. BIND, SE rounds, teleportation and TICK do not increment it. |
| Module / fragment | A unique executed primitive module ID and its `ModuleFragment` wrapper around verified stimflow chunks/loops/reflows plus physical/logical provenance. Multi-block CNOT is one fragment; a multi-target memory primitive may produce several. |
| Composite | A `CompositeOperation`, e.g. BellStatePrep or KnillEC, expanding to ordinary primitives with parent/child IDs. A composite adds no duplicate noise. |
| Stage | Semantic QEC region (`stage_id: str | None`), e.g. resource preparation or Bell readout. Separate from a primitive, epoch or time interval. |
| Semantic label | Authored `operation_id`, or LSTIM `[label]`. Labels connect source spans to operation/composite metadata; they do not assign epochs or physical layers. |
| Physical time layer / TICK | Global gate/idle interval in `compiled.time_layers`, delimited by physical TICKs. One SE round contains multiple layers. No laboratory duration model is implied. |
| MeasurementKey / raw index | Semantic historical identity versus absolute zero-based column in the complete raw record batch. Both survive retirement/reuse. |

For the three-cycle schedule D visits P0/0, P2/0, P1/1, P0/2. That is three
relocations of one logical state, seven physical uses and three fixed patches.
See [the use table](three_patch_knill.md#physical-identities-and-cycles) and
[architecture glossary](architecture.md#identity-and-lifecycle-glossary-m7-a).

## Array and source conventions

Let S be shots, M canonical measurements, D global detectors and O reliable global
observables. Offline batch APIs accept unpacked two-dimensional binary bool or
integer arrays (values 0/1), never bit-packed bytes or float probability arrays.
They generally normalize outputs to `numpy.bool_`. Matrices returned by
`check_matrix` are `numpy.uint8`. The older `interpreted_measurements` helper
coerces its input to bool; use proper binary arrays consistently.

| Array | Shape / column order |
| --- | --- |
| Physical raw measurements | `[S, M]`, canonical zero-based record order across every block/use |
| Global events / observable flips | `[S, D]` / `[S, O]`, canonical IDs |
| View events / flips / records | `[S, len(view.detector_map.global_ids)]`, `[S, len(view.observable_map.global_ids)]`, `[S, len(view.measurement_map.global_ids)]`, exact local selection order |
| Noiseless reference | `[M]`, global raw-record convention; deterministic parity signs must agree |
| Physical correction bits | `[S, 2*n]`, X support on `data_ids`, then Z support on the same ordered data IDs |
| Readout correction bits | `[S, n]`, `LogicalReadout.records` order |
| Boundary sectors / record errors | `[S, len(request.checks)]`, request check order |
| Final physical frame arrays | `[S, compiled.circuit.num_qubits]`, global Stim wire order |

Arrays alone cannot prove circuit identity. `source_fingerprint(compiled) -> str`
from `decoding` hashes exact ideal/selected physical instructions, Stim version,
metadata, use/owner/ancestry/time histories and M9 boundaries. View schema is
`decoder-view-v3`; regenerate v1/v2 caches and all models after any source change.
Same gates with different authored binding/label metadata can have different
fingerprints. Comments and SourceSpan provenance are excluded. Exact instruction
snapshots avoid lossy text probability round trips. Supply fingerprints where
accepted and use `view.assert_source(compiled)` for explicit source validation.

Sampling uses Stim's public circuit APIs. Sample a physical batch once and replay
it offline; sampling again for another decoder changes the experiment. View
projection, record flips and frame analysis preserve input raw arrays. Frame
batches store immutable owned copies; source-bound input/correction containers
also freeze their arrays. A `CompiledCircuit` is a frozen dataclass, but its Stim
circuit objects remain mutable: copy them for experiments, then regenerate derived
models if the source changes. View circuit/DEM properties return independent copies.

## Language entry points

Import these from `logical_to_stim_converter` or its `language` namespace.
Signatures below use ordinary Python typing; `FileNode` is the language AST type.

```text
parse_logical_circuit(source: str, source_name: str = "<string>",
                      *, max_operations: int = 100_000) -> LogicalProgram
parse_logical_file(path: str | os.PathLike[str],
                   *, max_operations: int = 100_000) -> LogicalProgram
LogicalProgram(source: str, source_name: str = "<string>",
               *, max_operations: int = 100_000)
format_logical_circuit(program: LogicalProgram | FileNode) -> str
program.to_operations() -> tuple
program.compile(*, noise_model: NoiseModel | None = None,
                allow_open_outputs: bool = False) -> CompiledCircuit
```

Parsing validates syntax and static semantics and lowers bounded repeats without
physical compilation or sampling. The operation budget includes BIND directives
and members of parallel groups. `program.source`, `ast`, `blocks`, `operations`,
`operation_spans`, `label_spans`, `expanded_operation_count` and `source_name`
retain immutable program/provenance data. `to_operations()` returns the ordered
tuple including explicit BindPatch and nested parallel tuples. `.compile()` uses
an empty initial mapping, executes every BIND, and delegates lifecycle/flow/noise
validation to CircuitCompiler with fresh state on each call.

File parsing reads UTF-8 bytes, preserves CRLF offsets/path and chains OS/encoding
failures. Formatting accepts a program or raw AST, validates static semantics,
preserves all typed semantic fields and nesting/target/binding/option order, drops
comments/blank lines, uses four spaces/LF/final newline, and never unrolls or
compiles. Syntax-only `language.parse_ast` is distinct from semantic validation.

The [README program](../README.md#quick-start) is the minimal executable example.
The [language guide](lstim.md) covers file/formatter use; the
[v1 contract](lstim_v1.md) defines opcodes/defaults and bounded syntax. No generic
expressions, runtime branching, automatic allocation, text noise/decoder config,
physical Stim passthrough or CLI is implemented.

All ordinary source failures derive from root-exported `LSTIMError(ValueError)`:

| Error | Meaning / fields |
| --- | --- |
| `LstimSyntaxError` | Lexical/grammar/parser-budget failure; located file/line/column |
| `LSTIMSemanticError` | Unsupported version, names/declarations/signatures/options or static expansion |
| `LSTIMFileError` | Read/UTF-8 failure; `original_error` and `__cause__` preserved; invalid UTF-8 reports first invalid byte/location |
| `LSTIMCompileError` | Physical compiler ValueError/TypeError/NotImplementedError; preserves original cause and file, without guessing a source statement |

`str(error)` includes a bounded excerpt/caret when located. Common fields are
`message`, `span`, `source_name`, `line`, `column`, `excerpt`, `caret`; fields
requiring a location are None when only the file is known.
[Source](../src/logical_to_stim_converter/language/program.py),
[errors](../src/logical_to_stim_converter/language/errors.py),
[API tests](../tests/test_lstim_api.py), [formatter tests](../tests/test_lstim_formatter.py).

## Compiler and compiled artifacts

Import from `logical_to_stim_converter`:

```text
CircuitCompiler(blocks: Sequence[LogicalBlock], *,
                logical_to_block: Mapping[str, str] | None = None,
                backend: CodeBackend | None = None)
compiler.compile(operations: Sequence[OperationModule | BindPatch |
                                     Sequence[OperationModule | BindPatch]], *,
                 noise_model: NoiseModel | None = None,
                 allow_open_outputs: bool = False) -> CompiledCircuit
```

The default backend is `RotatedSurfaceCodeBackend`. Omitted mapping reserves
block-named logical handles; explicit `{}` reserves none. Each compile owns fresh
state. Nested operation lists/tuples are explicit parallel layers; consecutive
entries form barriers. Parallel physical overlap is rejected. BindPatch only
reserves an explicitly selected available patch, without reset/duration/noise;
LogicalInit starts the use. Stale handles and pending reservation conflicts fail.
Closed compilation requires all registered patches measured; open mode permits
active outputs/unused blocks and exports a verified interface without fake readout.

Core root factories and operations used by consumers:

```text
CodeSpec.rotated_surface(distance: int) -> CodeSpec
PhysicalLayout.rotated_surface(code: CodeSpec) -> PhysicalLayout
LogicalBlock.placed(block_id: str, code: CodeSpec, *, patch_index=0) -> LogicalBlock
BindPatch(logical_id: str, physical_block_id: str)
LogicalInit(targets: str | tuple[str, ...], basis: str, rounds: int, *,
            noise: NoiseOverride | None = None, operation_id: str | None = None)
SyndromeExtraction(targets: str | tuple[str, ...], rounds: int, *, noise=None, operation_id=None)
LogicalMeasure(targets: str | tuple[str, ...], basis: str,
               mode: str = "deterministic", *, noise=None, operation_id=None)
TransversalH(targets: str | tuple[str, ...], *, noise=None, operation_id=None)
TransversalCNOT(control: str, target: str, *, noise=None, operation_id=None)
LogicalPauli(targets: str | tuple[str, ...], pauli: str,
             mode: str = "physical", *, noise=None, operation_id=None)
BellStatePrep(first, second, rounds=None, *, noise=None, operation_id=None)
KnillEC(data, first_resource, output_resource, *, prepare_resource=True,
        rounds=None, noise=None, operation_id=None)
```

Here targets/operand names are logical handles. Basis is X/Z; Pauli is X/Y/Z;
Pauli mode is physical/frame. Deterministic readout must have a known intended
logical eigenvalue; `mode="random"` retains random classical records without a
reliable observable. Bell resources default to d complete SE rounds. Existing
resources may be consumed with `prepare_resource=False`. Geometry, code
orientation and actual signed logical actions constrain H/CNOT; a generic CSS
CodeSpec does not provide a physical backend. See the executable
[memory and open-Knill examples](examples.md), [gate contract](architecture.md#m3-code-orientation-and-multi-block-gate-contract)
and [lifecycle tests](../tests/test_patch_reuse.py).

`CompiledCircuit` is returned by compilation; consumers should not manually supply
its internal construction/evaluation state. Principal fields/methods:

| Member | Return / ownership / limitation |
| --- | --- |
| `ideal_circuit: stim.Circuit` | Verified ideal canonical circuit, retaining all global detectors |
| `noisy_circuit: stim.Circuit | None` | Noise-injected canonical circuit if a NoiseModel was supplied; None when omitted |
| `circuit: stim.Circuit` | Noisy circuit when present, otherwise ideal; use `.detector_error_model()` for native canonical DEM |
| `validate_metadata() -> None` | Checks record/annotation/use/causal provenance and M9 boundaries; malformed metadata raises ValueError |
| `append(operations, *, noise_model=None) -> CompiledCircuit` | Recompiles complete prefix plus continuation with `allow_open_outputs=True`. None inherits prior full noise policy; pass `NoiseModel()` for zero ordinary noise. Does not mutate or execute the prefix. |
| `physical_qubit_map`, `logical_to_block`, `orientations`, `block_status` | Read-only maps of stable sites to final wire indices, final handle locations, code frames and physical state |
| `measurements`, `detectors`, `observables` | Tuples in canonical global index order; history is not replaced by the newest use |
| `measurement_index_by_key` | Read-only semantic key -> absolute raw-record index |
| `preparations`, `readouts`, `bell_measurements`, `relocation_history` | Historical protocol records, including retired handles |
| `block_uses`, `binding_history`, `available_blocks` | Reset-execution-order occupancy history, zero-time reservations and currently bindable patches |
| `preparation_dependencies`, `block_preparation_dependencies`, `use_preparation_dependencies`, `ancestry_events` | Causal histories through actual interactions/relocations; coordinate reuse alone creates no ancestry |
| `frames`, `time_layers`, `fragments`, `composites` | Symbolic affine logical frames, physical scheduling and primitive/composite provenance |
| `open_logical_outputs`, `open_interface` | Active handle -> block map and verified stimflow interface |
| `resource_preparation_boundaries` | Immutable M9 noise cut/target provenance; empty when disabled/no resources |
| `stage_separated_circuit(*, noisy=False) -> stim.Circuit` | Explicit legacy annotation view with unchanged physics; noisy=True fails if no noisy circuit |
| `stage_separated_detector_indices` | Local legacy view -> canonical detector IDs; `detector_boundary_candidates` retain global crossing IDs |

`suppressed_detectors` is a compatibility alias for candidates: those detectors
are present in canonical circuits. A stage-separated view does not establish
independent stage inference. Constructor/lifecycle/geometry/unsupported-operation
failures use ValueError/TypeError/NotImplementedError; native Stim/stimflow
verification errors propagate in the Python compiler, or through LSTIMCompileError
in the language bridge. [Source](../src/logical_to_stim_converter/compiler/circuit_compiler.py),
[metadata tests](../tests/test_global_detector_provenance.py),
[open continuation tests](../tests/test_knill_teleportation.py).

## Measurement and protocol metadata

These types are root imports; fields below are consumer contracts. They are
normally obtained from CompiledCircuit rather than constructed independently.

```text
MeasurementKey(block_id: str, local_id: str, kind: str,
               round_index: int | None = None, epoch: int = 0)
MeasurementInfo(key: MeasurementKey, index: int, logical_id: str, basis: str,
                module_id: str, time_layer: int, stage_id: str | None = None)
```

Keys distinguish syndrome/data records, per-use round and epoch;
`key.block_use_id -> BlockUseId`. Global indices increase across uses, while
syndrome round counters restart. `MeasurementInfo.logical_id` is the historical
producer's owner, not the final handle occupying its coordinates.

```text
DetectorInfo(index: int, coordinates: tuple[float, ...],
    measurement_indices: tuple[int, ...], measurement_keys: tuple[MeasurementKey, ...],
    block_id: str, check_id: str, supporting_block_ids: tuple[str, ...] = (),
    stage_id: str | None = None, source_stage_ids: tuple[str | None, ...] = (),
    crosses_decoder_boundary: bool = False, anchor_module_id: str = "", basis: str = "",
    physical_support: tuple[tuple[str, str], ...] = (),
    anchor_use_id: BlockUseId | None = None, source_use_ids: tuple[BlockUseId, ...] = ())
ObservableInfo(index: int, logical_id: str, block_id: str, basis: str,
    measurement_indices: tuple[int, ...], readout_measurement_indices: tuple[int, ...] = (),
    frame_correction: ParityExpression = ParityExpression(), expected_value: int = 0,
    block_use_id: BlockUseId | None = None)
```

`DetectorInfo` provides `index`, absolute `coordinates`, sorted XOR
`measurement_indices` and aligned `measurement_keys`; `block_id`/`check_id`
(also `anchor_block_id`/`anchor_check_id`) identify its semantic anchor.
`supporting_block_ids`, `anchor_module_id`, `basis`, stable-site `physical_support`,
`anchor_use_id`, `source_use_ids`, `stage_id`, `source_stage_ids` and
`crosses_decoder_boundary` distinguish the anchor from every contributor.
`None` is a valid ordinary source stage. Coordinates alone do not determine scope.

`ObservableInfo` provides global `index`, `logical_id`, `block_id`, `basis`, full
Stim `measurement_indices`, canonical `readout_measurement_indices`, affine
`frame_correction: ParityExpression`, intended `expected_value` (0/1) and
`block_use_id`. IDs follow sorted historical logical names, not patch order.
`ParityExpression(terms=(), constant=False)` is a symbolic XOR of MeasurementKeys
and a binary constant; `PauliFrame.x`/`.z` use these expressions. Stim observable
annotations omit affine constants. Canonical observable flips are relative to a
noiseless reference; absolute intended bits additionally use frame interpretation.

```text
compiled.interpreted_measurements(measurements, *, preparation_corrections=None,
                                  validation="noiseless") -> bool[S, O]
compiled.evaluate_frames(measurements, preparation_corrections, *,
                         validation="noiseless") -> FrameEvaluation
compiled.validate_noiseless_preparation_corrections(measurements,
                                                    preparation_corrections) -> None
```

Without Bell measurements, `interpreted_measurements` applies the readout parity
and symbolic frame. Knill requires resolved preparation corrections; omission
raises ValueError instead of assuming zero. Correction mappings are preparation
module ID -> one `PhysicalPauliFrame` per shot. `FrameEvaluation` is the returned
evaluation object exposing `corrected_measurements`, `logical_outputs`,
`readout_values`, `bell_measurements`, `final_frames`. Its class lives in private
compiler implementation code; consume the returned fields without importing that
class. Final frames map open logical handles to per-shot PhysicalPauliFrames.
Noiseless mode proves final recorded syndrome equations and the prepared logical
value. `validation="hypothesis"` checks source/support/orientation/logical metadata
without requiring a noisy estimate to reproduce faulty checks. Acceptance of a
hypothesis does not prove recovery. The batch frame-plan API below is the reusable
sparse alternative. Physical samples/circuits remain unchanged.

`PreparationInfo` records `module_id`, `block_id`, `logical_id`, `stage_id`,
prepared `basis`, `orientation`, ordered `data_ids`, `checks`, physical `logical_x`
and `logical_z` supports, and `block_use_id`. Each CheckHistory retains check
ID/basis/support and ordered measurement keys. `.rounds`, `.gauge_measurements`
and `.unresolved_frame` expose duration, first conjugate-basis sector labels and
an unresolved physical correction. `check_matrix(basis) -> uint8[checks, data]`;
`resolve(x, z) -> PhysicalPauliFrame` accepts two binary length-n vectors in
`data_ids` order, wrapping a hypothesis without selecting/proving it. Both support
fields None mean unresolved; empty tuples mean resolved identity.

`LogicalReadout` records module/handle/block/use, basis/orientation/mode/stage,
ordered `records`, `logical_parity` and `checks`. `check_matrix(basis)` columns
follow records. Random Bell X/Z readouts have no reliable deterministic observable.
`BellMeasurementResult` connects its two readouts, incoming/raw/logical/physical
frames, dependency IDs and data/first-resource/output use IDs.
`RelocationRecord` retains source/output blocks/uses and logical identity.
`BlockUseInfo(use_id, reset_module_id, terminal_module_id=None,
logical_owner_history=(), measurement_start=0, measurement_stop=None,
time_layer_start=0, time_layer_stop=None)` describes half-open global record/layer
intervals, including any concurrent records. Stops remain None for active uses.
Owner events preserve the transfer from resource B to persistent D without reset.

[Protocol source](../src/logical_to_stim_converter/core/protocol.py),
[record metadata](../src/logical_to_stim_converter/core/compiler_context.py),
[reuse tests](../tests/test_patch_reuse.py),
[frame validation tests](../tests/test_frame_validation_modes.py).

## Noise policy

Root imports (also policy types from `logical_to_stim_converter.noise`):

```text
NoiseParameters(reset: float = 0, one_qubit: float = 0, two_qubit: float = 0,
                measurement: float = 0, idle: float = 0)
NoiseOverride(reset: float | None = None, one_qubit: float | None = None,
              two_qubit: float | None = None, measurement: float | None = None,
              idle: float | None = None)
ResourcePreparationNoise(enabled: bool = False, p_st_transversal: float = 0.0)
NoiseModel(default: NoiseParameters = NoiseParameters(),
           operation_overrides: Mapping[str, NoiseOverride] = {},
           resource_preparation: ResourcePreparationNoise = ResourcePreparationNoise())
NoiseModel.uniform_depolarizing(probability: float) -> NoiseModel
model.resolve(operation_type: str | None = None,
              instance: NoiseOverride | None = None) -> NoiseParameters
```

Default arguments shown as values denote fresh dataclass factories. Instance
channels override primitive-type channels, which override global defaults;
None inherits and zero replaces. Supported type keys are LogicalInit,
SyndromeExtraction, LogicalMeasure, TransversalH, TransversalCNOT and LogicalPauli.
Composites pass policy to their primitives without injecting again. Unknown keys,
wrong policy types and invalid probabilities raise ValueError.

Ordinary probabilities are finite non-boolean Python int/float in [0,1]; global
channels cannot be None. Reset uses an anticommuting Pauli after reset;
one-/two-qubit gates use depolarization; measurement flips reported results;
idle depolarization is applied once on active unused sites in composed layers,
including eligible ancillas. Waiting live blocks use global idle defaults;
never-initialized/retired gaps do not idle. `uniform_depolarizing(p)` sets all five
channel probabilities to p, not a hardware-duration/rate model. `NoiseModel()`
adds zero noise; omitting a model leaves noisy_circuit=None. Native DEM extraction
can reject some ordinary [0,1] configurations; no approximation is substituted.

M9 requires a bool enable and finite non-boolean p_st_transversal in **[0,.75]**,
even disabled. Enabled zero still suppresses the two Bell-owned initialization
reset/SE intervals. Nonzero channels target only layout data once per resource
use, after final SE idle/TICK and before resource CNOT, with no extra TICK.
D/spectators and later waiting/gates retain ordinary noise. The
[dedicated M9 guide](resource_preparation_noise.md#physical-contract) specifies
eligibility, exact gate/result/idle suppressions, channel placement and decoder cuts.

`ResourcePreparationBoundary` is imported from `logical_to_stim_converter.noise`:

```text
ResourcePreparationBoundary(bell_preparation_id: str, preparation_module_id: str,
    block_use_id: BlockUseId, resource_entangling_module_id: str,
    first_layer: int, final_se_layer: int, ideal_boundary_instruction: int,
    data_sites: tuple[tuple[str, str], ...], channel_instruction: int | None = None)
NoiseInjector().apply(ideal: stim.Circuit, *, model: NoiseModel,
    physical_map: Mapping[tuple[str, str], int], layers: tuple[TimeLayer, ...],
    fragments: tuple[ModuleFragment, ...],
    resource_preparation_boundaries: tuple[ResourcePreparationBoundary, ...] | None = None
) -> stim.Circuit
```

Boundary first/final layers are inclusive physical interval indices; the ideal
instruction index is an exclusive prefix cut. `data_sites` are stable physical
site keys, while optional `channel_instruction` is the inserted noisy-circuit
instruction index (None when no channel is emitted); `.channel_tag` carries
`resource_post_se:<module>` provenance. Standard compilation resolves and validates
the complete immutable tuple structurally from executed Bell composites.

Direct low-level apply requires a verified ideal schedule/map/fragments and rejects
already noisy input. Disabled policy accepts omitted/None boundaries. Enabled
omitted/None raises ValueError before setup, also at p=0. Explicit `()` declares
no eligible resources and uses ordinary noise. Nonempty verified tuples apply the
special policy; disabled/nonempty, malformed tuple/element types and duplicates
fail. The direct caller attests to eligibility; the injector cannot recover it
from primitive names/stages and contains no second resolver. Prefer standard
compile for complete validation. [Policy source](../src/logical_to_stim_converter/noise/model.py),
[injector](../src/logical_to_stim_converter/noise/injector.py),
[exact tests](../tests/test_resource_preparation_noise.py).

## Decoder views and index maps

Import the following from `logical_to_stim_converter.decoding` (several are also
root exports):

```text
make_decoder_view(compiled, *, detector_selector=None, observable_selector=None,
    measurement_selector=None, cross_region_policy="retain",
    model_source="physical_circuit", dem_options=DEMOptions(),
    expected_source_fingerprint=None) -> DecoderView
compiled.make_decoder_view(**options) -> DecoderView
DEMOptions(decompose_errors: bool = False, flatten_loops: bool = False)
IndexMap(global_size: int, global_ids: tuple[int, ...])
observable_local_views(compiled, *, observable_selector=None,
                       region_selector=None, **options) -> tuple[DecoderView, ...]
```

None selects all; explicit ID sequences preserve caller order; metadata predicates
preserve canonical order. Observable selectors additionally accept historical
logical names; random readouts raise UndefinedObservableError. Measurement
selectors accept global IDs or MeasurementKeys. Detector/observable/measurement
selection is independent: selecting projected records never limits records needed
for parity evaluation. `IndexMap.local_to_global` equals `global_ids`;
`.global_to_local` is a read-only inverse, `.local_ids` contiguous and
`.project(values)` returns a copied binary batch in declared order. Duplicate or
out-of-range IDs and malformed selections raise DecoderViewError.

```text
DetectorSelector(block_ids: tuple[str, ...] | None = None,
    block_membership: str = "anchor", stage_ids: tuple[str | None, ...] | None = None,
    stage_membership: str = "touching", basis: str | None = None,
    predicate: Callable[[DetectorInfo], bool] | None = None,
    description: str = "semantic selection", use_ids: tuple[BlockUseId, ...] | None = None,
    use_membership: str = "anchor")
```

Filters intersect, tuple entries form a union. Anchor means semantic anchor,
touching means any source, strict means all sources in the set. Blocks include
all epochs; use_ids selects specific historical uses. Basis is the physical anchor
check basis after orientation changes. `a | b` unions predicates. Cross-region
policies retain (default), omit or joint select annotations spanning uses/blocks/
stages; none deletes a physical fault. `SelectionAudit` reports requested,
omitted/crossing IDs and actual region block/stage/use IDs versus requested uses.

A view keeps every physical gate/noise channel and raw measurement and changes
only annotations. Stim re-extracts an exact physical marginal for selected IDs;
it is not a conditional posterior or direct truncation of a DEM. Faults touching
excluded detectors retain their selected effects; hyperedges and correlated `^`
components survive. Only physical_circuit model source is supported. Exact
options do not imply graphlike matching compatibility. Extraction failures raise
DEMConstructionError, unsupported approximation modes UnsupportedProjectionError.
The canonical full model remains `compiled.circuit.detector_error_model()`.

Public view properties: `source_fingerprint`, `schema_version`, `detector_map`,
`observable_map`, `measurement_map`, selected metadata tuples, `audit`,
`dem_options`, `detector_record_map`, `observable_record_map`, immutable
`reference_sample`; `source_circuit`, `circuit`, `detector_error_model` return copies.
Methods (all batch outputs bool):

```text
view.assert_source(compiled) -> None
view.project_detection_events(global_events, *, source_fingerprint=None) -> bool[S, d]
view.project_observable_flips(global_flips, *, source_fingerprint=None) -> bool[S, o]
view.project_raw_measurements(global_raw, *, source_fingerprint=None) -> bool[S, m]
view.events_from_raw(global_raw, *, reference_sample=None,
                     source_fingerprint=None) -> bool[S, d]
view.observable_flips_from_raw(global_raw, *, reference_sample=None,
                               source_fingerprint=None) -> bool[S, o]
view.inputs_from_raw(global_raw, *, record_flips=None,
                      source_fingerprint=None) -> DecoderInputs
view.update_detection_events(global_events, record_flips) -> bool[S, d]
```

Lowercase d/o/m are selected widths. Parity methods require all M raw columns,
XORing against the reference convention, including signed deterministic values.
Override reference shape is [M] and must match selected noiseless parities.
`DecoderInputs` contains immutable source-bound `detection_events`,
`observable_flips` and selected `records`. Flips are labels for external evaluation,
not hidden information a decoder should receive. Optional record_flips uses a
copy; after frame edits recompute events or apply incidence-map updates, rather
than slicing stale physical events.

This block continues the README quick start (`compiled` and `raw`):

```python
from logical_to_stim_converter.decoding import DetectorSelector, observable_local_views

view = compiled.make_decoder_view(
    detector_selector=DetectorSelector(block_ids=("P0",)),
    observable_selector=("D",), measurement_selector=(1, 0),
)
inputs = view.inputs_from_raw(raw, source_fingerprint=view.source_fingerprint)
assert inputs.records.shape == (4, 2)
assert view.measurement_map.local_to_global == (1, 0)
assert (inputs.detection_events == view.events_from_raw(raw)).all()
assert len(observable_local_views(compiled)) == 1
```

`observable_local_views` uses time-expanded connected components of actual
CNOT/relocation/detector-flow uses, seeded by each observable. Reusing coordinates
does not join independent memories. `region_selector(observable_info)` may replace
the detector selector; this is a locality policy example, not an optimal decoder.

For caller-defined record transforms, `GF2Map(input_size, supports)` stores one
tuple of input columns per output bit; `.apply(bool[S,input_size]) -> bool[S,outputs]`.
`GF2Map.from_matrix(matrix)` takes `[input_bits, output_bits]`, not its transpose;
`.incidence_matrix` returns a sparse copy. `view.record_flip_map(input_ids, matrix)`
requires `[correction_bits, M]` and returns
`RecordFlipMap(source_fingerprint, input_ids, transform)`.
`map.apply(raw, correction_bits, *, source_fingerprint) -> bool[S,M]` validates
identity and dimensions, then XORs into a copy. `apply_record_flips(raw, flips)`
also accepts a shared [M] mask or [1,M]. These functions propagate specified
linear edits; they never infer a physical correction.

[View source](../src/logical_to_stim_converter/decoding/views.py),
[record maps](../src/logical_to_stim_converter/decoding/records.py),
[physical marginal tests](../tests/test_decoder_views.py),
[record tests](../tests/test_record_frames.py),
[epoch tests](../tests/test_epoch_views_noise.py).

## Temporal and readout stage requests

Import from `logical_to_stim_converter.decoding`:

```text
make_stage_requests(compiled) -> StageRequests
StageInputs(source_fingerprint: str, events: np.ndarray, records: np.ndarray,
            expected_sector: np.ndarray | None = None)
StageResult(correction: CorrectionBatch, predicted_record_errors: np.ndarray | None = None,
            net_sector: np.ndarray | None = None, diagnostics: tuple[tuple[str, float], ...] = ())
StageDecoder.decode_batch(self, request, inputs: StageInputs) -> StageResult
```

`StageDecoder` is a typing Protocol implemented by the caller, not an algorithm.
`StageRequests(boundaries, readouts, sector_input_ids, order)` holds tuples of
BoundaryRequest/ReadoutRequest. `order` is causal `(kind, module_id)` pairs with
kind boundary/readout; `sector_input_ids` orders `(module_id, check_id)` columns.
It schedules offline inference only and does not execute/sample stages.

`BoundaryRequest` exposes `module_id`, `block_id`, `block_use_id`, `orientation`,
`data_ids`, `checks`, `last_record_ids`, `preparation`, `source_preparation`, `view`,
`model_circuit`, `detector_error_model`, `target_ids`, `check_matrix(basis)`.
Use the factory instead of constructing its private exact snapshots. Preparation
is the optional known prepared-logical target for initialization; ordinary SE
has None. Source preparation identifies the actual reset of the use in both cases.
Last-record IDs and checks align; target IDs are last-record errors in check order,
then the prepared logical error if present. That target is final recorded check
XOR actual boundary check, not a directly measured decoder input.

Boundary models copy a physical prefix, select strict module-local annotations
and append ideal **model-only** MPP probes. Never sample these as experimental
measurements or pass their truth to decoders. Preparation models end before M9
post-SE faults; conditional Bell models own those channels. Exact decomposable
model failure raises DEMConstructionError. One-round ordinary SE has no internal
temporal detectors; general cross-boundary inference is downstream.

`ReadoutRequest(readout, record_ids, view, sector_map, sector_constant,
source_preparation=None)` exposes `block_use_id`, measured-basis `check_matrix`
and readout-local `logical_indices`. Record IDs follow `readout.records`.
`sector_map` maps `[S,len(requests.sector_input_ids)]` predicted net boundary sectors
to `[S,num_readout_checks]`; XOR `sector_constant` once. The signed transport uses
actual physical H/CNOT pairings. Current physical-frame anticommutation is already
in interpreted records and must not be subtracted again.

StageInputs events are current events in `request.view.detector_map` order;
records follow `request.view.measurement_map`; expected_sector (for readout) follows
request check rows. They are immutable binary batches with equal shot counts.
Their constructor checks binary shape/count, but adapters must check request
source fingerprint and widths. They contain no model-only boundary truth.
StageResult correction bits follow the frame boundary order described below;
boundary predicted_record_errors and net_sector follow `request.checks`.
Result validation checks binary/equal shot count; request-specific widths and
semantic correctness remain the adapter's responsibility. Diagnostics are optional.

For a minimal factory/shape example, continue the README memory program:

```python
from logical_to_stim_converter.decoding import StageInputs, make_stage_requests

requests = make_stage_requests(compiled)
request = requests.boundaries[0]
stage_inputs = StageInputs(
    request.view.source_fingerprint,
    request.view.events_from_raw(raw),
    request.view.project_raw_measurements(raw),
)
assert stage_inputs.records.shape[0] == len(raw)
assert len(request.target_ids) == len(request.checks) + 1
```

A concrete restricted external adapter is in
[knill_memory_offline_decoding.py](../examples/knill_memory_offline_decoding.py);
its temporal/capacity approximations are documented in the [example guide](examples.md#external-knill-decoding-demonstrations).
The [installed Knill tutorial](knill_memory_tutorial.md) supplies a small
consumer-owned observed-sector adapter without optional decoder dependencies.
[Stage source](../src/logical_to_stim_converter/decoding/stages.py),
[epoch stage/frame checks](../tests/test_epoch_stages_frames.py).

## Offline frame plans and corrections

Import these from `logical_to_stim_converter.decoding`:

```text
compiled.make_frame_plan() -> OfflineFramePlan
plan.start(raw, *, source_fingerprint) -> OfflineFrameBatch
CorrectionBatch(source_fingerprint: str, boundary_id: str, bits: np.ndarray,
                block_use_id: BlockUseId | None = None,
                input_ids: tuple[str, ...] | None = None)
batch.apply(correction: CorrectionBatch) -> None
batch.events(view: DecoderView) -> bool[S, selected_detectors]
```

Build a plan once from verified physical assembly. It is an immutable affine
transducer with `source_fingerprint`, `boundaries`/`boundary_by_id`, global raw
record/final-X/final-Z GF2Maps and constants. It precomputes actual H/CNOT/reset/
readout/Bell-feedback effects without samples, decoder inference or a shot loop.
Each `FrameBoundary` has unique module `boundary_id`, physical/readout `kind`,
block/use/orientation/data IDs, `input_ids` and record/final-X/final-Z maps.
Physical inputs are `X:<data_id>` in data order, then `Z:<data_id>`;
readout inputs are `record:<data_id>` in LogicalReadout.records order.

Starting a plan requires a matching fingerprint and binary [S,M] raw batch.
`OfflineFrameBatch` owns isolated mutable analysis; public `raw_measurements`,
`interpreted_measurements`, `final_x`, `final_z` are immutable array copies/views
with shapes defined above. Real resets remove prior physical support while
legitimate teleported/classical dependencies survive. Final physical support is
not hidden simulator truth or a decoder correctness score.

Apply caller-selected CorrectionBatch once per boundary. Optional use/input labels
validate exact epoch/XZ order; omission uses the declared plan order. Shape, source,
unknown/duplicate boundary, use or ordering errors are rejected. Follow
StageRequests.order so later inference sees all previous hypotheses; apply does
not enforce this causal inference policy itself. Later readout hypotheses update
provisional Bell feedback by XOR delta exactly once. `batch.events(view)` always
recomputes from current records; it never resamples or edits physical measurements.
A marginal physical DEM does not become a posterior model merely because the
records were reframed.

This identity hypothesis illustrates ordering, continuing the preceding memory
blocks. It is not a decoder or a noisy recovery claim:

```python
import numpy as np
from logical_to_stim_converter.decoding import CorrectionBatch

plan = compiled.make_frame_plan()
batch = plan.start(raw, source_fingerprint=plan.source_fingerprint)
boundary = plan.boundary_by_id[request.module_id]
correction = CorrectionBatch(
    plan.source_fingerprint, boundary.boundary_id,
    np.zeros((len(raw), len(boundary.input_ids)), dtype=bool),
    block_use_id=boundary.block_use_id, input_ids=boundary.input_ids,
)
batch.apply(correction)
assert np.array_equal(batch.raw_measurements, raw)
assert batch.events(view).shape == (len(raw), len(view.detectors))
```

The alternative per-shot physical-frame replay/strict validation helpers are
specified under [protocol metadata](#measurement-and-protocol-metadata).
[Frame source](../src/logical_to_stim_converter/decoding/frames.py),
[physical replay checks](../tests/test_knill_memory_offline_decoding.py),
[reused-epoch replay checks](../tests/test_patch_reuse_offline_replay.py).

## Conditional Bell fault actions

Import from `logical_to_stim_converter.decoding`:

```text
make_conditional_readout_model(compiled, bell: BellMeasurementResult) -> ConditionalReadoutModel
PauliFault(instruction_index: int, channel: str, exclusive_group: tuple[int, int],
           probability: float, paulis: tuple[tuple[int, str], ...],
           measurement_record: int | None = None)
```

Choose bell from `compiled.bell_measurements`; a foreign instance/use raises
DecoderViewError. The immutable model provides source fingerprint, composite/use
IDs, actual resource-entangling/output-preparation module IDs, half-open global
`start_instruction`/`end_instruction`, readable `boundary_convention`, ordered
`faults`, `readout_record_ids`, `output_data_ids` and GF2Maps below. Before reusing
a stored conditional model, compare its `source_fingerprint` with
`source_fingerprint(compiled)`; this data object has no automatic reuse validator.

The incoming hypothesis convention is immediately **before resource CNOT**, or,
with emitted M9 channels, immediately **before the earliest post-SE channel**.
The window ends after destructive Bell readout's physical idle/TICK accounting.
Intervening gates/idle faults are included. Earlier residual errors are represented
only by the external incoming sector/frame hypothesis, whose accuracy is not
asserted. Enabled nonzero widened windows crossing an intermediate preparation/SE
measurement on a Bell operand raise UnsupportedProjectionError. Canonical physical
compilation/global DEM still work. [M9 boundary ownership](resource_preparation_noise.md#boundary-provenance-and-offline-decoding)
prevents the same post-SE faults being assigned to both modular stages.

A PauliFault describes a nonidentity categorical atom at a global physical
instruction; `paulis` uses global wire indices, `measurement_record` is a global
reported-result flip when present. `exclusive_group=(instruction_index, offset)`
identifies mutually exclusive alternatives for one target/pair. DEPOLARIZE1 has
X/Y/Z atoms at p/3; DEPOLARIZE2 has 15 alternatives at p/15. Identity has the
remaining probability. Different groups are independent channel locations.
Do not treat same-group alternatives as independent Bernoulli mechanisms.

All model GF2Maps have input width `len(model.faults)`; supports describe joint
single-atom effects and XOR propagation of physically valid selected atoms:

| Map | Output order |
| --- | --- |
| `raw_flip_map` | `readout_record_ids`: X-readout records then Z-readout records |
| `output_x_map`, `output_z_map` | Survivor physical support in `output_data_ids` order, at this window's end |
| `x_syndrome_map` | Check rows of the X destructive readout |
| `z_syndrome_map` | Check rows of the Z destructive readout |
| `logical_flip_map` | Two raw logical parity flips: X-readout, then Z-readout |

For atom selections [S,F], each map returns bool [S,output_width]. They retain
correlated readout/check/logical/survivor actions. This is a categorical
fault-action distribution, **not** a deterministic Stim DEM for random Bell
outcomes. The returned model does not infer incoming sectors, select corrections,
run decoding or propagate corrections through the remainder of the program;
OfflineFramePlan supplies the latter linear propagation separately. Unsupported
physical noise/Clifford channels raise UnsupportedProjectionError.

This independent installed-API example constructs a noisy M9 model without an
optional decoder:

```python
from logical_to_stim_converter import (
    CircuitCompiler, CodeSpec, KnillEC, LogicalBlock, LogicalInit, LogicalMeasure,
    NoiseModel, ResourcePreparationNoise,
)
from logical_to_stim_converter.decoding import make_conditional_readout_model

code = CodeSpec.rotated_surface(3)
blocks = [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate("DAB")]
noise = NoiseModel(
    default=NoiseModel.uniform_depolarizing(.001).default,
    resource_preparation=ResourcePreparationNoise(True, .003),
)
knill = CircuitCompiler(blocks).compile([
    LogicalInit("D", "Z", rounds=3), KnillEC("D", "A", "B"), LogicalMeasure("D", "Z"),
], noise_model=noise)
model = make_conditional_readout_model(knill, knill.bell_measurements[0])
assert len(knill.resource_preparation_boundaries) == 2
assert model.raw_flip_map.input_size == len(model.faults)
knill.circuit.detector_error_model()
```

[Conditional source](../src/logical_to_stim_converter/decoding/conditional.py),
[atom physics checks](../tests/test_knill_memory_offline_decoding.py),
[M9 boundary/atom checks](../tests/test_resource_preparation_models.py).

## Exceptions and verification

All following offline errors are imported from `logical_to_stim_converter.decoding`
and derive from `DecoderViewError(ValueError)`:

| Type | When to handle it |
| --- | --- |
| `DecoderViewError` | Invalid metadata, selection, binary arrays, dimension/order/boundary contract |
| `SourceMismatchError` | Explicit fingerprint/model/plan mismatch; stale models must be regenerated |
| `UndefinedObservableError` | Requested random/unreliable logical readout has no deterministic label |
| `DEMConstructionError` | Exact Stim DEM extraction/decomposition fails; original reason is chained |
| `UnsupportedProjectionError` | Unsupported model source/approximation/channel or conditional interval |

These validate provenance and representability, not a decoder's statistical
correctness. Never recover from stale-source errors by silently substituting another
fingerprint. Source-less arrays remain the caller's provenance responsibility.

The [scope matrix](index.md#current-implementation-and-limitations),
[certification](lstim_certification.md), [architecture](architecture.md) and
[beta verification ledger](research_beta_0.0.1_plan_and_verification.md) state actual
bounded physics and installed-wheel evidence. External examples use optional
PyMatching/Matplotlib and restricted models; installed consumers supply their own
algorithms. The [ordinary memory](ordinary_memory_tutorial.md) and [Knill](knill_memory_tutorial.md)
tutorials exercise the installed contract. The
[Phase 5 gate](research_beta_0.0.1_plan_and_verification.md#phase-5--final-integration-gate-and-handoff-2026-11-09)
records final bounded verification and remaining legal/platform decisions.
P1's broader detailed single-fault worked guides remain separate work.
