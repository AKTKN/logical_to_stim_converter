# STATUS — Core

## Transversal Pauli backend contract — 2026-11-11

CodeBackend adds optional transversal_pauli with explicit unsupported-backend
rejection; mathematical code/layout/context contracts remain unchanged. The
rotated backend supplies signed-flow physics tests. Root STATUS records evidence.


## M7-B update — 2026-11-08

DetectorInfo adds anchor_use_id/source_use_ids, distinct from physical sites and
coordinates. TimeLayer adds immutable active_use_ids with one use per active
physical block. CompilerContext stores check sectors and round counts by use.
PhysicalPauliFrame identifies its target use independently of historical sources;
preparation resolve/unresolved APIs preserve it. PreparationDependencyEvent adds
input/output use edges. Compiler artifacts retain immutable per-use ancestry.
All touched APIs/helpers were reviewed for accurate English documentation.

Verified at d=3/5: three independent mixed-basis signed memories, unique raw
history, canonical detector/use provenance, H/reset orientation boundaries,
actual relocated ancestry, frame resets and stale-use rejection. Existing APIs
retain their default constructor fields; root STATUS records final full checks.

## M7-A update — 2026-11-08

lifecycle.py adds immutable BlockUseId, BlockUseInfo, PatchBindingEvent and
UseOwnerEvent. MeasurementKey adds a backward-compatible trailing epoch=0.
CompilerContext accepts partial explicit initial reservations, validates retired
aliases, reserves specified free patches atomically, starts epochs only at reset,
and reuses retired tableau slots within a fixed physical-patch-sized capacity.
Measured status is historical until a binding reserves the patch as uninitialized.
Preparation/readout/observable/fragment/Bell/relocation metadata carries use IDs;
physical site and Stim wire identities remain unchanged. Docstrings reviewed for
all public objects and significant helpers in touched source modules.

Verified: d=3/5 X/Z both signed bits, physical/virtual Paulis, exact per-use rounds
and raw indices, independent observable history, malformed/overlapping/reserved/
retired bindings, reset flow rejection, spectator isolation, open Knill relocation
and fresh preparation, and 13 consecutive uses in one tableau slot. Focused reuse
plus old Knill suite: 77 passed. Root STATUS records final complete checks.
Epoch-aware decoder policies and repeated three-patch Knill decoding remain
M7-B/M7-C work; no allocator or decoder is introduced.

## M6-B update — 2026-11-08

DetectorInfo adds actual physical check basis at its semantic anchor and stable
physical data support underlying all contributing syndrome/data records. H-induced
basis changes and cross-block support are explicit, with no check-prefix inference.
Compiler validation checks these fields against layouts and orientation metadata;
negative basis/support tests reject corrupted provenance. No flow/frame algebra
or physical gate/noise behavior changes. Exact verification is in root STATUS.

## M6-A update — 2026-11-08

DetectorInfo now carries a stable global index, an explicit anchor module/stage,
all ordered source stages, and a proposed-boundary marker. protocol.py adds typed
PreparationDependencyEvent edges and DetectorBoundaryCandidate (with the M5
SuppressedDetector import alias). PreparationInfo.resolve wraps a well-formed
external hypothesis; exact final-sector/logical-eigenvalue truth is a separate
strict validation mode. Physical commutation metadata is checked against support.
Existing CompilerContext affine frame algebra/provenance behavior is retained.

Verified by the focused causal/global/frame suite: independent spectators and
parallel gadgets, actual CNOT and d=3/5 reference history, pre-existing resources,
extra SE, repeated relocation, exact global record/stage attribution, malformed
edges/records/stages/signs, and noisy hypotheses. Full checks are in root STATUS.
No decoder, correction selector, adaptive operation or block reuse was introduced.

## M5 update — 2026-11-07

`protocol.py` adds preparation/check histories, physical Pauli corrections with
explicit resolution status, semantic random readouts, Bell results/dependencies,
composite contracts, detector suppression provenance, and relocation records.
Physical vectors are separate from affine logical frames. Context retains
historical readout blocks/modes, source gauge keys, and stable logical simulator
slots while current logical-to-block ownership changes during Knill teleportation.
ModuleFragment retains stage/composite IDs and readout mode.

Verified: d=3/5 nonzero preparation sectors, CSS correction equations, all four
input states, encoded reference entanglement, rotated-code pairings, relocation,
continued gates, and negative correction/mapping/orientation tests. Full check
counts/results are in root STATUS. No correction selector or production decoder.

## M3 update — 2026-11-07

M3: code_frame.py adds fixed-site coordinate frames and signed Stim Pauli
conjugation. OperationContext and tuple-based ModuleFragment identities support
ordered multi-block operands, separate physical target/interface support, code
orientations, actions, and provenance; scalar memory accessors/build remain.
CompilerContext stages updates atomically, tracks affine PauliFrame/ParityExpression
values and check-sector keys, validates logical determinism via Stim, and exports
code-frame/readout metadata. DetectorInfo adds all supporting blocks; ObservableInfo
adds canonical readout indices, frame correction, and expected ideal value.
Logical/physical IDs stay separate. Teleportation/relocation/decoder corrections
remain deferred.

Evidence: the extended 173-test suite, Ruff, and both examples; exact final
commands/results are in root STATUS. Dependencies remain pinned to Stim 1.15.0
and stimflow commit ffe0d043598ed5df0851a3e6b4920359a23fafbd. External
source trees are unchanged.

## Prior memory implementation record

**2026-11-07: memory foundation implemented and locally verified.**

- `code_spec.py`: immutable binary CSS matrices, GF(2) rank checks, stabilizer/logical
  commutation and pairing, odd-distance rotated-surface factory. General distance
  remains a declared parameter; no general distance solver is claimed.
- `physical_layout.py`: data/check identities, geometry, connectivity, explicit
  mathematical-column mapping, independent check support validation, N/Z layers,
  and same-layer collision rejection.
- `logical_block.py`: stable block and global site identities, explicit placement,
  local/global mapping, and separated equal-distance patch placement.
- `code_backend.py`: abstract memory backend contract and basis validation.
- `compiler_context.py`: per-compilation bindings/lifecycle, stable observable IDs,
  symbolic measurement keys, memory frame, detector/time-layer metadata.
- `module_fragment.py`: public stimflow chunk/loop wrapper with logical inputs and
  outputs, lifecycle/frame transition, operation/provenance IDs, and final records.

Evidence: code/layout, signed-flow, memory, and noise tests in `tests/`; see root
STATUS for exact commands/results. Invalid algebra/layouts, collisions, identity
confusion, and lifecycle misuse are rejected. Byte-backed matrices cannot be made
writable. Two/three patches retain correct indices after stimflow reindexing.

Deferred: general codes' physical backends, logical relocation, non-memory frame
propagation, decoder-dependent corrections, and physical block reuse.

History: 2026-11-07 began as docstring-only scaffolding; memory-core task adds the
first implementation. Next: separately scoped transversal-operation contracts.
