# STATUS — Tests

## M6-D update — 2026-11-08

Added 46 integration/physics tests (24 memory and 22 decoder-view tests), retaining
all 394 M1–M6-C tests. The memory suite covers d=3/5 X/Z, both input bits, T=1/2,
all four Bell branches, actual physical encoded-reference tableaux, open residual
frames against M5 replay, omitted byproduct failure, noisy replay/alternate
capacity weights/chunking, one sampling call, no oracle input and report timing.

Decoder-view tests cover strict stage/gauge partitions, shot-specific conditional
Bell sectors without preparation normalization, early/late measurement-noise
targets, every conditional Pauli atom against vectorized Stim FlipSimulator at
both distances, independent physical correction execution/current-event updates,
source/batch/double-application failures, actual H/CNOT/orientation and physical/
virtual Paulis, parallel independent gadgets/spectator isolation and immutable
stage contracts. Ten separately injected data/SE/resource-CX/Bell-CX/readout/post-SE/
logical faults compare actual physical global signatures with Stim's linear oracle;
an undetectable logical fault honestly yields failures.

The normal path never imports the M5 noiseless preparation helper or receives
hidden faults/tableaux. Full pytest, all six examples, isolated wheel and wall
results are recorded in root STATUS and e2etest/m6d_knill; no timing/LER threshold
is asserted and no raw samples/profiler binaries are committed.

## M6-C update — 2026-11-08

Added 24 tests in test_memory_offline_decoding.py plus two exact snapshot/source
identity regressions in test_decoder_views.py. All 368 prior tests are retained.
The memory tests cover d=3/5 X/Z R=d noiseless gauges and repeated seeds; signed
-1 inputs and physical/virtual Pauli interpretation; raw detector and observable
truth reconstruction independent of the adapter; noisy exact XOR failure counts
with independent d/R; one sampling call; immutable raw reuse; nontrivial mixed X/Z
patch/global observable order; chunk-independent decoding; registration-order
reproducibility; deterministic data/result fault signatures; hyperedge rejection
and supported correlated graphlike models; custom noise and report generation.

No stochastic LER target is asserted. Bounded integration tests use 64–512 shots
per batch; the separate requested figure uses 20,000 shots for each of five cases.
The precision tests emulate Windows DEM formatting, preserve tagged repeats,
shifts and ^ components, and catch source-fingerprint collisions caused by circuit
text rounding. Full-precision equality assertions remain unchanged. PyMatching
2.3.1 and Matplotlib are dev/example dependencies, never runtime decoder imports.
Root STATUS records final full pytest/lint/build/examples and platform evidence.

## M6-B update — 2026-11-08

Added 105 tests; all 263 M1–M6-A tests remain unchanged. test_decoder_views checks
d=3/5 memory and open/closed Knill identity DEMs, permuted/sparse/global-to-local
indices, one-batch semantic selections, strict/touching/anchor regions, cross-stage
policy/audit, signed reference conversion and record updates. It compares exact
DEM marginal parity expectations, physically enumerates selected faults, preserves
hyperedges/correlated ^ components, and checks independently seeded statistical
marginals. Public metadata hand circuits deliberately have no private compiler or
frame state. Negative indices, sources, missing metadata, check basis/support,
random observables, sample shapes and unsupported exact noise modes fail clearly.

test_record_frames checks immutable sparse/dense GF(2) maps (including uint8
overflow), empty dimensions, external correction maps against explicit physical
Pauli execution, once-only copy-based record updates, and malformed/source/shape
rejection. helpers/decoder_view_physics contains independent metadata/fault/parity
checks. The fourth example samples once for global/patch/observable-local views.
Root STATUS records final full test/lint/build/example and pinned API evidence.

## M6-A update — 2026-11-08

Added 42 tests; all 221 M1–M5 regressions are retained. Only the two explicit
Knill annotation-policy cases change their contract to canonical global detectors
and an explicit stage-separated derived view. Original M3 tests remain unchanged.

- test_causal_preparation_dependencies.py: spectator exclusion, parallel-gadget
  isolation and registration-order invariance, actual CNOT dependencies, d=3/5
  reference entanglement on physical tableaux, pre-existing resources, extra SE,
  repeated relocation, corrupted ancestry edges/snapshots, and correction-value
  isolation independently from metadata sources.
- test_global_detector_provenance.py: d=3/5 full detector recovery, independent
  Stim instruction parity/order reading, 256-shot raw parity reconstruction and
  m2d agreement, all random Bell branches, full ideal/noisy DEMs, unchanged physical
  instructions/noise locations/coordinates/records in the legacy view, explicit
  global/view detector mapping, open continuation, and negative index/stage tests.
- test_frame_validation_modes.py: strict noiseless equations/eigenvalue proof,
  a final check-result fault accepted as a hypothesis, actual noisy raw samples,
  deliberately wrong logical hypotheses, immutable samples/circuits, repeatable
  once-only replay, and malformed/unresolved/source/support/sign rejection.

Focused suite: 44 passed (including the two migrated boundary cases). Full final
test/lint/build/example evidence is recorded in root STATUS. No stochastic LER or
production decoding result is asserted.

## M5 update — 2026-11-07

