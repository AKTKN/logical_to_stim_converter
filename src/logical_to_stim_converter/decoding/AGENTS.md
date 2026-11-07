# AGENTS.md — `decoding`

Scope: `src/logical_to_stim_converter/decoding/`. Root AGENTS and architecture apply.

## Responsibility

Provide decoder-neutral offline inputs/models over one canonical physical experiment.
No decoder algorithm, fitting, Monte Carlo runner, LER aggregation or sweep belongs
here; external consumers and knill_bench own those choices.

- views.py: immutable DecoderView snapshots, bidirectional IDs, content fingerprints,
  public-metadata validation, exact noise-preserving annotation selection and Stim
  DEM re-extraction, observable-local region example and batch input adapters.
- selectors.py: public semantic anchor/touching/strict block/stage/check selection.
- records.py: pure vectorized sparse GF(2) transforms and caller-defined record frames.
- errors.py: typed source/metadata/selection/DEM construction failures.
- frames.py: immutable correction/plan contracts and isolated caller-owned batch state.
- stages.py: typed requests/protocol, strict temporal model-only boundary probes,
  and signed conditional sector transfer from public physical metadata.
- conditional.py: exact Bell-interval Pauli atoms, exclusive groups and joint
  raw/survivor fault actions; not a shot-conditioned deterministic Stim DEM.
- interfaces.py: future production decoder contracts; the small StageDecoder
  protocol in stages.py supports replaceable external M6-D adapters.

Never remove a physical fault because it touches an excluded detector. Re-extract
from the unchanged physical gate/noise sequence; preserve hyperedges and correlated
^ components. Explicit DEMOptions must not silently enable approximations. Keep
random Bell records separate from reliable observables. View ordering is the
caller's explicit ID sequence or canonical order for semantic callbacks. Selection
audit and source fingerprint are authoritative; NumPy widths alone cannot prove
sample identity. No view code may depend on private compiler/evaluation state.

Keep source/model snapshots and public metadata immutable, return copies of Stim
objects/matrices, and never edit caller raw arrays in place. Use exact immutable
instruction snapshots and full-precision source fingerprints; Stim circuit/DEM
text roundtrips can round floating-point arguments, especially on Windows. All performance-sensitive
sample transformations operate on whole batches. Physical correction selection stays external. Compiler make_frame_plan supplies
verified Pauli-to-record maps; this namespace consumes them without private
compiler state. Read STATUS before
changes and update it plus root STATUS with exact physics/model evidence.

Model-only ideal boundary probes may define temporal output targets, but never
enter canonical circuits or normal decoder input truth. Preserve physical noisy
prefix instructions and every selected fault effect. Conditional Bell models
retain correlated readout/survivor actions and exclusive categorical alternatives.
Do not pretend raw random Bell parities are zero-expected global detectors.
