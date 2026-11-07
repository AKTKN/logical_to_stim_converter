# STATUS — Compiler

**2026-11-07: minimal synchronous memory compiler/artifact implemented.**

- `circuit_compiler.py`: explicit parallel operation layers, fresh context per
  compilation, stable logical/observable identity, signed ChunkCompiler assembly,
  final ideal DEM validation, optional noise injection and noisy DEM validation.
- `_parallel.py`: disjoint TICK-layer composition, physical collision checks,
  symbolic flow measurement remapping, and passive identity ports. Passive flows
  explicitly use no new center to preserve check detector coordinates.
- `_metadata.py`: final physical indices from assembled coordinates; absolute raw
  record indices and semantic keys; detector/observable parities; preparation
  syndrome keys; active physical-time layers and module provenance.

Evidence: one/two/three patches, d=3/5, X/Z and mixed bases, exact parities,
observable uniqueness, registration-order invariance, local/final index changes,
no cross-patch gates, unequal rounds, waiting and retired blocks, and mixed-phase
parallel layers. Adding independent patches preserves synchronous physical depth.
See root STATUS for exact final test results.

StimCircuitLoom's matching-instruction requirement was inspected; mixed-basis
boundaries use the small public-API layer adapter instead. ChunkLoop components
are verified then expanded for exported per-layer/per-record metadata. Output
size is linear in rounds. No general scheduling optimizer, REPEAT compression,
decoder, Clifford assembly, or incomplete memory artifact is supported. Every
registered one-slot block must complete matched-basis preparation/readout once.

History: 2026-11-07 scaffold -> first working memory compiler.