Added 48 physics/metadata/noise tests; all 173 original tests are retained.
- test_knill_state_preparation.py: d=3/5 X/Z d-round preparation sectors across
  seeds; actual semantic histories/check order; gauge/temporal detectors; CSS
  equations and explicit corrected tableau checks; seven vector/matrix/order/
  mapping/orientation/omission failures.
- test_bell_state_preparation.py: d=3/5 default/overridden rounds, parallel timing,
  primitive-equivalent circuits, child/stage identity, physical corrected XX/ZZ,
  random singles, and separate explicit-correction simulation.
- test_knill_teleportation.py: four input states at both distances, all four Bell
  branches, explicit physical correction references, encoded reference-data
  entanglement, open export/continuation, H/SE/physical and virtual Paulis, all
  resource orientations, CNOT after relocation, other live patches, parallel
  composites, random readout/H timing, and wrong byproduct/orientation failures.
- test_knill_detector_boundaries.py: stage-local detector records, retained raw
  Bell checks, valid excluded global relations, boundary rejection, and ideal/
  noisy DEM construction.
- test_knill_noise.py: exact physical reset/result/gate/idle faults, two shared
  CNOTs, no duplicate/virtual faults, primitive equivalence, and seeded sampling.

helpers/preparation_matching.py imports PyMatching 2.3.1 unconditionally and
resolves final noiseless sectors only. helpers/knill_physics.py independently
probes physical tableaux and actually executes selected corrections on a separate
simulator. There is no temporal/circuit-level decoder or noisy recovery claim.
Root STATUS records exact final test/lint/build/example and CI evidence.

## M3 update — 2026-11-07

Final suite: **173 passed in 144.89 s**, including all 79 original memory tests.
Ruff, source/wheel build, both examples, and an isolated built-wheel Bell/frame/DEM
check passed. See root STATUS for commands and platform evidence.

- `test_clifford_backend.py`: all four CNOT orientation pairs at d=3/5; independent
  physical pair/support conventions; full check/logical flows; H-conjugated SE;
  H²/CNOT²; physical X/Y/Z action; wrong direction/pair/missing gate/orientation,
  required reflow, and corrupted generator-product failures.
- `test_clifford_compiler.py`: all CNOT logical basis truth-table inputs at d=3/5
  and every orientation pair, raw/affine readout signs, H then SE/H², virtual and
  physical Paulis, affine measurement-key rules, independent logical-tableau oracle
  comparisons for twelve random deterministic-output circuits, partial-readout/H
  concurrency, ordered/shared fragment identity, atomic failure, overlap/inactive
  rejection, and corrupted frame propagation caught by signed physical proof.
- `test_bell_roundtrip.py`: (d,R)=(3,1),(3,3),(5,1),(5,5), ideal/noisy DEMs, physical
  intermediate XX=ZZ=+1 and zero local X/Z expectation, raw final Z outcomes (0,0),
  exact correlated detector parities/provenance, reproducible noisy samples,
  CNOT-only correlated faults, and a syntactically valid corrupted record parity.
- `test_clifford_noise.py`: exact layer/channel/probability/target counts for mixed
  concurrent H/CNOT/Pauli operations, one shared CNOT provenance, once-only gate
  noise, idle on both participants, virtual zero time/noise, and zero-noise equality.

No decoder/LER, Knill, parser, or general Clifford/teleportation tests are claimed.
The Ubuntu/Windows Python 3.11/3.12 CI matrix is preserved and runs both examples.

## Prior memory test record

**2026-11-07: 79 tests passed in the local Python 3.12.7 environment.**

- `test_code_layout.py`: d=3/5 CSS ranks/commutation/logical pairing and immutability,
  invalid specifications, GF(2)-versus-real rank, N/Z direction/control/target,
  local mappings, counts, and explicit pinned-reference d=3 support fixture.
- `test_flows.py`: full signed check/both-logical flow counts, init/readout discarded
  boundaries, ChunkLoop composition, ideal DEM/sampling, and deliberately corrupted
  gate/record/sign verification failures.
- `test_memory.py`: d=3/5, one/two/three patches and X/Z/mixed bases, SE rounds 1/3/5,
  exact detector/observable raw parity, first/intermediate/terminal records, physical
  distance 3/5 in both bases (compared with Stim's built-in memory distance),
  lifecycle/frame/preparation syndrome, registration-order invariance, final-index
  reordering, collisions, unequal rounds, waiting and mixed-phase operation layers.
  Adding a random preparation-sector outcome as a detector is rejected by Stim.
- `test_noise.py`: exact fault channels/targets/probabilities, concurrent idle,
  reset/result errors, one-qubit upstream rule, type/instance replacement, waiting
  and retired blocks, zero-noise equality, no reinjection, metadata preservation,
  and seeded noisy smoke sampling without statistical thresholds.
- `test_scaffold.py`: retained package import smoke test, renamed to reflect the
  now-functional public memory API.

Executed: `python -m pytest` -> **79 passed in 33.48 s**;
`python -m ruff check src tests` -> **all checks passed**. Build and the two-patch
example also pass; see root STATUS for versions and complete evidence.

No decoder/LER benchmark, Clifford/teleportation-frame test, or other code-family
physics is implemented. CI is configured for Ubuntu/Windows Python 3.11/3.12;
remote jobs have not run during this task. No upstream tests or sources were edited.

History: initial import-only scaffold -> full memory-core physics suite on 2026-11-07.
