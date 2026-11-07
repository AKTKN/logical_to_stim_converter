# STATUS — Operations

**2026-11-07: three memory primitives implemented and verified.**

- `base.py`: abstract OperationModule with validated logical target IDs,
  optional operation identity and instance noise override, and fragment build API.
- `initialization.py`: LogicalInit(X/Z, explicit rounds >=1), with an upstream
  transversal reset boundary followed by a verified ChunkLoop of SE rounds.
- `syndrome_extraction.py`: positive round count, full stabilizer and both logical
  Pauli flows, verified ChunkLoop representation and memory-frame preservation.
- `measurement.py`: destructive same-basis memory readout with terminal parity
  flows and lifecycle termination. Compiler assigns final observable IDs.

Evidence: signed primitive-flow verification, independent ideal raw-record and
observable parity checks, random preparation-syndrome rejection as detectors,
parallel/mixed-basis memories, lifecycle and argument rejection, and override
noise-location tests. See root STATUS for executed checks.

Transversal, Pauli, Bell, and Knill modules remain unimplemented placeholders.
Their docstrings were wrapped to resolve existing Ruff E501 findings. No decoder,
postselection, grammar, or dedicated memory-experiment class was introduced.

History: 2026-11-07 scaffold -> memory primitives. Next: a separate Clifford task.
