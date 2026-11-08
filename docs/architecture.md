# Architecture and implemented circuit contracts

**2026-11-08:** Rotated-surface memory, M3 H/CNOT/Pauli, M5 Bell/Knill
teleportation, and M6-A/B global detector/provenance and offline-view contracts are implemented.
M6-C/D demonstrate external ordinary/Knill memory decoding without a runtime decoder.
See [repository status](../STATUS.md).

## Implemented pipeline

`CodeSpec` + `PhysicalLayout` -> physical `LogicalBlock` instances -> Python
`LogicalInit` / `SyndromeExtraction` / `LogicalMeasure` -> `ModuleFragment` chunks
and loops -> physical-layer parallel adapter -> verified `stimflow.ChunkCompiler`
-> ideal circuit and final metadata -> `NoiseInjector` -> optional noisy circuit.
The caller samples the circuit and may later supply a decoder.

## Identity and data separation

`CodeSpec` is immutable mathematical CSS data: binary H_X/H_Z, L_X/L_Z, GF(2)
rank and symplectic-pairing validation, parameters, and string metadata. General
code distance is declared, not solved. The square odd-distance factory defines
[[d², 1, d]], with column-major data ordering, southern logical X, and western
logical Z. `PhysicalLayout` independently constructs/validates that convention,
with one ancilla per independent generator, connectivity, and N/Z CNOT order.

`LogicalBlock` scopes local D/X/Z keys to a stable physical block. Its global site
identity is `(block_id, local_key)`, and its geometry is an independent translated
coordinate. Stim indices are another mapping entirely. `CompilerContext` records
logical-ID-to-block bindings; live tableau slots are bounded by registered patches. Final exported
indices are recovered from the assembled circuit's QUBIT_COORDS, because stimflow
reorders qubits. Observable names are `(logical_id, basis)` until assembly; stable
final observable IDs follow sorted logical IDs, independent of block registration.

## Identity and lifecycle glossary (M7-A)

| Identity | Physical or semantic meaning |
| --- | --- |
| PhysicalBlockId (`str`) | Fixed placed patch: data/ancilla sites, layout and coordinates. |
| GlobalSiteId (`tuple[str, str]`) | Physical block plus local qubit key; stable across reuse. |
| Stim qubit index (`int`) | Final global wire index recovered after assembly; never an epoch. |
| BlockUseId | Immutable `(block_id, epoch)` for one reset-to-release occupancy. |
| epoch (`int >= 0`) | Per-patch occupancy generation, starting at the first actual reset. |
| LogicalStateId (`str`) | Persistent state identity through teleportation, or a fresh temporary resource name. |
| ModuleId (`str`) | Unique executed primitive, including its physical gates. |
| StageId (`str` or `None`) | Semantic protocol region, such as resource preparation or Bell readout. |
| TimeLayer | Physical interval between adjacent TICKs, with a zero-based index. |
| MeasurementKey | Physical block, local qubit, kind, per-use check round and trailing epoch. |
| Stim measurement index (`int`) | Absolute zero-based physical record position, increasing across all uses. |

`BindPatch(logical_id, physical_block_id)` is a compile-time reservation, separate
from OperationModule. It specifies exactly one patch and has zero duration/noise.
The initial injective mapping may reserve every patch as before, or a subset;
omitting the mapping retains block-named reservations. A pending reservation is
occupied for binding validation, although its physical status is UNINITIALIZED.
An unreserved patch is explicitly listed in `available_blocks`. After destructive
readout the final-use status remains MEASURED until a new binding reserves it.
Binding sets UNINITIALIZED without advancing epoch or creating a preparation.
Only the following LogicalInit resets data and advances that patch's epoch.

Retired aliases cannot execute, and retired names cannot be rebound. Historical
name-to-slot and readout dictionaries retain facts about prior measurements; they
do not confer permission to access a newly occupying state. Unrebound measured
aliases remain in the final mapping for compatibility. Rebinding removes the old
alias from that location map. Tableau capacity remains the registered patch count:
fresh aliases reuse retired internal slots and LogicalInit resets those slots.
The persistent data slot stays fixed during Knill relocation. Temporary A/B names
retire independently from physical release; B's active use acquires D as owner.

`block_uses` is an immutable tuple of BlockUseInfo, in reset execution order. Each
entry records reset/terminal ModuleIds, logical-owner events, and half-open global
measurement/TimeLayer intervals. Active uses have no terminal/stop fields.
Intervals describe positions in the full circuit and may include concurrent
spectator records. Preparations/readouts/fragments, observables and Bell/relocation
records retain explicit use identities. Every raw measurement keeps its producer
ModuleId and historical logical owner. Syndrome round counters restart per use;
physical site keys never change. Both deterministic readouts of a recycled site
remain distinct observables, canonically numbered by historical logical name.

