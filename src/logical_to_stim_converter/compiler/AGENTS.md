# AGENTS.md — `compiler`

Scope: `src/logical_to_stim_converter/compiler/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Assemble ideal logical operation fragments into physical Stim circuits and metadata.

- Use stimflow.ChunkCompiler for compatible flow composition/detector generation.
- Represent simultaneous operations as truly concurrent physical layers; do not equate logical layers with TICK.
- Preserve symbolic measurement/observable IDs and logical-location history for later decoding.

## Files and intended responsibilities

- `circuit_compiler.py` — **CircuitCompiler, CompiledCircuit**: Planned fragment ordering, parallel-layer handling, assembled ideal/noisy Stim circuits and stable decoder-facing metadata.

The memory compiler/artifact and private parallel/metadata adapters are implemented. Preserve explicit logical barriers and reject physical collisions or unmatched flows. Update this folder's `STATUS.md` and root status after changes.
