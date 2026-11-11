# STATUS — LSTIM language

## Parallel composites and primitive ideal override — 2026-11-11

Grammar permits operations (including KNILL_EC/BELL_PREP) in PARALLEL; validation
retains minimum two, REPEAT restrictions, labels/options and compiler-owned
conflict/lifecycle checks. Existing lowering sends composite tuples to Python
planner; formatter roundtrips all fields/order without a scheduler. Pauli mode
adds transversal and primitive noise=ideal lowers to all-zero NoiseOverride.
Two obsolete syntax/semantic prohibitions were updated; golden tests unchanged.
Focused 261 checks pass with eight workers; root STATUS records full evidence.


## M8-D certification — 2026-11-08

The existing frontend passes independent physical/simulation equivalence; no
language Python or grammar change. Exact matched-reference circuits/DEMs, signed
flows, public canonical metadata, binding/epoch/relocation histories, source
fingerprints and views agree. Source file/comments/SourceSpan remain frontend
provenance. Explicit bindings/labels and empty initial mappings match direct
references; legacy implicit reservations are not silently equated.

164 new checks: 98 physical, 38 ordinary/Knill simulation E2E, 28 safeguards.
Together with all 1041 existing cases: 1205 passed in 260.96 s using -n 8.
Same-seed records and same-raw external decoder stages/predictions/corrections/
frames/failure labels agree for d=3/5 X/Z signed inputs, including three-cycle
P0/P1/P2 reuse and replacement adapters. 257-shot replay matches 13/134/110
slices without quantum execution. Independent encoded-reference/Bell-branch,
executed-Pauli and fault/reset proofs also pass. Root STATUS records exact
commands, final order-only Knill rerun, build/install evidence and limitations.
No new runtime decoder or simulator. Deferred features remain explicit in the
contract/certification guide; finite samples imply no universal LER guarantee.

Exact staged frontend: 600 passed in 144.32 s; Ruff, wheel/sdist/isolated
installed API and all eight CI examples pass. Root STATUS records commands.

## M8-C implemented — 2026-11-08

formatter.py emits canonical nested source with four spaces, lowercase booleans,
LF/final newline and no invented defaults. It preserves every typed semantic
field/order except SourceSpan and drops comments/blank lines. Static validation,
same-grammar reparse and exact typed immutable signatures reject malformed raw
ASTs. It neither lowers/unrolls nor allocates/compiles physical code. Raw ASTs use
the default budget; LogicalProgram retains its caller-validated larger budget.

program.parse_logical_file reads UTF-8 without newline translation and retains
the path. LSTIMFileError preserves original OS/encoding causes, reporting byte
and character locations for bad UTF-8 and no guessed line for unreadable paths.
Root/language export the four program/text/file/format APIs and five error types.
Existing immutable blocks/operations/spans, explicit labels and standard compiler
return values are preserved. No syntax, lifecycle, scheduling or physical changes.

C1 formatter: 57 passed in 1.47 s plus Ruff. C2 API+formatter: 82 in 2.07 s;
1040 full API-checkpoint regressions in 125.01 s. C3 packaging+lexer: 53 in 6.87 s,
including syntax-only and normal root imports from real wheel resources, both
source samples, independent noise, canonical metadata/DEMs, labelled Knill
children and views/frame/stage APIs. Both builds now use private source trees.
C4 full suite: 1041 passed in 119.24 s; exact staged frontend: 436 in 14.87 s;
Ruff/build pass. All pytest commands use -n 8 with pytest-xdist 3.8.0. Root STATUS
records commands, actual Linux Python 3.12.7/Lark 1.3.1/upstream pins and separate
Windows/Python 3.11 CI configuration. Runtime dependencies have no decoder/plot
requirement; wheel consumers block repository/optional imports and verify loaded
module paths. M8-D full noisy sample/decoder E2E certification remains deferred.

## M8-B implemented — 2026-11-08

Baseline main 0370baf7623791bbf473ac31aec71b5174e86d7e (M8-A, 768 tests).
semantics.py validates static names/order, FORMAT, code distances, signatures,
options/types/labels and repeats without modeling quantum lifecycle. Expansion
cost counts operations/directives/parallel members before constructing any code
or patch; default max_operations=100,000, configurable positive integer. Empty
repeat bodies are rejected so large empty loops cannot hide zero-cost iteration.
PARALLEL requires >=2 primitive operations; repeated bodies restrict resource
changes/labels and preserve the 64-block syntax bound.