Planning yields one user entry at a time and resolves composites using the
current mapping after earlier reservations/relocations. Parallel groups validate
physical operands before applying bindings, so bind/use/readout/reset overlap is
rejected even under different names. Independent bindings may share a user layer
with disjoint physical work and add no TICK or idle exposure. Physical flow ports
terminate at readout and restart at reset using public stimflow boundaries. The
global circuit retains all deterministic detectors, physical noise and raw order.
Independent metadata validation reconstructs use epochs and ownership from reset,
readout and relocation events rather than trusting final mappings.

M7-A proves sequential independent patch reuse and relocation/binding composition.
M7-B extends the decoder-neutral contracts below across these uses; production
allocation and the full M7-C three-patch Knill decoding demonstration remain separate.
Pinned stimflow `ChunkCompiler.o2i` assigns named observables by first encounter;
the compiler remaps their final Stim IDs to historical logical-name order after
lazy planning. Physical instructions and signed flow verification are unchanged.

## Use-aware models, timing and frame boundaries (M7-B)

DetectorInfo carries anchor_use_id and sorted source_use_ids in addition to
physical sites, module/stage IDs and raw parity. An anchor identifies the physical
check's reset interval; sources identify the uses that produced its raw records.
Neither is a coordinate. Compiler metadata validation checks these against actual
producer fragments. A physical reset terminates local flow ports; verified global
relations through interactions/teleportation remain, including legitimate earlier
use dependencies. No detector is deleted to establish decoder independence.

TimeLayer.active_use_ids is parallel to active_blocks, with at most one use for
each physical block. Eligibility starts at the data reset layer and includes the
terminal destructive-readout layer. Unused data and check ancillas receive one
effective idle channel per active use; measured/available/reserved gaps receive
none. NoiseInjector still runs after ideal signed-flow validation. Existing
primitive/global/instance precedence and composite-child ownership are unchanged.

PreparationDependencyEvent adds explicit input/output use tuples. The compiler's
immutable use_preparation_dependencies retains latest ancestry for each historical
use, while block_preparation_dependencies retains the compatibility latest-use
view. Per-use syndrome/round dictionaries prevent stale check values at reset.
Each LogicalInit creates only its own preparation source. Only actual operand
interactions and relocation union source histories; old logical information that
has already moved onto another use can legitimately survive the former site's reset.

DetectorSelector.use_ids accepts immutable BlockUseIds independently of physical
block and stage filters. Anchor, touching and strict membership respectively mean
the anchored use, any source use or all source uses. Physical-block filters span
all epochs. SelectionAudit records both requested_use_ids and retained
region_use_ids. Each view preserves every physical instruction/noise probability
and re-extracts its model with Stim, keeping excluded-region effects on retained
outputs, hyperedges and correlated components. Snapshot schema v3 fingerprints
include use histories, binding/owner events, Bell and ancestry snapshots and the
physical-time provenance. v1/v2 identities must be regenerated. Exact immutable
instruction snapshots remain in use, avoiding Windows floating-point text loss.

observable_local_views uses nodes per BlockUseId. Actual CNOTs, explicit relocation
and verified signed detector relations connect nodes; physical coordinate reuse
alone never adds an edge. Observable seeds include every contributing raw-record
use and the historical readout use. The resulting connected region is conservative;
region_selector remains a caller override, with no decoder prescribed.

BoundaryRequest.source_preparation identifies the reset of that boundary's use.
Its preparation field still means an optional prepared-logical prediction target
for LogicalInit; an ordinary SE request has none. CheckHistory, orientation,
last-record IDs and strict temporal detectors are module/use scoped. Model-only
ideal MPPs define last-noisy-record XOR actual-check targets; no probe or fault
truth enters canonical samples or normal decoder inputs. ReadoutRequest exposes
its source preparation and actual use. Signed sector transfer tracks a live bank
per use, through real H/CNOT pairings. Reset creates a new bank; expressions on
surviving other uses can still refer to earlier preparation sectors.

ConditionalReadoutModel resolves the Bell instance's exact output-use preparation
and actual resource-use CNOT, including pre-existing Bell resources. Public use,
module and window IDs make this auditable. Each categorical Pauli/result-error
atom retains its exclusive channel group, joint destructive-record/check/logical
effects and physical survivor X/Z support. This is a conditional fault-action
distribution under incoming hypotheses, not an unconditional deterministic Bell DEM.

