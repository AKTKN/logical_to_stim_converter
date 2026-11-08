# LSTIM language milestones

M8-A implements the grammar-backed lexer/parser and immutable syntax tree.
M8-B adds semantic validation, bounded lowering and existing-compiler integration.
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
`language.parse_logical_circuit` returns an immutable LogicalProgram with existing
CodeSpec/LogicalBlock definitions and OperationModule/BindPatch objects. Its
compile method delegates to CircuitCompiler with an explicit empty initial
mapping; every source BIND is executed in order. Static loop analysis bounds
expanded occurrences before allocating patches or unrolling. M8-C will add
the public text/file API and canonical formatter; M8-D will independently certify
physical, DEM and sample equivalence.

Logical PARALLEL groups and REPEAT boundaries retain exact logical barriers. The existing
physical compiler continues to own physical TICKs, scheduling, noise, flow
verification and epoch/lifecycle validation. No implicit patch allocation,
decoder, CLI or alternate physical compiler is part of this frontend.
