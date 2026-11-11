# Independent golden memory validation

This research suite certifies one rotated patch at distances **3 and 5**, in
**X and Z** memory bases, with **exactly three syndrome rounds**. The DUT uses
`LogicalInit("D", basis, 1)`, `SyndromeExtraction("D", 2)`, and destructive
`LogicalMeasure`. Initialization already supplies the first syndrome round.
Nothing here is installed in the runtime package or selects a decoder.

Run from the repository root with `.[dev]` installed:

```sh
python -m validation.golden_memory.run --distance 3 --basis Z --level all
python -m validation.golden_memory.run --distance 3 --basis X --level all
python -m validation.golden_memory.run --distance 5 --basis Z --level all
python -m validation.golden_memory.run --distance 5 --basis X --level all
python -m validation.golden_memory.run --matrix --workers 8 --output /tmp/golden.json
python -m pytest -n 8 tests/test_validation_golden_memory.py -ra
```

On Windows, use a suitable local path for `--output`. The CLI accepts `--distance
{3,5}` (default 3), `--basis {X,Z}` (default Z), `--level {A,B,C1,C2,all}` (default
all), `--matrix` (all four cases), `--workers 1..8` (default 8), `--output PATH`
(optional JSON copy), and `--regenerate-fixtures` (explicit maintenance below).
The pool uses `spawn`; each task constructs its own DUT. A full matrix has 16
independent tasks. Ordered reports are invariant under worker assignment. There
are no Monte Carlo tolerances or performance thresholds. The 64-shot, fixed-seed
ideal smoke checks supplement exact proofs; streams are never equated shotwise.

`compare.py` exposes `ideal_semantic_equivalence`, `common_noise_equivalence`,
and `exact_schedule_equivalence`. Success returns a `ValidationReport`; failure
raises `normalize.Mismatch`, an assertion with semantic keys, coordinates,
rounds, expected/actual rows, moments, events, probabilities or fault signatures.
`compile_dut` is the sole bridge to public converter construction. Callers may
supply a Stim circuit directly for deliberate corruption controls.

## A: ideal semantic equivalence

`reference_stim.py` calls Stim's standard rotated-memory generator. Its sparse
wire IDs, ancilla H/MR convention, raw-record order and physical CX schedule
differ from the converter. Reflection `(x,y)_Stim -> (y,x)_golden` aligns **only
occupied coordinates**, independently classifying data and check sites. Every
raw record is parsed into a check/basis/coordinate/round or a data/basis/coordinate
key. DUT measurement, detector, logical parity and anchor metadata are checked
against that parser, never used to generate expected physics.

For each check, expected constraints are the first matched-basis syndrome,
adjacent round differences, and the last matched-basis syndrome XOR terminal
check support. The logical constraint is the independently selected logical
string's readout parity. First complementary-basis syndromes remain random.

The complete measurement-only signed constraint space is extracted from
`Circuit.flow_generators()` by eliminating **all input and output Paulis**.
Elimination multiplies actual `stim.Flow` objects, retaining Pauli phases; each
eliminated signed relation is verified again with `has_flow`. GF(2) reduction
compares the entire affine space, proving both the expected constraints and the
absence of additional constraints. A signed Bell-Y regression checks the phase
convention. Rank is **25/73**, leaving exactly **8/24** free raw bits at d=3/5.

Each round separately proves both signed check-measurement flows and preservation
of logical X and Z. Ports live on data; ancillas are discarded. When splitting
the standard circuit, the output reset state of the preceding MR is explicitly
supplied as the next round's ancilla R. Ancilla output states are not equated to
converter MX/M outputs. The 54/150 signed round flows per circuit establish the
specified data/check instrument. Detector/observable rows are also checked
individually and as GF(2) row spaces, independently of emission order and display
coordinates. Record multiplicities cancel modulo two.

## B: common reset/readout noise across schedules

Both circuits use reset and readout probability `.01`, with all Clifford and
idle noise disabled. Actual elementary channels are enumerated separately from
DEMs. Initial data/ancilla reset faults map directly; standard post-MR reset
faults in round t map to converter pre-round resets in t+1. X-ancilla faults
are conjugated through H (`X` in the standard R/H convention corresponds to
`Z` after converter RX). Standard pre-MR/readout Pauli faults map to converter
measurement-result flips. Other channels are rejected in this comparison.

Every matched mechanism is forced **in isolation**, including any with zero
signature. Its reference record supplies the candidate detector/logical response;
`has_all_flows` then proves every response bit's signed parity deterministically.
No probabilistic sample or DEM-row association establishes the truth table.
Canonical semantic detector anchors align the signatures. All **66/194** matched
mechanisms per d=3/5 case have equal signatures; none of these matched mechanisms
has zero signature. Standard resets after the last MR are explicitly unmatched:
all **8/24** are verified inert, individually. Multiple elementary mechanisms
may share a signature and are still checked separately. No DEM faults are removed.