FrameBoundary exposes its historical block_use_id. CorrectionBatch optionally
declares the use and input labels; explicitly wrong epochs, column order, source,
shape or shot count fail before state mutation. Omitting those two optional fields
retains the source/module-bound API with the plan's declared input order. Plans
contain every preparation/SE/readout module and no per-shot state. Applying
corrections edits only copies of classical records/residual frames, once per module.
Actual resets extinguish old physical supports; already measured Bell feedback
continues to the surviving data. StageRequests.order is offline causal boundary
order, never a gate schedule. events(view) recomputes current reference-relative
events after frame edits. Strict noiseless sector proofs remain independent from
acceptance of well-formed, potentially incorrect noisy decoder hypotheses.

The implementation adds no allocator, scheduler, decoder, sampling orchestrator
or adaptive quantum feedback. Full multi-cycle three-patch LER comparison belongs
to M7-C; generic conditional models do not promise optimal joint inference.

## Physical and flow boundaries

The backend builds resets, one six-layer SE cycle (ancilla reset, four CNOT
layers, ancilla measurement), and destructive data readout with public stimflow
APIs. X ancillas control data; Z ancillas are CNOT targets. The four directions
are X: NW/SW/NE/SE; Z: NW/NE/SW/SE. Boundary interactions are skipped in place.

Every cycle declares signed incoming and outgoing measurement flows for all
checks and signed preservation flows for both logical Paulis. Initialization and
readout use upstream transversal boundary mechanisms with signed verification.
Only same-basis initial checks are deterministic; opposite-basis outputs are
explicitly discarded at the boundary. The first SE round establishes their raw
syndrome sign references. Terminal same-basis checks close through data parity;
conjugate checks/logicals are explicitly discarded at destructive readout.

The wrapper adds module/operation IDs, logical input/output identity, block/frame
transition information, future stage provenance, and finalized measurement records.
It does not implement another stabilizer-flow engine. A memory frame has no
assumed logical correction; the first conjugate-basis syndrome keys are retained
as preparation-sector information. No decoder-dependent Pauli correction is made.

## Parallel assembly and time

Each explicit list/tuple of operations is a logical parallel layer/barrier.
Targets of a single operation are concurrent. Fragment loops are verified as
`ChunkLoop` objects, then expanded for assembly. For each corresponding physical
component, a small adapter aligns TICK-separated layers, remaps local measurements
in the flows to the woven record order, and combines disjoint chunks. Components
with fewer layers finish early; untouched live blocks receive identity flows.
Those pass-through flows use `center=None` so stimflow does not average a support
centroid into a boundary detector's location.

StimCircuitLoom was inspected: its matching-instruction-sequence requirement is
unsuitable for generic mixed-basis boundary chunks. The adapter handles physical
layer/measurement remapping only; stimflow composes the flows and emits every
DETECTOR/OBSERVABLE_INCLUDE. Missing flows and collisions raise errors.

This is a simple synchronous schedule, not a scheduling optimizer. Explicit
barriers are honored. Output circuits expand rounds instead of retaining REPEAT
blocks, so circuit/metadata size grows linearly with rounds. Large-round compression
and more general asynchronous scheduling remain future work.

## Metadata and lifecycle

Each compilation has fresh state. A physical use transitions uninitialized -> active ->
measured. A later explicit BindPatch reserves the same physical patch for a fresh
logical name; only its subsequent LogicalInit starts a new use. Closed compilation retains its completion
check; `allow_open_outputs=True` permits active outputs and unused blocks. Readout
defaults to deterministic under the intended logical Clifford circuit. Its basis
may differ from preparation after H. Explicit random readout produces classical
records and conditional state flows without a deterministic logical observable.

Compiled artifacts preserve ideal/noisy circuits, final physical indices, logical
bindings, absolute raw measurement indices with semantic keys and module/layer
provenance, detector parity records/check identity, observable parity records,
frames, final block status, fragment metadata, and physical time layers. No module
contracts contain hand-written rec[-k] offsets. The final metadata reader validates
all record indices, semantic anchors, and contributing blocks against causal
interactions. Independent memory detectors still have one supporting block.

## Noise

`NoiseModel` resolves instance > primitive type > global defaults for each channel.
An absent override inherits, while explicit zero replaces an inherited value.
`NoiseParameters.to_stimflow()` provides upstream NoiseModel/NoiseRule definitions:
anticommuting reset errors, one-/two-qubit Clifford depolarization, and reported-bit
measurement flips. Physical instruction tags carry module provenance through
assembly; default and overridden gate noise are applied only after ideal flow and
DEM verification. Already noisy input is rejected by the injector.

