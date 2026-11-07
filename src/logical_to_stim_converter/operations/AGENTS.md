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
- `bell_preparation.py` — planned **BellStatePrep**: Composite two-state preparation + H + transversal CNOT, or future alternative resource gadget.
- `knill_ec.py` — planned **KnillEC**: Composite Bell measurement, logical relocation D->B and symbolic correction/bell measurement metadata; decoder-independent.

Memory, TransversalH/CNOT, and physical/virtual LogicalPauli operations are implemented and flow verified. BellStatePrep/KnillEC remain placeholders. Update this folder's `STATUS.md` and root status after changes.

Use ordered operands and OperationContext for multi-block builds. Preserve CNOT control/target order. Independent multi-target memory operations retain their compatibility decomposition. Virtual Paulis have zero physical duration.
