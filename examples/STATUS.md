# STATUS — Examples

## M9 follow-up — 2026-11-09

The M9 paired example now describes --p-st in [0,.75] as a policy-level DEM
compatibility requirement. It delegates validation to ResourcePreparationNoise
and reports invalid settings through argparse, without a traceback or separate
sampling-only exception. Direct Python callers receive the same policy validation.
The example's direct/source physical/DEM/shared-raw comparison is unchanged.
Root STATUS records CLI help/invalid/valid checks and all nine example commands.
The demo-only restriction and p=1 API behavior below are historical pre-follow-up.


## M9 initial update — 2026-11-09 (historical pre-restriction)

knill_resource_preparation_noise.py opts into ideal Bell resource initialization
plus post-SE independent data depolarization. It reuses the independently authored
explicit Python reference and unchanged three-cycle LSTIM file, comparing exact
ideal/noisy circuits, canonical DEMs/source identities, same-seed raw samples and
same-raw existing external decoding. No decoder implementation is added.

The new CI command --shots32 --p.001 --p-st.003 passes locally from the exact
staged export: 51 wires/255 records/192 detectors, six resource uses and 54 new
data targets; the finite seed929 batch has two restricted-baseline failures
(LER .0625), an observation without a threshold/optimality assertion. All eight
previous CI example commands also pass. Probability zero remains opt-in ideal
preparation. At the initial pre-restriction revision, only this demo rejected
p_st>3/4 and the API allowed p=1 sampling; the follow-up enforces the policy-level
[0,.75] range for every caller. Root STATUS records full tests/build and
remote Ubuntu/Windows Python 3.11/3.12 results separately. Exact physics and
conditional limits are in docs/resource_preparation_noise.md.


## M8-D paired source/physical/offline demonstration — 2026-11-08

lstim_equivalence.py independently writes direct public-operation references for
both frozen .lstim sources, using exact initial/later BindPatch directives and
labels. It compares ideal/noisy circuits, canonical DEMs, physical source identity,
same-seed records and shared-raw decoder outputs via unchanged memory/Knill
adapters. It checks unmodified raw records/DEMs and reports physical statistics,
exact first-DEM-error probabilities/targets, use history and finite decoder
failures/LER. No tests/reference clone imports or production changes are needed.

Local --shots32 --p.001 --seed826: memory 17 qubits/49 records/40 detectors/
492 DEM errors, zero failures in three strategies; Knill 51/255/192/2698, seven
uses and four restricted-baseline failures. These are observations, not LER
thresholds. The new bounded d=3 command is eighth in the existing platform/Python
CI matrix. The M7-C runner and both frozen source files are unchanged. Root
STATUS and docs/lstim_certification.md record full verification/scope/performance.

Exact staged frontend: 600 passed in 144.32 s; Ruff, wheel/sdist/isolated
installed API and all eight CI examples pass. Root STATUS records commands.

## M8-C frozen logical source samples — 2026-11-08

lstim/memory_d3.lstim and lstim/three_patch_knill_d3.lstim exactly match the two
v1 contract programs. They are UTF-8/LF logical source (enforced by Git attributes),
not physical Stim exports, and ship in sdist. The isolated-wheel root consumer
parses/formats/compiles both to 17/51 wires and checks real metadata/DEMs, source
labels/composite children, existing offline APIs and independent noise. The Knill
source preserves the explicit P0/P1/P2 reuse schedule and fresh resource handles.
The M7-C Python runner is unchanged. All seven existing CI example commands
pass from the exact staged export, including the three-patch 32-shot/13-row-batch
suite. Root STATUS records full commands and regression/build evidence;
full M8-D noisy E2E equivalence remains separate.


## M7-C explicit three-patch Knill memory — 2026-11-08

knill_memory_three_patch_reuse.py adds a separate caller-authored P0/P1/P2
schedule, explicit BindPatch directives/fresh resource handles and unchanged
KnillEC primitives. Public source-example helpers expose the program, compiled
artifact, prepared M6-D consumer, bounded aggregate run and reports. The original
fresh-resource example/result format remains unchanged. No runtime package,
upstream reference or dependency is modified; PyMatching/Matplotlib stay here.

One sampler serves bounded raw batches, decoded once per causal boundary in
software. Raw rows are released after aggregate failure/timing/hash updates.
Reports retain actual cycle/use/owner/binding/relocation events, preparation/SE/
readout stages and exact selected IDs, source/DEM identities, decoder restrictions,
honest corrected physical-readout labels and exclusive wall phases. Physical
width alone is constant; circuit/records/models/history grow with duration.

The 2048-shot/case d=3/5 X/Z T=3 p=.003 demo uses eight 256-shot batches each,
giving failures 454,553,652,651 respectively, with 51/147 physical qubits. T=10
d=3 signed-Z noiseless smoke uses nine shots in 4/4/1 batches with zero failures,
773 records and 584 detectors. Root STATUS and docs/three_patch_knill.md record
commands, independent physics/chunk/replacement checks and measured setup costs.
Prefix/stage model setup dominates the T=10 observation; no performance or
threshold claim is made. Local aggregate plots/JSON/CSV are ignored artifacts;
no raw samples or dense correction maps are saved or committed.
All seven CI example commands pass from the exact staged source tree, including
the new d=3/5 X/Z T=3 suite with 32 shots in batches 13/13/6. The README usage
and a different explicitly declared triple schedule pass. All nine significant
new example functions/classes have docstrings. Sdist includes the example and
guide; an isolated wheel public-API consumer uses its own sector adapter with
PyMatching/Matplotlib/examples/tests/reference imports blocked successfully.