Global idle noise is computed once per physical layer on active unused sites.
Blocks become eligible on the initialization layer and retire after the destructive
measurement layer. Ancillas are included throughout that interval. A currently
operated block uses that primitive's effective idle rule; a live waiting block uses
the global default. Never-initialized and retired sites receive no idle errors.
Full stage-specific/nested-composite noise selection is deferred; fragments already
carry an optional stage field for a later additive interface extension.

## Deferred boundaries

No production decoder, text grammar/CLI, other code-family backend, S/other logical
Clifford gates, adaptive per-shot quantum operations, physical block reuse, or LER
benchmark is implemented. Relocation currently follows the Knill contract. `knill_bench` remains
a downstream experiment runner. This package never imports it.


## M3 code orientation and multi-block gate contract

Physical-site identity never changes. Code orientation is a binary classical
choice of stabilizer/logical representatives. H applies physical H on all data
and toggles 0 ↔ 1; it does not execute or silently assume a state permutation.
The orientation-1 canonical data template is rotated clockwise about `(d, d)`.
Its logical X is the physical western column; logical Z is the northern row.
Check ancillas keep their original site/check keys, with X/Z basis exchanged.
SE is the H conjugate of the original round, including the four physical edge
layers, reversed CX directions, and flipped ancilla reset/readout bases.

CNOT sends each canonical control data coordinate to the corresponding target
coordinate in the target frame. The physical pairing changes for unequal
orientations. The backend checks equal distance, standard local geometry,
disjoint sites, signed physical flows for every check and logical Pauli, and the
intended logical action modulo the output checks. Inter-block transversal links
are assumed available; hardware routing/SWAP synthesis is outside this model.

`ModuleFragment.logical_ids`/`block_ids` are ordered tuples; CNOT is one shared
fragment. `OperationContext` supplies immutable build orientation/provenance.
Independent multi-target operations retain concurrent one-block fragments for
memory compatibility. The legacy scalar build call and scalar identity accessors
remain valid for one-block fragments. Fragment identity/scope is checked against
its operands. Context updates are staged on a copied state, after verified build;
invalid operands do not partially change code frames, logical frames, or lifecycle.

## Correlated checks and logical-state flow ports

Gate check flows are exact Stim conjugations of input generators. After CNOT,
ChunkReflow reconstructs the canonical per-block generator basis from correlated
products. No required check or random initial sector is discarded to make a gate
compose. Reflow products are verified with public stimflow APIs.

The compiler transports a complete **known logical-state generator basis** jointly
across blocks. It does not replace an entangled state with independently known local
Paulis. These state ports remain unnamed until deterministic local readout so
internal correlations do not become spurious observable IDs. Each primitive is
separately verified against both logical Pauli actions before the assembly adapter
selects the prepared-state flow basis. Public Stim conjugation and stimflow
ChunkReflow/ChunkCompiler perform the algebra; there is no second physical flow engine.

At readout, a verified reflow expresses local output logical representatives and
the remaining state's generator basis in terms of the incoming state/check ports.
Stim logical tableaus validate deterministic intended readout and follow component
time for partial readout parallel to another block's H. The default readout mode
still rejects a random logical value. Explicit random readout uses the conditional
state procedure below. Deterministic X/Z Clifford outputs retain signed parity proofs.

Reflow fusion may average detector coordinates. Semantic anchor flags therefore
carry sequence/check identity through flows, and a ChunkCompiler metadata callback
labels the completed detector. `DetectorInfo` exports anchor and all supporting
record blocks. Indices, anchor registration, and support within the causal CNOT
interaction component are checked; neither a coordinate centroid nor an anchor
alone defines a decoder region.

## Affine frames, signs, and measurement interpretation

The logical Pauli frame is affine over symbolic MeasurementKeys, not numerical
shot guesses. H exchanges X/Z frame coordinates; CNOT uses the binary symplectic
rules. A representative change under H can multiply a logical observable by check
operators. Their measured sector parities are included in the frame using verified
reflow identities. Initial preparation-sector provenance remains available.

Physical Pauli execution changes the physical circuit and intended logical state.
Virtual Pauli execution changes the intended state and affine frame only; it has
no physical duration or noise location. Physical Paulis use the same one-qubit
Clifford depolarization convention as H, once per executed physical gate.

