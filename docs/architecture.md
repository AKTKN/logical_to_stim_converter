# Architecture and implemented memory contracts

**2026-11-07:** Rotated-surface memory and M3 multi-block H/CNOT/Pauli paths are
implemented. Broader logical compilation remains planned. See [repository status](../STATUS.md).

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
measured and cannot be reused. All registered blocks must complete. Readout must be deterministic under the intended logical Clifford circuit. Its basis
may differ from preparation after H. Random individual Bell readouts are rejected;
no fake deterministic observable is generated.

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

No dedicated Bell/Knill protocol class, decoder algorithm or adapter, text grammar/CLI,
other code-family backend, S/other logical Clifford gates, adaptive per-shot quantum
operations, general logical relocation, or LER benchmark is implemented. `knill_bench` remains
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
time for partial readout parallel to another block's H. An arbitrary random logical
readout raises an error. This supports the Bell prepare–SE–inverse circuit and
other deterministic X/Z Clifford outputs without a decoder.

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
