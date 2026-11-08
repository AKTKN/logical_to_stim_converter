# AGENTS.md — `operations`

Scope: `src/logical_to_stim_converter/operations/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Abstract logical operation type, requested primitives, and composite Bell/Knill operations.

- Keep OperationModule subclasses independent of code family by delegating physical details to CodeBackend.
- Return verifiable ideal stimflow components and semantic metadata; do not hard-code a decoder.
- Keep time and noise context explicit; a composite must not inject noise twice.

## Files and intended responsibilities

- `base.py` — **OperationModule**: ABC and common build/validate contract; targets, operation ID, optional noise instance override.
- `initialization.py` — **LogicalInit**: Prepare |0_L> (Z) or |+_L> (X) using physical reset plus specified repeated SE rounds.
- `syndrome_extraction.py` — **SyndromeExtraction**: Generate a configurable number of SE rounds and associated flow boundaries; prefer stimflow.ChunkLoop.
- `transversal.py` — **TransversalH, TransversalCNOT**: Physical transversal gates, verified logical/stabilizer transforms, code-specific layout/basis effects.
- `pauli.py` — **LogicalPauli**: Logical Pauli operation, either physical gate realization or virtual logical Pauli-frame update.
- `measurement.py` — **LogicalMeasure**: Destructive X/Z readout and terminal flow/observable metadata; mark consumed block.
- `bell_preparation.py` — **BellStatePrep**: Concurrent X/Z resource resets and d SE rounds, then transversal CNOT.
- `knill_ec.py` — **KnillEC**: Composite resource preparation, random Bell readout, and a compiler relocation/frame contract; decoder-independent.
- `composite.py` — **CompositeOperation**: Expand into staged primitive layers; no second physical gadget implementation.

Memory, TransversalH/CNOT, and physical/virtual LogicalPauli operations are implemented and flow verified. BellStatePrep/KnillEC expand into staged verified primitives through CompositeOperation. They retain child provenance and never inject noise. LogicalMeasure has deterministic/random modes. Update this folder's `STATUS.md` and root status after changes.

Use ordered operands and OperationContext for multi-block builds. Preserve CNOT control/target order. Independent multi-target memory operations retain their compatibility decomposition. Virtual Paulis have zero physical duration.

M7-A: binding.py defines BindPatch as a zero-duration compiler directive, not an
OperationModule. It accepts a fresh logical ID and an explicit physical block ID;
the following LogicalInit supplies the physical reset and starts the use epoch.
