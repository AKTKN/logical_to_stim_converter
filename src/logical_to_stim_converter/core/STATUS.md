# STATUS — Core

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
