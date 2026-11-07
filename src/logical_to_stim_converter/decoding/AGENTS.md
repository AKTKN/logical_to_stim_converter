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
- interfaces.py: still a placeholder for future decoder result/prediction schemas.

Never remove a physical fault because it touches an excluded detector. Re-extract
from the unchanged physical gate/noise sequence; preserve hyperedges and correlated
^ components. Explicit DEMOptions must not silently enable approximations. Keep
random Bell records separate from reliable observables. View ordering is the
caller's explicit ID sequence or canonical order for semantic callbacks. Selection
audit and source fingerprint are authoritative; NumPy widths alone cannot prove
sample identity. No view code may depend on private compiler/evaluation state.

Keep source/model snapshots and public metadata immutable, return copies of Stim
objects/matrices, and never edit caller raw arrays in place. All performance-sensitive
sample transformations operate on whole batches. Physical correction selection and
automatic Pauli-to-record maps remain outside this milestone. Read STATUS before
changes and update it plus root STATUS with exact physics/model evidence.
