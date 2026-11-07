# STATUS — Core

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