lowering.py constructs the existing code/patch/operation types, preserving each
BIND, default flag/round value, label, ordered operand, separate SE and parallel
tuple. Repeated objects are fresh. program.py exports namespace-only immutable
LogicalProgram/parse_logical_circuit, blocks/operations/to_operations, original
source/AST and aligned source/explicit-label spans. compile delegates to
CircuitCompiler(blocks, logical_to_block={}) and the unchanged compile method.
No physical lifecycle/flow/noise/decoder logic is duplicated. Deferred imports
preserve syntax-only use and its existing isolated-wheel regression.

errors.py retains all M8-A syntax classes and adds LSTIMError, SemanticError and
CompileError. Semantic diagnostics locate statements/options; compiler wrappers
retain original_error/__cause__, source file and explicitly absent statement span.
The compiler provides no reliable statement marker; implicit module IDs are
never guessed. Source labels retain existing operation_id/composite provenance.

Checkpoints: semantics 117 passed in 0.20 s; lowering 47 passed in 0.22 s;
physical bridge 26 passed in 11.76 s; combined 190 passed in 11.92 s. Ruff passes.
M8-A syntax+semantics 280 passed in 4.51 s including wheel/physical-import isolation.
Focused tests compare actual objects, layouts/sites, physical ideal/noisy circuits,
DEMs, canonical record/detector/observable/use/stage metadata, repeated-compilation
independence and labelled Knill children against independently authored Python.
Compiler negatives retain original lifecycle/resource/geometry errors. Root STATUS
records complete commands and final full regression/build/source-snapshot evidence.
Full regression: 958 passed in 670.19 s; every one of the 768 old checks remains.
The exact staged source passes all 353 M8-A/B frontend cases in 16.41 s, lint and
sdist/wheel builds. An isolated installed-namespace Knill consumer verifies
bindings/relocation, labels, independent noise, DEM, metadata/views/frame plans
with decoder/plot/example/reference imports blocked. Wheel/sdist grammar and new
runtime modules agree with the index; README memory produces 17 wires/40 detectors.

Inspected actual constructor/planner/context/lifecycle APIs and pinned public
stimflow Chunk.verify before integrating. Dependencies remain Stim 1.15.0,
stimflow 1.17.dev0 ffe0d043, Lark 1.3.1. No external_lib/physical/decoder source
changes. Root/file parser and formatter remain M8-C; full noisy sampling/decoder
E2E equivalence certification remains M8-D. No allocator/CLI/scheduler/decoder.

## M8-A implemented — 2026-11-08

Baseline main 06cdc4fd61486cb4e0d138feff10c685bc1a0858 (M7-C).
Syntax only against docs/lstim_v1.md. Lark 1.3.1 selected after
inspecting its published Python compatibility and installed contextual/LALR,
interactive parsing and nonrecursive transformer APIs. Physical pins unchanged.
Semantic validation, lowering, public program/formatter APIs remain M8-B/C.

One grammar.lark drives contextual lex_source and parse_ast. Frozen typed ASTs
retain a version header, declarations, ordered bindings/operations/options,
labels, nested unexpanded repeats and primitive parallel groups. SourceSpans use
half-open code-point offsets and 1-based line/columns; CRLF offsets are retained
but excluded from equality/hash. No physical dependency is imported here.
Located Lex/Parse/Limit errors use bounded excerpts/carets. Budgets are 1,000,000
source characters, 100,000 tokens, 64 block levels and 128 decimal digits.

A1 lexer/package: 52 passed in 1.44 s; Ruff src/tests passed.
A2 AST/parser: 87 passed in 0.18 s.
A3 diagnostics/budgets: 24 passed in 3.44 s.
Combined: 163 passed in 5.05 s; Ruff src/tests/examples passed. Both exact
contract programs and illegal physical syntax are exercised. An isolated-wheel
test loads the grammar and runs tokens/AST with source paths removed, first with
physical imports blocked and then through the normal package root. Build and
wheel/sdist grammar/metadata checks pass. Full regression: 768 passed in 713.70 s,
including all 605 original physics checks. The exact staged-source syntax run
passes 163 tests in 4.66 s, with lint and sdist/wheel builds passing independently.
A 3,000-source seeded mutation check produces only
valid ASTs or typed located syntax errors.

Supported versions, positive counts, signature/option legality, declaration
ordering, resource/lifecycle rules and expanded-operation limits remain semantic
work for M8-B. Empty blocks and invalid quantum programs may parse structurally.
No lowering, formatter, compile bridge, decoder or physical equivalence is claimed.