A terminal observable combines canonical raw data parity with the symbolic frame
terms. A structured OBSERVABLE_INCLUDE update adds any classical parity difference
to the stimflow transport observable. A **signed Stim flow proof** independently
checks this final parity against the intended logical output; deterministic DEM
construction alone is not used as a sign proof. Affine constants remain in metadata
and do not affect DEM fault correlations. `interpreted_measurements(raw)` evaluates
the exact affine output; bare Stim observable parity differs by its frame constant.
No decoder-dependent correction or adaptive physical operation is introduced.

## M5 composite and relocation boundaries

`CompositeOperation.expand` returns staged primitive layers. The plan retains
hierarchical operation IDs, primitive type/instance noise, all parent composite
IDs, and stage IDs. `BellStatePrep` resets A in X and B in Z concurrently, executes
exactly d SE rounds on each by default, then CNOT A→B. `KnillEC` optionally builds
this resource, executes CNOT D→A and concurrent X(D)/Z(A) destructive readout,
then applies a semantic relocation boundary. Existing Bell resources must have
intended XX=ZZ=+1; code compatibility and lifecycle are validated.

The logical identity D persists at B. Physical D and A retire; the resource
identities A/B leave the binding map. Historical fragment/record IDs do not change.
`RelocationRecord` retains source/output blocks and retired identities. The ideal
logical-state oracle reverses only the internal Bell-measurement CX to describe
the intended identity channel, preserving unrelated parallel computation and
reference entanglement. Actual physical flow ports follow the measured branch;
their surviving B slot is renamed to D. The oracle is not a physics proof: signed
physical flows, check equations, and independent tableau tests supply that proof.

## Conditional measurements and partial artifacts

Random readout first projects a logical tableau to choose a surviving conditional
generator basis. Public `ChunkReflow.from_auto_rewrite` expresses these outputs
using the old known-state ports, checks, and measured logical representatives.
The generator change is completed to a square invertible basis. Measurement-
destroyed generators are explicitly consumed as discarded inputs of the physical
readout chunk; surviving conditional generators become signed measurement-
mediated physical flows solved by `Stim.solve_flow_measurements` and verified
by `has_flow`/`Chunk.verify`. No random local named observable is created.

Open compilation preserves `cur_end_interface()` in the artifact. A copy of the
verified compiler is projected for faithful physical export using a zero-operation
chunk with discarded frontier inputs. The original frontier remains exported;
the projection is not a physical state termination. There is no magical MPP end
chunk, extra measurement, or quantum feedback. `CompiledCircuit.append` recompiles
the prefix and continuation, retaining complete verification and stable sites.

Pinned stimflow at `ffe0d043598ed5df0851a3e6b4920359a23fafbd` requires equal
numbers of reflow inputs/outputs, including discarded inputs. Its nonsquare
`ChunkReflow.verify` diagnostic also unpacks PauliMap keys incorrectly. This code
does not use nonsquare reflows or patch upstream; physical measurement discards
and explicit export projection use supported Chunk boundaries. Stim 1.15.0 supplies
signed flow solving and tableau projection. Dependency pins remain unchanged.

## Physical preparation-sector frame evaluation

`PreparationInfo` records physical data order, actual check bases/supports, full
measurement histories, gauge keys, and final syndrome keys. A `PhysicalPauliFrame`
is separate from the affine logical `PauliFrame`: it carries stable physical
X/Z supports, orientation, source module/stage, resolution state, and logical
commutation contribution. None supports mean unresolved; empty supports mean
a selected identity. The package does not select corrections.

An external correction result enters through `PreparationInfo.resolve` and
`CompiledCircuit.evaluate_frames`. The backwards-compatible default
`validation="noiseless"` verifies H_X z=s_X, H_Z x=s_Z against actual semantic
raw records and checks preservation of the prepared logical eigenvalue.
`validate_noiseless_preparation_corrections` makes that proof explicit without
frame replay. `validation="hypothesis"` instead accepts noisy externally selected
physical frames after checking binary shape, identity, orientation, source
boundary, known data IDs and logical commutation metadata. It does not compare
to a raw-sector oracle or assume decoder success; a faulty final check need not
agree with the hypothesis. Logical eigenvalue preservation is a noiseless proof,
not a general restriction on decoder hypotheses. Both modes replay binary Pauli
vectors through the actual woven physical instruction pairings, including H, CX,
resets, and ancilla readout.
Measurement anticommutation flips are applied once. Virtual logical Paulis are
inserted at their explicit zero-duration evaluation boundary. Bell X/Z parities
are computed from the interpreted records, and their X^mZ Z^mX byproduct enters
the output physical frame. Subsequent gates update that residual frame.

