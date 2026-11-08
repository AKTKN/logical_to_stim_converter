# STATUS — LSTIM language

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
