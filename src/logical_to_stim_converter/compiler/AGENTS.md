# AGENTS.md — `compiler`

Scope: `src/logical_to_stim_converter/compiler/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Assemble ideal logical operation fragments into physical Stim circuits and metadata.

- Use stimflow.ChunkCompiler for compatible flow composition/detector generation.
- Represent simultaneous operations as truly concurrent physical layers; do not equate logical layers with TICK.
- Preserve symbolic measurement/observable IDs and logical-location history for later decoding.

## Files and intended responsibilities

- `circuit_compiler.py` — **CircuitCompiler, CompiledCircuit**: Planned fragment ordering, parallel-layer handling, assembled ideal/noisy Stim circuits and stable decoder-facing metadata.

The memory/Clifford compiler and private logical-port, parallel, and metadata adapters are implemented. Preserve explicit logical barriers and reject physical collisions or unmatched flows. Update this folder's `STATUS.md` and root status after changes.

M3: preserve all check correlations through ChunkReflow and transport a complete known logical-state port basis in `_logical.py`. Frame-corrected readout requires a signed physical Stim proof. A detector anchor is not its decoder scope: validate and export every contributing block.

M5: `_plan.py` retains composite child identity and parallel stages; `_teleport.py`
handles semantic relocation. Random readout consumes only measurement-destroyed
ports and retains signed conditional outputs. Open export retains the verified
frontier, with no magical terminal measurements. `_frames.py` propagates externally
resolved physical vectors; it must not select corrections or import a decoder.
M6-A: preserve the complete flow-derived detector circuit in the principal
ideal/noisy properties. Stage separation is an explicitly requested derived view,
with global detector IDs retained in metadata. `_provenance.py` checks exact raw
record/annotation mappings and causal event edges; validate these at compilation.
`_teleport.py` joins preparation ancestry at actual physical interactions and
relocation only. Frame replay accepts well-formed noisy hypotheses independently
from the explicit strict noiseless sector/eigenvalue validator.

M6-B exports actual detector basis and full underlying data support and validates
them against physical layouts/orientations. CompiledCircuit delegates offline view
construction to decoding; quantum assembly/noise remain independent of selectors.

M6-D: _frame_plan.py compiles exact physical Clifford and causal Bell feedback
into immutable sparse batch maps once. It may read private verified assembly;
external examples must use make_frame_plan instead. Keep per-shot state and
concrete decoders outside the compiler. Existing evaluate_frames and strict
noiseless validation remain independent regression references.
