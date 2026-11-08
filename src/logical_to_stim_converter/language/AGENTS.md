# AGENTS.md — LSTIM frontend

Read root/package instructions and this directory's STATUS before editing.
`grammar.lark` is the single syntax authority; load it with importlib.resources.
Use Lark LALR/contextual lexing and immutable, source-located AST nodes. Keep
syntax independent of physical compiler, Stim/stimflow, noise and decoder APIs.
The canonical v1 contract is docs/lstim_v1.md. parse_ast validates syntax only.
M8-B semantics checks static names/signatures/options and expansion budgets before
lowering constructs any patches/operations. LogicalProgram is immutable; compile
delegates once to CircuitCompiler(blocks, logical_to_block={}). Keep every BIND
directive, repeated occurrence and parallel tuple. Do not duplicate lifecycle,
geometry, flow, noise, allocation or decoder logic. Compile errors preserve their
cause and report file-only context when the compiler supplies no reliable span.
Only explicit operation_id labels map to source spans; never emulate module IDs.
Keep physical imports deferred so syntax-only use remains independent. M8-C owns
the package-root/file APIs and formatter; M8-D owns full noisy E2E certification.
Preserve statement/target/option order, explicit bindings and block nesting.
Update this ledger and root/test ledgers with actual checkpoint evidence.
