# AGENTS.md — LSTIM syntax layer

Read root/package instructions and this directory's STATUS before editing.
`grammar.lark` is the single syntax authority; load it with importlib.resources.
Use Lark LALR/contextual lexing and immutable, source-located AST nodes. Keep
syntax independent of physical compiler, Stim/stimflow, noise and decoder APIs.
The canonical v1 contract is docs/lstim_v1.md. A successful parse is not a
semantic or quantum-state validation. M8-B owns validation/lowering; M8-C owns
the package-level public API/formatter. Do not add either in M8-A.
Preserve statement/target/option order, explicit bindings and block nesting.
Update this ledger and root/test ledgers with actual checkpoint evidence.
