# Architecture notes — planned contracts

**Status:** design document, not proof of implementation. Check [repository status](../STATUS.md).

## Conceptual pipeline

`logical operation` -> `OperationModule` subclass -> code-specific `CodeBackend` -> `ModuleFragment` carrying `stimflow` components and logical metadata -> `CircuitCompiler` -> ideal physical Stim circuit plus metadata -> `NoiseInjector` -> noisy Stim circuit. Sampling and decoder comparison are performed by the caller (`knill_bench`).

## Stable separations to preserve

1. **Mathematical code**: `CodeSpec` holds CSS check matrices, logical representatives, and parameters; no physical indices.
2. **Patch template and instance**: `PhysicalLayout` holds local data/ancilla sites, check schedules, and coupling; `LogicalBlock` binds it to actual global physical sites.
3. **Logical identity and location**: `CompilerContext` tracks `logical_qubit_id -> (block_id, logical_slot)` and per-block availability. Knill teleportation changes location; physical site identifiers do not move.
4. **Operation vs. code implementation**: operation subclasses say *what* is requested; backends say *how* that code realizes it physically.
5. **Physical flow vs. decoding**: `stimflow.Chunk` represents ideal Pauli flow through noisy-measurement-capable circuits; decoder-induced corrections and evaluation are separate symbolic/runtime data.
6. **Time vs. module order**: logical operation layers do not equal Stim `TICK`s. Independent physical modules must align their layers to represent concurrent execution and correct idle noise.

## Planned classes and responsibilities

| Class | Responsibility | Must not own |
|---|---|---|
| `CodeSpec` | CSS algebra: `H_X`, `H_Z`, chosen `(L_X, L_Z)` and parameters. Validate commutation, rank, symplectic pairing. | Physical placement, gate noise, sampled frame. |
| `PhysicalLayout` | Local data/ancilla sites, check-to-ancilla pairing, coupling graph, optional coordinates. | Global Stim indices. |
| `LogicalBlock` | Stable physical-block instance, local-to-global site map. | Ownership of logical ID across teleportation. |
| `CodeBackend` | Build ideal code-specific chunks: init/SE, transversal gates, destructive measurement. | Experiment runner, decoder selection. |
| `OperationModule` | Abstract input/output block contract; compile using backend. | Fixed decoder, global measurement offsets. |
| `ModuleFragment` | `stimflow.Chunk`/`ChunkLoop`/`ChunkReflow` plus block transition, frame rule, semantic measurement keys. | Duplicate stabilizer-flow implementation. |
| `CompilerContext` | Physical/logical registries, block availability, sample-independent symbolic frame/measurement metadata. | Shot-wise decoder state. |
| `CircuitCompiler` | Verify and assemble fragments, return compiled circuit plus mapping/observable metadata. | Physical code rules inside compiler. |
| `NoiseModel` | Default physical noise + per-operation/stage/instance overrides. | A second simulation of the same fault. |
| `NoiseInjector` | Apply noise to composed physical operations and globally active/idle qubits. | Reinterpret logical operation semantics. |

## Operation modules (requested initial scope)

- `LogicalInit(targets, basis in {X,Z}, rounds)`: physical basis reset plus repeated SE, initial stabilizer preparation, appropriate generated/unknown flows.
- `SyndromeExtraction(targets, rounds)`: repeated, verifiable SE chunks with boundary/round detector pairing.
- `TransversalCNOT(control, target)`: corresponding-physical-qubit pairing; verify logical and stabilizer action. Multi-logical-qubit blocks generally act on all encoded slots.
- `TransversalH(target)`: H on physical data, plus any code-specific relabeling/geometry to produce the claimed logical H; reject unsupported backends.
- `LogicalPauli(target, axis in {X,Y,Z}, mode in {physical,frame})`: distinguish executed physical gates from virtual Pauli-frame changes. Optional `LogicalX/Y/Z` convenience wrappers.
- `LogicalMeasure(targets, basis in {X,Z})`: destructive readout, terminal detectors, logical observable, release/reset suitability.
- `BellStatePrep(A,B)`: composite with two `LogicalInit`s, an H, and CNOT (or a substituted backend resource protocol); inputs can execute concurrently.
- `KnillEC(D,A,B)`: consumes pre-prepared Bell resource, transversal Bell measurement, logical `D -> B` location transition, symbolic byproduct and decoder input. It must not hardwire a decoder.

Memory experiments are assembled from `LogicalInit` + `SyndromeExtraction` + `LogicalMeasure`, not given a separate primitive class initially.

## Flow and detector contract

A module supplies an ideal Pauli relation of the form `P_in -> (-1)^(alpha · m + c) P_out`, including stabilizer and logical flows. `stimflow.Chunk.verify()` should validate each primitive. `stimflow.ChunkCompiler` composes compatible ports and produces detector/observable annotations; `ChunkReflow` handles changes of generators/basis. The package should add *metadata*, not a duplicate flow engine.

Decoder-independent artifacts must retain stable physical identifiers, complete measurement records, detector/observable maps, and symbolic frame transformations. Local/joint decoders later operate on identical physical samples. A `stim.DetectorErrorModel` captures noise correlations; a stabilizer flow alone is not an error model.

## Noise architecture

Use `stimflow.NoiseRule` and `stimflow.NoiseModel` wherever possible. Proposed selection precedence: operation instance > composite stage > operation type > global default. A more specific physical-gate rule *replaces* its inherited rule unless additive behavior is explicitly requested and tested. Never apply a composite's noise after independently applying its children's noise. Insert gate/measurement/reset noise and global idle noise exactly once after physical time-layer alignment. A read-only module/stage tag or external metadata may select the effective rule; verify how Stim and stimflow preserve tags before relying on them.

**Initial physics verification:** ideal circuit flow checks, detector determinism, target observable consistency, correct logical block migration after teleportation, DEM generation with physical noise, and explicit tests for coincident/idle qubits.

## Explicitly unresolved

- Exact public signatures and datatypes; how best to wrap/subclass stimflow objects.
- Integration versions/commits and surface-sim/Hex adapters.
- Parallel time-layer merger and exact idle noise semantics.
- Symplectic frame-rule storage and decoder-independent metadata schema.
- General support for code families without transversal H or with `k > 1`.
- Text logical-circuit parser (see `future_logical_syntax.md`); no parser in initial milestones.
