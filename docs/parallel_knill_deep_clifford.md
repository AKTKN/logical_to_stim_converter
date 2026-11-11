# Parallel Knill / deep Clifford implementation record

Date: 2026-11-11 (Asia/Tokyo).

## Git integration

`git fetch origin` confirmed main
`be734ce71c5140a9e01ccd1fdb2d181678cef663` and validation
`64e139d16dd5e66dd8ecb33a1baaf5ca4364d302`, with five validation commits ahead
and none behind. Main was fast-forwarded and pushed to 64e139d; no merge commit,
force push, fixture regeneration or upstream edit was used.

`feature/parallel-knill-deep-clifford-api` was created from that main. The
checkout's preexisting dependency-compatibility commit 110f6ab was retained by
fast-forward; this feature makes no further dependency specification changes.
Implementation commit: `b74df3282e4936a32e7c698bbc7305d881038c05`.
The evidence-only follow-up commit containing this record is the branch HEAD.

## Public changes and source map

- `language/grammar.lark`, `semantics.py`, `lowering.py`: independent KNILL_EC and
  BELL_PREP in PARALLEL, Pauli mode=transversal and primitive noise=ideal. Existing
  formatter handles the added typed options/groups. REPEAT restrictions stay.
- `operations/pauli.py`, `backends/surface_code.py`, `core/code_backend.py`:
  separate data-wide signed physical Pauli mode. The old representative physical
  mode and zero-duration software frame mode retain their behavior.
- `noise/model.py`, `post_initialization.py`, `injector.py`: typed
  PostInitializationNoise selected by operation ID and physical-use epoch,
  distinct final-SE cuts and exact channel location/probability metadata. Existing
  M9 eligibility/resolution/suppression is reused; duplicate/overlapping policies
  fail. Empty policies retain existing circuit/source behavior.
- `compiler/terminal.py`: LogicalPauliProduct, TerminalObservableInfo and
  TerminalObservableProbe, intended active logical stabilizer snapshots and
  CompiledCircuit.make_terminal_observable_probe. Signed products are validated
  and lifted using final bindings/H orientation. Y=iXZ and explicit MPP target
  inversion preserve physical signs. Circuit snapshots are exact independent
  copies. The canonical prefix and terminal suffix have separate maps.
- `compiler/export.py`: CompiledCircuit.export_metadata exports owned JSON values
  with exact instruction arguments/targets/tags, public provenance, dependency
  versions, pinned stimflow source commit and the selected typed noise settings.
- `decoding/views.py`, `stages.py`, `conditional.py`: optional explicit-init cut
  provenance in source fingerprints and correct preparation/conditional windows.
  StageRequests, CorrectionBatch and OfflineFramePlan semantics remain intact.
- `examples/deep_clifford.py`, `examples/lstim/deep_clifford_d3.lstim`: public-only
  four-qubit depth2/3, one/two Knill-cycle consumer, three patches per logical
  state, both resource policies, terminal probes and export. Its recorded-sector
  recovery checks noiseless physics; noisy samples have no claimed LER decoder.