`BellMeasurementResult` exposes raw readouts, check-matrix mappings, raw logical
parities, incoming frame/dependencies, affine byproduct/output frame, and unresolved
physical output frame. `FrameEvaluation` exposes evaluated Bell outcomes,
byproducts, corrected records, logical readout values, and resolved open frames.
The original circuit never contains these selected corrections. The ordinary
affine transport observable remains independently signed and DEM-validated, but
the public Knill interpretation API requires explicit physical corrections.

PyMatching 2.3.1 is mandatory only in the development extra and CI tests. The
test helper constructs Matching(H_Z) for x and Matching(H_X) for z, validates
matrix-column order/vector length/check equations, and uses final noiseless
syndromes from metadata. It performs no temporal or circuit-level inference.
Tests compare frame-only physical expectations with a separate simulator that
actually applies corrections and executes compatible projective measurements.

## Canonical global detectors and explicit annotation views (M6-A)

All global check and conditional logical flows compose with pinned stimflow before
noise insertion. The principal ideal/noisy circuits retain every deterministic
flow-derived detector, including cross-block and cross-stage relations; both pass
Stim DEM validation. No physical measurement is added to close an open artifact.
Random Bell singles and sector-valued one-shot Bell checks remain raw metadata.

`DetectorInfo.index` is the zero-based canonical global detector ID. It retains
exact global raw-record parity, semantic keys, supporting blocks and `(x, y, t)`
coordinates. Flow anchor flags carry the latest semantic check's module/block/
check IDs through composition into an instruction tag, without extra coordinate
dimensions. `stage_id` comes from that anchor's module; `source_stage_ids` retains
all record stages, ordered with None first then lexically. More than one source
stage marks `crosses_decoder_boundary`; it does not invalidate the physical parity.
Measurements and observables likewise retain canonical IDs and full raw parities.
`measurement_index_by_key` reverses the stable semantic record mapping.

`stage_separated_circuit(noisy=...)` returns an explicit legacy annotation view;
only cross-stage DETECTOR instructions are omitted. Physical gates, quantum
measurements, noise, coordinates and observable annotations are identical.
`stage_separated_detector_indices` maps its detector IDs to global IDs.
`detector_boundary_candidates` stores each crossing global detector's ID, parity
and stages. The M5 `suppressed_detectors` name is a read-only alias to these present
relations. The private `separate_detector_regions` helper remains available for
explicit legacy calls; compilation never calls it or the stage-only validator.
This migration intentionally increases Knill detector counts. M3 un-staged
correlations remain unchanged. This view neither slices faults nor establishes
independent stage DEMs. M6-B provides explicit physical-model marginal views below.

`validate_metadata` checks the annotation reader against the canonical circuit,
physical site/record order, fragment modules and stages, exact detector/observable
indices, coordinates and boundary candidates. It also checks causal event edges.

## Causal preparation ancestry

Each LogicalInit creates a PreparationInfo event with stable module, logical and
physical block identities, stage, basis, full check histories and physical frame.
ProtocolAssembly tracks histories per physical use while primitive fragments
are built. Local operations retain their operand history. A physical transversal
CNOT conservatively unions the two actual operand histories onto both outputs;
it does not bring in unrelated earlier or parallel preparations. A destructive
readout records consumption without creating a new preparation source. Historical
block ancestry remains available for auditing; a new reset replaces the current
patch ancestry while preserving historical preparation events and use records.

Knill relocation unions the data and relevant resource histories onto the surviving
physical block and persistent logical identity. Resource logical identities leave
the binding map, while their preparation events remain legitimate historical
sources. Reference/input interaction history survives; independent spectators and
parallel gadgets never enter this union. Pre-existing resources and repeated
relocations follow the same event rule.

PreparationDependencyEvent records primitive and relocation input/output block
edges and resulting preparation-module dependencies. Final
`preparation_dependencies` covers initialized, currently bound logical identities
(including measured outputs); `use_preparation_dependencies` retains use history,
and `block_preparation_dependencies` is its compatibility latest-use view.
Bell results snapshot dependencies at their own relocation boundary. Unresolved
and evaluated physical frames list precisely those source preparations' final
syndrome keys; affine frame provenance lists their gauge keys. Final open frames
use the final causal history, not all preparations in the program. Per-shot Pauli
supports continue through the existing physical symplectic replay independently
of these source lists. Ancestry never supplies a correction value.

No runtime decoder, adaptive branch, independent stage DEM or batch decoder
adapter is introduced. See [deferred work](deferred_work.md).

## Offline model and record views (M6-B)