CX faults need not agree between these different schedules. B does not claim
full noisy physical equality or compare finite-p logical error rates.

## C: exact independent physical schedule

`reference_same_schedule.py` depends only on Python and Stim. It neither imports
converter objects nor reads DUT circuits/metadata. It constructs checkerboard
plaquettes on a dual square grid, boundary colours, supports and logical strings
from elementary coordinates. Tests check CSS rank/commutation/logical pairing and
hard-code the reviewed d=3 supports. A subprocess blocks all converter and test
imports while building every reference.

The written schedule uses ancilla displacements X=`NW,SW,NE,SE` and
Z=`NW,NE,SW,SE`, X ancilla controls, and Z ancilla targets:

| Moment | Action |
| --- | --- |
| 0 | Data reset in the memory basis |
| 1, 7, 13 | Ancilla RX/R |
| 2–5, 8–11, 14–17 | Four CX layers |
| 6, 12, 18 | Ancilla MX/M |
| 19 | Destructive data readout |

C1 compares all 20 physical moments and 19 TICKs against the frozen ideal
fixtures. Qubit IDs map through occupied coordinates, aliases canonicalize in
Stim, REPEAT expands, tags/display annotations disappear, and grouped targets
split into atomic events. A dependency depth on each wire permits reordering
only disjoint events within a moment. Gate direction, basis, inversions and
causal order on every wire remain exact. Annotations are compared independently
using the mathematical expected rows.

C2 manually authors reset errors `.01`, CX depolarization `.03`, measurement
result flips `.04`, and idle depolarization `.05`. The one-qubit Clifford setting
`.02` intentionally has **zero** locations in this memory schedule. All patch
sites are active from moment 0 through moment 19 inclusive, including ancilla
idles after terminal data readout. Noise counters preserve multiplicity and key
moment, parent occurrence/side, channel, ordered target(s), double probability,
and position on each wire. Gate and idle parents are distinguished. Noise cannot
commute through an overlapping reset, CX or measurement to manufacture equality.

| d | Occupied | Records | Detectors | Reset | CX depol. | Result flips | Idle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 17 | 33 | 24 | 33 | 72 | 33 | 130 |
| 5 | 49 | 97 | 72 | 97 | 240 | 97 | 306 |

Each case has one logical observable. Native Stim DEMs are re-extracted from
**every physical instruction/channel** using independently canonical annotation
IDs and compared as exact objects, without printed probability rounding,
decomposition, projection or dropped faults. Each ideal/noisy comparison also
checks 27 deterministic X/Y/Z probes at the beginning, middle and end of every
round. All deliberate CX/support/layer/annotation/reset/CX-noise/idle/result/TICK
corruptions in the pytest suite must fail their designated checks after the
unmutated baseline passes.

## Frozen fixtures and maintenance

`fixtures/manifest.json` records actual Stim/stimflow versions and source commit,
DUT baseline commit, generator SHA-256, fixture SHA-256 and expected counts.
Fixtures are authored **only** by `build_reference`, never converter exports.
CI verifies their hashes, generator identity, dependency identity and direct
builder equality without writing files. No default invocation regenerates them.

For an intentional, reviewed change to the written specification or generator:

```sh
python -m validation.golden_memory.run --regenerate-fixtures --matrix --workers 8
python -m pytest -n 8 tests/test_validation_golden_memory.py -ra
```

Review the generator and fixture diffs, independently check d=3 supports and
four-layer gates, algebra, TICKs and annotations, inspect the manifest, and update
the dated evidence and status ledgers. This flag overwrites all four fixtures
and their manifest. Never invoke it to repair an unexplained DUT mismatch.

The [dated report](../reports/golden_memory_2026-11-11/REPORT.md) records the actual
source baseline, commands, counts, checksums and limitations. This certification
does not extend to H/Pauli/CNOT logical operations, multiple patches, M9, Knill,
reuse, other distances/round counts, decoder performance or platform coverage.
Those retain their separate existing regressions and research reports.

## Dependency compatibility

Stim >=1.15.0 is accepted using PEP 440 version ordering. Frozen manifest
versions describe their original generation environments and are never
rewritten to accept a newer wheel. The stimflow package/source checks remain
exact, including its Git commit. SHA-256, generator provenance, signed flows,
physical schedules, fault/noise locations and native DEM comparisons remain
unchanged. A newer version must pass those same checks; a behavior mismatch
is a compatibility failure. See the
[two-version execution record](../../docs/dependency_compatibility.md).
