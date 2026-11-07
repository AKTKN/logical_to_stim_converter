# Architecture and implemented memory contracts

**2026-11-07:** The independent rotated-surface memory path is implemented. Broader
logical compilation remains planned. See [repository status](../STATUS.md).

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
measured and cannot be reused. All registered blocks must complete. Same-basis
preparation/readout is required for deterministic memory observables; unsupported
cross-basis readout is explicitly rejected.

Compiled artifacts preserve ideal/noisy circuits, final physical indices, logical
bindings, absolute raw measurement indices with semantic keys and module/layer
provenance, detector parity records/check identity, observable parity records,
frames, final block status, fragment metadata, and physical time layers. No module
contracts contain hand-written rec[-k] offsets. The final metadata reader validates
that detector records remain within their patch.

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

No transversal H/CNOT, logical Pauli, Bell/Knill protocol, decoder algorithm or
adapter, text grammar/CLI, other code-family backend, runtime per-shot frame,
general logical relocation, or LER benchmark is implemented. `knill_bench` remains
a downstream experiment runner. This package never imports it.