`decoding` owns immutable `DecoderView`, `IndexMap`, `DEMOptions`,
`DetectorSelector`, `SelectionAudit`, `DecoderInputs`, `GF2Map`, and `RecordFlipMap`.
It contains no decoder algorithm. `CompiledCircuit.make_decoder_view` delegates to
this public namespace without exposing compiler/evaluation internals. Principal
circuits remain canonical full circuits.

The view validates global indices, record keys/parities, coordinates, physical
support and source annotation agreement against public artifact metadata. A SHA256
content fingerprint covers the ideal and physical circuits, Stim version, schema
version and relevant metadata, including semantic operation/relocation history.
No per-shot state is retained. Source/derived circuits and DEMs use immutable exact instruction
snapshots; properties materialize copies through public Stim append APIs. Text
roundtrips are avoided: Stim 1.15 circuit text rounds arguments, and its Windows
DEM printer can round double probabilities. Schema v3 fingerprints include exact
circuit arguments and use provenance; regenerate v1/v2 fingerprints. Tags, targets, shifts, repeat
structure and correlated separators survive copying. Input arrays can optionally carry a
separately stored fingerprint; their width alone cannot prove provenance.

`DetectorInfo.basis` records the actual physical check basis at its anchor module,
including orientation changes. `physical_support` unions stable data sites of all
underlying ancilla checks and raw data readouts; it does not collapse cross-block
correlations into the anchor's scope. Compiler validation independently checks
these against layouts/orientations. Selector callbacks use these public fields.
Block and stage membership have explicit anchor/touching/strict semantics. A
selector combines fields by intersection, supports unions, and preserves canonical
order; explicit ID lists instead preserve caller order. Every view exposes exact
bidirectional detector/observable/record maps with contiguous local IDs. Random
Bell readouts are raw metadata, never reliable observable selectors.

The default cross-region policy retains selected crossings. Omit explicitly drops
any detector spanning multiple physical uses/blocks or source stages. Joint retains
selected crossings with an auditable combined scope. These policies select
annotations; they neither delete faults nor assert statistical independence.
Observable-local default regions are conservative connected components of actual
CNOT/relocation/check-flow history between uses, seeded by the readout use and raw observable parity.
A user region-selector callback may replace this choice. This supports the style
of observable-local subgraphs without prescribing lomatching or another decoder.

The derived circuit copies every physical instruction/noise channel. Repeat
occurrences are expanded while preserving SHIFT_COORDS and TICKs. Selected
OBSERVABLE_INCLUDE instructions stay at their original positions with remapped
IDs. All selected detectors are emitted at the end in requested local order,
using global record supports converted to end-relative offsets, original tags,
and coordinates translated through the retained final coordinate shift. No
quantum gate, raw measurement or boundary relation is synthesized. This ordering
allows arbitrary detector permutations even when records were produced at very
different times. Physical timing and absolute detector coordinates are unchanged.

Stim 1.15.0 re-extracts the selected DEM from the physical circuit. A physical
fault affecting kept and excluded detectors survives on its retained support.
Default extraction preserves hyperedges; requested decomposition keeps Stim's
correlated ^ semantics. There is no direct DEM projection path, probability
compression engine, gauge elimination or disjoint-error approximation. Unsupported
exact extraction/decomposition raises a typed DEMConstructionError carrying Stim's
reason, rather than silently claiming MWPM compatibility. DEM repeat/shift
handling and optional flattening are delegated to Stim.

Sparse GF2Map multiplication uses uint8 arithmetic reduced modulo two; overflow
by 256 preserves parity. Public incidence matrices are copies. The reference raw
sample comes from the same physical circuit's noiseless reference sample. Selected
detector/observable parity offsets therefore match compile_m2d_converter, including
nonzero deterministic signs. An override reference is accepted only if its
selected deterministic parities agree. Projecting stored events is appropriate
for unedited samples; edited records require parity recomputation or incidence-map
XOR updates. GF2Map and RecordFlipMap operate on entire batches without per-shot
Python loops. All raw/mask inputs remain unchanged.

RecordFlipMap accepts caller-defined correction bits and their linear effects on
future global records. It verifies source identity and bit/shot dimensions, not
whether a decoder chose a correct correction. Automatic Pauli-to-record maps,
conditional Bell checks, noisy preparation decoding and LER demonstrations remain
separate work. A selected DEM is a physical marginal; using it after a conditional
record-frame update may require a later decoder-specific conditional model.

