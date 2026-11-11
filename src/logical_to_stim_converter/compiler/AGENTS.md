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

M7-A: _plan.py yields user entries lazily against the updated binding context.
BindPatch has no physical fragment/time. _provenance.py independently reconstructs
reset/release epochs and owner changes; observable history includes retired names.
Never infer that a bare physical block names one unique preparation/readout.

M7-B: detector anchors/source uses and active TimeLayer uses come from actual
physical fragments. Ancestry edges carry explicit input/output use IDs and retain
historical use dependencies. Frame plans label each module/use boundary; old
physical supports die at reset while earlier Bell feedback survives on real data.

M9: build resource-noise insertion plans only after ideal metadata validation.
Retain immutable use-aware boundaries/channel indices on CompiledCircuit and the
complete NoiseModel on continuation. Preserve the ideal circuit and existing
TICK/annotation ordering. ResourcePreparationNoise enforces [0,.75] for native
exact DEM compatibility. Validate the actual noisy circuit directly and propagate
Stim errors; never cap/reweight resource probabilities. Always pass an explicit
boundary tuple to NoiseInjector.apply, including () for resource-free programs.

terminal.py owns signed intended active-state snapshots and derived ideal terminal
MPP probes. Eliminate retired slots by signed stabilizer multiplication, preserve
Y=iXZ and explicitly invert MPP targets (Stim 1.15 drops PauliString append signs).
Probe frame evaluation must check source/raw alignment. export.py emits exact
JSON instruction arguments and public provenance. Post-init noise plans resolve
after ideal validation; preserve M9's sole structural Bell resolver.
