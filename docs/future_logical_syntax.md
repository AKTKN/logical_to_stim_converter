# LSTIM language milestones

M8-A implements the grammar-backed lexer/parser and immutable syntax tree.
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

`logical_to_stim_converter.language.parse_ast` checks syntax only. A parsed
program has no allocated physical resources and cannot yet compile. M8-B will
validate declarations, signatures and bounded static loops, then lower to the
existing OperationModule/BindPatch sequence and CircuitCompiler. M8-C will add
the public text/file API and canonical formatter; M8-D will independently certify
physical, DEM and sample equivalence.

Logical PARALLEL groups and REPEAT boundaries are syntax data. The existing
physical compiler continues to own physical TICKs, scheduling, noise, flow
verification and epoch/lifecycle validation. No implicit patch allocation,
decoder, CLI or alternate physical compiler is part of this frontend.
