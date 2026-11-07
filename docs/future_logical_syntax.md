# Future Stim-like logical-circuit syntax (not implemented)

The intended long-term user input is a textual logical program similar to Stim:

```text
R 0 1
TH 0
TCNOT 0 1
REPEAT(9) {
    SE 0 1
}
MZ 1
MX 0
```

**The grammar, parser, semantics of `TICK`/parallel layers, and public API are not implemented and not yet fixed.** This example is a design reminder, not a supported file format.

When this milestone is started, parse into operation objects or a small logical IR, then reuse exactly the same `OperationModule` and compiler path as direct Python calls. In particular, logical program layers must not be conflated with physical Stim `TICK`s, and resource state placement must remain explicit or governed by a separately defined policy. Do not add a DSL parser during initial core/primitive implementation.
