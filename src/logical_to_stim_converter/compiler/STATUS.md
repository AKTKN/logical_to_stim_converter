# STATUS — Compiler

## M6-A update — 2026-11-08

Principal ideal/noisy circuits and detector metadata retain the full verified
physical detector history. Compilation no longer calls separate_detector_regions;
that compatibility helper and stage_separated_circuit explicitly derive views.
Boundary candidates retain canonical indices/parities/stages and the view exports
local-to-global detector IDs. Physical instructions, noise and raw records agree
exactly. Tags retain check/block/module anchors without extra coordinate dimensions.
_provenance.py validates global mappings and actual primitive/relocation ancestry
edges at compilation and through the public validate_metadata method.

ProtocolAssembly tracks per-block preparation sources at actual operand
interactions. Bell results snapshot relevant input/resource histories; final
physical and affine frame provenance follows final causal sources. Independent
spectators/parallel gadgets stay isolated, including interleaved resources and
repeated relocations. Physical per-shot propagation remains separate from sources.

Frame replay preserves strict M5 validation by default and accepts explicitly
selected noisy hypotheses after shape/identity/support/commutation checks.
validate_noiseless_preparation_corrections separately checks the final raw sector
and prepared eigenvalue without replay. Hypothesis acceptance is not decoder truth.

Focused verification: 44 causal/global/frame/boundary checks passed at d=3/5;
all three examples and the initial build passed. Root STATUS records final full
verification. Pins remain Stim 1.15.0 and stimflow 1.17.dev0 at
ffe0d043598ed5df0851a3e6b4920359a23fafbd. Inspected installed FlowMetadata,
ChunkCompiler metadata callback/detector insertion and VCS install provenance;
its public tag preserves anchors, with default (x,y,t) coordinates. No upstream
code or pin changed. General DEM projection, batch decoder adapters, noisy
sector inference and LER remain deferred to M6-B/C/D and downstream consumers.

## M5 update — 2026-11-07

_plan.py expands composites while preserving parallel layers/identity/stages.
_teleport.py verifies resource contracts and transfers persistent logical identity
D to physical B, retaining history and retiring resource identities. _logical.py
retains signed conditional quantum outputs through random destructive readout.
Physical measurement discards consume only the destroyed logical generators.

Open artifacts retain cur_end_interface and export through a zero-operation
projection on a copied compiler; no MPP/artificial readout closes the circuit.
append recompiles the physical prefix plus continuation with full verification.
Default closed-memory completion checks remain compatible.

_metadata.py builds stage-local preparation/readout matrices and histories. All
physical flows and the unfiltered circuit are verified first; an explicit detector
policy suppresses cross-stage annotations while retaining their raw parity and
provenance. Emitted regions and ideal/noisy DEMs validate. Ordinary M3 correlations
remain unchanged. _frames.py validates externally resolved physical corrections,
propagates actual physical H/CX pairings, interprets measurement flips once, and
tracks Bell byproducts/residual frames without modifying the primary circuit.

Verified physics, boundary rejection, continuations, and exact fault tests are
recorded in root STATUS. Pins remain Stim 1.15.0/stimflow ffe0d043598ed5df0851a3e6b4920359a23fafbd.
Pinned ChunkReflow requires square generator changes; its nonsquare diagnostic
is defective. Supported square reflows and Chunk measurement/export boundaries
avoid this path without modifying upstream. Production decoding, incremental
compilation caching, independently sliced stage DEMs, and noisy recovery deferred.

## M3 update — 2026-11-07

M3: _logical.py retains a complete known logical-state generator basis
across interacting blocks, using public Stim conjugation and stimflow reflows.
CNOT check correlations are preserved. Local readout is rebased only when its
intended logical outcome is deterministic; final affine output gets an independent
signed Stim flow proof. _parallel.py supports H/X/Y/Z and reflow steps without
extra duration. _metadata.py exports semantic check anchors, all contributing
blocks, validated causal provenance, affine observable correction, and raw readout
indices. CompiledCircuit.interpreted_measurements(raw) includes symbolic terms
and constants; code orientations and physical indices are exported independently.
Component-time logical basis tracking handles readout parallel to another block's H.
No general scheduler, random individual Bell readout, decoder, or teleportation
is introduced.

Evidence: the extended 173-test suite, Ruff, and both examples; exact final
commands/results are in root STATUS. Dependencies remain pinned to Stim 1.15.0
and stimflow commit ffe0d043598ed5df0851a3e6b4920359a23fafbd. External
source trees are unchanged.

## Prior memory implementation record

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
