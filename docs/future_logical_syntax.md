# LSTIM language milestones

M8-A implements the grammar-backed lexer/parser and immutable syntax tree.
M8-B adds semantic validation, bounded lowering and existing-compiler integration.
M8-C adds package-root text/file APIs, typed file errors and canonical formatting.
M8-D adds independent exact physical and same-raw offline-decoding certification.
The canonical specification and complete examples are in [LSTIM v1](lstim_v1.md).
The former R/TH/TCNOT sketch is superseded; those names are not accepted v1 syntax.

```text
FORMAT(1)
CODE sc ROTATED_SURFACE(3)
PATCH P0 sc index=0
BIND D P0
INIT_Z(3) D
REPEAT 2 {
    SE(1) D
}
MZ D
```

`logical_to_stim_converter.language.parse_ast` checks syntax only.
`parse_logical_circuit` (package root or language namespace) returns an immutable LogicalProgram with existing
CodeSpec/LogicalBlock definitions and OperationModule/BindPatch objects. Its
compile method delegates to CircuitCompiler with an explicit empty initial
mapping; every source BIND is executed in order. Static loop analysis bounds
expanded occurrences before allocating patches or unrolling. `parse_logical_file`
reads UTF-8 and retains the path and original CRLF offsets. `format_logical_circuit`
preserves the nested AST and all operation semantics, using four spaces, LF and
a final newline, dropping comments/blank lines. See the [language guide](lstim.md)
for installed API use and diagnostics. The [M8-D certification matrix](lstim_certification.md)
records verified physical/DEM/metadata and sample/decoder equivalence and its limits.

Logical PARALLEL groups and REPEAT boundaries retain exact logical barriers. The existing
physical compiler continues to own physical TICKs, scheduling, noise, flow
verification and epoch/lifecycle validation. No implicit patch allocation,
decoder, CLI or alternate physical compiler is part of this frontend.

## Deferred features

Automatic allocation, additional code families, non-Clifford gates, runtime
conditionals, probabilistic branching, text-defined noise/decoder configuration,
physical Stim passthrough and a CLI remain unsupported. v1 REPEAT is bounded
static unrolling, preserving each existing operation and logical barrier.