The small consumer illustrates the requested circuit family; it does not
reproduce numerical results or correlated inference from
[Cain et al.](https://arxiv.org/abs/2403.03272).

## Verification

The initial focused updated checkpoint passed **261 tests in 114.59 seconds**
with `python -m pytest -n 8`, after fixing explicit signed MPP target encoding.
The installed Stim 1.15.0 PauliString append shorthand drops the input sign;
regressions now check negative stabilizers, multi-block Y products and actual
inserted logical Pauli errors independently of the frame evaluation.

The expanded focused file has 67 parameterized cases; the complete repository
has 1,664 cases (1,598 baseline + 67 additions - one obsolete syntax rejection).
Existing golden tests, fixtures and reports remain unchanged. The existing
installed-wheel test also now executes new public APIs with repository and
optional-decoder imports blocked, from a private build tree.

Complete regression: `python -m pytest -n 8 --durations=10` passed **1,664 tests
in 1,035.32 seconds**, with no failures or skips. This includes every existing
A0–C2 Knill golden and memory/fault/fixture assertion. Ruff
`check src tests examples validation`, pip check and git diff --check pass.
The unchanged validation and dependency trees were checked against the starting
110f6ab commit. No live Hex re-extraction or frozen fixture rewrite was needed.
The final exact-tree public/export/installed-package gate passed **68 in 43.66 s**
with Stim 1.15.0 and **68 in 63.67 s** with Stim 1.16.0, both with eight workers:

```sh
python -m pytest -n 8 tests/test_parallel_deep_clifford.py tests/test_lstim_packaging.py --durations=5
```

The 1.16 check used a separate temporary virtual environment with an independently
installed Stim 1.16 wheel and the unchanged project environment's other packages.
Both dependency checks pass. The 1.16 check imports only the intended project
dependencies. Private wheel and sdist builds also pass. No build products or
sample batches were added to Git. Both resource policies, output export and the
noiseless recovery baseline execute within these integration checks.

Remote CI conclusions and the exact tested runtime revision are recorded below.

Local runtime:
Python 3.12.7, Stim 1.15.0, stimflow 1.17.dev0 at
ffe0d043598ed5df0851a3e6b4920359a23fafbd, NumPy 2.5.4, SciPy 1.18.1,
Lark 1.3.1, pytest 9.2.0, pytest-xdist 3.8.0, PyMatching 2.3.1.

The feature push started the full eight-job
[CI matrix](https://github.com/AKTKN/logical_to_stim_converter/actions/runs/43029481796):
Ubuntu/Windows × Python 3.11/3.12 × Stim 1.15.0/1.16.0. **All eight jobs completed successfully**, including installation, Ruff, the
complete 1,664-case suite, wheel/sdist builds and all eleven example commands.
The matrix is attributed to runtime implementation b74df32; this record's final
evidence-only commit changes documentation/status files and leaves every Python,
grammar, example, dependency and workflow byte identical to that tested revision. The main integration's existing four-job workflow
[run](https://github.com/AKTKN/logical_to_stim_converter/actions/runs/43026856339)
completed successfully in all four Ubuntu/Windows × Python 3.11/3.12 jobs.

The completed Ubuntu/Python 3.11/Stim 1.16 feature job reports **1,664 passed in
1,105.81 s** and successful lint/build/all eleven example commands. Both new
8-shot resource-policy examples report twelve patches, twenty uses, eight
teleportations, raw shape [8,592], sampling-with-probes shape [8,596], 432 global
detectors and four terminal stabilizers, with zero noiseless corrected failures.
The noisy decoder field explicitly remains unevaluated.


| OS | Python | Stim | Complete job |
| --- | --- | --- | --- |
| Ubuntu | 3.11 | 1.15.0 | PASS |
| Ubuntu | 3.11 | 1.16.0 | PASS |
| Ubuntu | 3.12 | 1.15.0 | PASS |
| Ubuntu | 3.12 | 1.16.0 | PASS |
| Windows | 3.11 | 1.15.0 | PASS |
| Windows | 3.11 | 1.16.0 | PASS |
| Windows | 3.12 | 1.15.0 | PASS |
| Windows | 3.12 | 1.16.0 | PASS |

The final documentation push starts the normal workflow again; that redundant
run is separate from the completed runtime matrix above.

## Downstream consumer

```python
from logical_to_stim_converter import NoiseModel, parse_logical_file
from logical_to_stim_converter.decoding import make_stage_requests

program = parse_logical_file("deep_clifford_d3.lstim")
compiled = program.compile(
    noise_model=NoiseModel.uniform_depolarizing(.001), allow_open_outputs=True,
)
compiled.validate_metadata()
requests, plan = make_stage_requests(compiled), compiled.make_frame_plan()
probe = compiled.make_terminal_observable_probe(compiled.logical_output_stabilizers)
samples = probe.circuit.compile_sampler(seed=113).sample(32)
raw, terminal = probe.split_measurements(samples)
frames = plan.start(raw, source_fingerprint=plan.source_fingerprint)
# An external MWPM adapter constructs/applies source/use-bound CorrectionBatch values.
# for correction in corrections: frames.apply(correction)
failures = probe.corrected_flips(samples, frames)
metadata = compiled.export_metadata()
```

SE memory and repeated Knill memory continue using the existing ordinary-memory
and three-patch public APIs. The new deep Clifford consumer supplies the added
parallel, noise and terminal-observable pieces without copying production
construction into knill_bench or editing generated Stim text externally.

## Remaining bounds

Rotated odd-distance surface codes only. Tests certify data-wide Paulis at
3/5/7; new deep/recycling examples use d=3 and depth2/3 with one/two cycles per
layer. Existing independent golden certification retains its d=3/5 bounded
memory/one-teleportation envelopes. Larger/deeper consumer programs use the same
APIs but are not a new independent golden certification claim.

Composites in REPEAT remain unsupported; author explicit groups and fresh resource
names. Static circuit/record/frame-plan size grows with duration despite fixed
physical width. No decoder is selected or shipped inside the converter. Exact
canonical DEMs can have hyperedges; ordinary matching conversion must explicitly
handle/reject unsupported correlations. Conditional Bell windows crossing an
intermediate operand SE still require extra unsupported temporal hypotheses.

Post-init and M9 data probabilities are restricted to finite non-boolean [0,.75]
for exact native DEM compatibility. Overlapping explicit and M9 channels on one
resource use fail. Terminal products must be commuting deterministic intended
observables, with all factors on active outputs. Raw terminal results are not
zero-expected decoder inputs; external physical frame hypotheses determine the
final symplectic correction. No noisy LER, threshold, correlated-decoder accuracy,
hardware scheduling or queueing result is claimed.