Reference inspections: lomatching b55a7a65969a106a547622287b620f0da2cb5e39 uses
observable observing regions plus physical-circuit annotation selection and DEM
re-extraction. surface-sim 493f800a3b4e9f80a6a569eb92d3c962dd6b09ad separates
semantic ancilla/check identity, basis and detector history. Hex
5de58f2f80791054411ad3c0885a4fe3671ed56a separates correction-to-measurement maps
from static sampling. These informed the boundary, not runtime imports or copied
integration code. Stim/stimflow pins are unchanged.


## External ordinary-memory decoding example (M6-C)

`examples/memory_offline_decoding.py` is an external consumer of public compiler,
view and metadata APIs. It samples one full raw batch per experiment, uses Stim's
m2d conversion for reference-relative event/observable labels, and compares full,
observable-local and strict patch views without resampling. Concurrent mixed X/Z
patches have nontrivial global/local observable remapping. The package owns no
PyMatching types, Monte Carlo framework, LER aggregator or plotting dependency.

The example retains the canonical undecomposed global DEM. Derived views request
Stim decomposition, and an adapter rejects remaining hyperedges before PyMatching
could ignore them. Two-pass correlated MWPM uses retained ^ correlations
heuristically; it does not promise exact maximum-likelihood decoding. Logical
failure is predicted XOR actual reference-relative observable flip. Raw readout
parity, full affine interpretation and intended eigenvalue are independently
checked, including -1 and virtual/physical Pauli cases. Results are scoped per
view, with an any-observable shot count and separate per-observable counts.

PyMatching and Matplotlib belong to the development extra/example only. JSON/CSV
summaries and PNG/SVG figures are small demonstration outputs, not a persistent
sample format. M6-D below adds a restricted conditional modular baseline; production recovery
and conditional joint inference remain deferred.


## Typed stages and static batch frame propagation (M6-D)

The compiler's make_frame_plan method reads verified physical assembly steps once.
A basis batch represents each raw record, each preparation/SE physical X/Z input,
each destructive-readout record correction and an affine constant. It propagates
through actual ideal H/CX/reset/measurement instructions, virtual logical Paulis
and causal Bell feedback, then freezes sparse GF2Maps. This setup uses no samples,
noise oracle or decoder. Runtime cost is sparse batched GF(2) application rather
than a Python loop over shots. Open final physical X/Z maps support tableau proofs.

OfflineFrameBatch is explicitly caller-owned mutable analysis state. Stored raw
records are immutable. A CorrectionBatch must match source fingerprint, boundary
ID, binary dimensions and shot count. Applying a boundary twice is rejected.
Provisional Bell feedback can be computed up front because the transform is
causally triangular: a later readout correction adds exactly its feedback delta
to future records/frames. No physical feed-forward or resampling occurs. Requests
are decoded in StageRequests.order; current events are recomputed from interpreted
records and their declared reference convention.

Public decoding/stages.py exports StageInputs/StageResult/StageDecoder plus
BoundaryRequest/ReadoutRequest. Boundary target models copy the physical noisy
prefix, retaining strict stage-local detectors, and add ideal model-only MPPs.
Their observables are last-record XOR true boundary check, and the known prepared
logical error where appropriate. Probes are not canonical measurements, not input
to the decoder and not inferred by treating random gauges as deterministic.
The example first estimates these targets temporally, then solves CSS sector
representatives with the appropriate prepared-logical constraint. These physical
vectors enter the verified correction maps; logical flips alone are not physical
corrections. Strict M5 noiseless-sector proofs remain separate from hypotheses.

Signed Pauli support elimination transports predicted boundary sectors through
actual transversal unitaries. Readout requests retain physical orientation, raw
record ordering and logical representatives; synthetic readout syndromes subtract
predicted sectors offline. An exact conditional fault-action model retains all
Pauli atoms of standard independent/depolarizing/measurement channels between
resource CNOT and Bell readout, their exclusive groups, joint destructive record
and logical/check effects, and survivor X/Z support. No synthetic raw Bell detector
is added to the global circuit. Unsupported channels fail explicitly.

The reference consumer is deliberately restricted. Temporal MWPM may choose an
ambiguous parallel-edge representative; unit-weight per-patch capacity Bell
matching ignores correlated joint inference. Strict ordinary-SE windows exclude
cross-boundary reference offsets; one-round windows have no temporal information.
Earlier decoder errors are not assumed absent in the honest final LER label.
Canonical full DEMs/correlations remain available for alternative joint consumers.
No decoder algorithm, LER runner or plotting import enters runtime package code.
Exclusive wall times distinguish one-time validated compilation/maps/models from
raw sampling, m2d, batch decoding and record/frame transformations.
