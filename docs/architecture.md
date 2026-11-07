# Architecture and implemented circuit contracts

**2026-11-07:** Rotated-surface memory, M3 H/CNOT/Pauli, and M5 Bell/Knill
teleportation paths are implemented. See [repository status](../STATUS.md).

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
logical-ID-to-block bindings; current memory is one slot per block. Final exported
indices are recovered from the assembled circuit's QUBIT_COORDS, because stimflow
reorders qubits. Observable names are `(logical_id, basis)` until assembly; stable
final observable IDs follow sorted logical IDs, independent of block registration.

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

Each compilation has fresh state. A block transitions uninitialized -> active ->
measured and cannot be reused. Closed memory compilation retains its completion
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
`CompiledCircuit.evaluate_frames`. Evaluation verifies H_X z=s_X, H_Z x=s_Z
against actual semantic raw records and checks preservation of the prepared
logical eigenvalue. It replays binary Pauli vectors through the actual woven
physical instruction pairings, including H, CX, resets, and ancilla readout.
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

## Physical flow verification and detector boundary policy

Hex reference commit `5de58f2f80791054411ad3c0885a4fe3671ed56a` separates
state-preparation modules/corrections from the Bell measurement correction map.
This implementation preserves that modular boundary without importing Hex.

All global check and conditional logical flows compose first, including valid
cross-stage history; the full circuit passes ordinary Stim DEM validation.
An explicit annotation policy then keeps a detector only when its source records
share a region. Knill resource A/B preparation stages are distinct even during
parallel reset/SE. Teleportation and subsequent stages are explicit. Excluded
cross-stage relations remain in `SuppressedDetector` with raw indices/stage IDs.
No raw record, physical gate, or required conditional output flow is removed.
The final stage validator rejects crossing annotations, and the resulting ideal
and noisy circuits both pass DEM construction.

One-shot Bell check parities depending on preparation sectors are exported as
raw readout syndrome metadata. There need not be teleportation-local detectors.
When all stages are absent, existing M3 cross-block detectors are retained.
This circuit-annotation boundary does not slice DEM mechanisms or establish
independent stage fault models. See [deferred work](deferred_work.md).
