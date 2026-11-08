# STATUS — Operations

## M7-A update — 2026-11-08

binding.py adds public immutable BindPatch(logical_id, physical_block_id), a
zero-duration compiler directive separate from physical OperationModule builds.
It validates names and reserves an explicit patch; LogicalInit alone resets and
starts the occupancy. Primitive/composite physical implementations are unchanged.
Verified active/reserved/retired/unknown/conflicting binding rejection, zero gate/
record/TICK/noise effect, independent reuse and Knill relocation followed by fresh
resource bindings. Root STATUS records complete test/build/example/CI evidence.

## M5 update — 2026-11-07

BellStatePrep and KnillEC now implement CompositeOperation expansion into staged
verified primitives. Resource X/Z resets plus exactly d SE rounds run concurrently
by default; rounds may be overridden. Knill supports an existing Bell resource,
random X(D)/Z(A) readout, and a compiler relocation/frame contract. No physical
H/CNOT/SE/measurement implementation is duplicated. Child IDs, stage/parent IDs,
primitive type noise, and optional inherited instance overrides survive expansion.
LogicalMeasure defaults to deterministic and adds explicit mode="random".

Verified primitive-equivalent physical circuits, Bell physical XX/ZZ and random
singles, complete teleportation and random branches, explicit-correction tableau
references, parallel composites/spectators, exact once-only noise, and preserved
M1–M3 APIs. Root STATUS records final evidence. Decoder selection, adaptive
operations, and noisy logical-state recovery remain deferred.

## M3 update — 2026-11-07

M3: TransversalH, TransversalCNOT(control,target), and LogicalPauli(X/Y/Z,
physical/frame) are implemented. OperationModule.build accepts ordered operands
and immutable OperationContext, retaining the original single-block build form.
A CNOT is one two-block fragment; independent multi-target memory work remains
concurrent single-block fragments for compatibility. Physical and frame actions,
orientation changes, and noise provenance are explicit. Virtual Paulis emit no
physical step. BellStatePrep/KnillEC classes remain unimplemented; the Bell example
uses primitives directly, as required.

Evidence: the extended 173-test suite, Ruff, and both examples; exact final
commands/results are in root STATUS. Dependencies remain pinned to Stim 1.15.0
and stimflow commit ffe0d043598ed5df0851a3e6b4920359a23fafbd. External
source trees are unchanged.

## Prior memory implementation record

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
