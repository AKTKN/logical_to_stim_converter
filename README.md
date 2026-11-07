# logical_to_stim_converter

**Status (2026-11-07): scaffold only. No logical-to-physical compiler or QEC operation is implemented.**

`logical_to_stim_converter` is a planned, reusable Python library for compiling logical quantum programs into **physical Stim circuits** with explicit stabilizer/logical-operator flows, detector and observable definitions, physical-qubit mappings, and decoding metadata. The initial target is a rotated surface code; the design should subsequently support color codes and other CSS/QLDPC codes.

The motivating research studies fault correlations created by transversal logical CNOTs between code blocks in Knill error-correcting teleportation (Knill EC). A downstream experiment runner can compare local and joint decoding on **the same physical circuit and sampled data**, including the effect of changing Knill EC intervals. This package is intended to be independent of `knill_bench`, which remains responsible for experiments, parameter sweeps, storage, and analysis.

## Architecture

```text
future logical program (Python objects; text parser deferred)
       |
       v
OperationModule objects (primitive or composite)
       |
       v
CodeBackend + LogicalBlock + PhysicalLayout
       |
       v
ModuleFragment [stimflow Chunk(s) + block/frame/measurement metadata]
       |
       v
CircuitCompiler / CompilerContext
       |       \-- stimflow.ChunkCompiler: flow composition, detectors, observables
       v
ideal physical Stim circuit + logical/block/measurement metadata
       |
       v
NoiseInjector (contextual rules based on stimflow.NoiseModel/NoiseRule)
       |
       v
noisy physical Stim circuit / decoder-facing compiled artifact
       |
       v
caller (e.g. knill_bench): sample, decode, compute LER
```

The architecture is a **design target**, not a description of working code. Class names, arguments, and file boundaries remain provisional until tested against the pinned external libraries.

**Separation of responsibilities:**

- `CodeSpec`: mathematical code definition (CSS stabilizers and logical representatives), independent of physical sites and noise.
- `PhysicalLayout`: local data/ancilla labels, check support, coupling, geometry, and measurement-ancilla assignment.
- `LogicalBlock`: one physical code-block instance and its local-to-global physical-site mapping; a logical *identity* is separate from the physical block that currently hosts it.
- `CodeBackend`: code-specific implementations of reset/preparation, SE, transversal operations, and destructive measurement.
- `OperationModule`: abstract logical operation; subclasses compile via a backend into fragments.
- `ModuleFragment`: wraps `stimflow.Chunk`, `ChunkLoop`, or `ChunkReflow` rather than reimplementing their flow system; adds logical block transitions, frame rules, and measurement metadata.
- `CompilerContext` / `CircuitCompiler`: logical-to-physical location tracking, module composition, measurement mapping, and compiled-artifact assembly.
- `NoiseModel` / `NoiseInjector`: physical noise rules with default, per-operation, stage, and instance overrides; insert physical noise **once** after ideal-circuit validation and correct time-layer composition.

## Planned operations

| Module | Intended semantics |
|---|---|
| `LogicalInit` | Prepare logical `|0_L>` (`Z`) or `|+_L>` (`X`) by physical initialization and repeated SE; round count configurable. |
| `SyndromeExtraction` | Configurable number of SE rounds. |
| `TransversalCNOT` | Code-specific corresponding-physical-qubit CNOT and induced logical/stabilizer flows. |
| `TransversalH` | Code-specific transversal H and any required support/basis transformation. |
| `LogicalPauli` / `LogicalX`, `LogicalY`, `LogicalZ` | Physical Pauli or virtual logical-frame mode. |
| `LogicalMeasure` | Destructive `X` or `Z` measurement with terminal detectors and logical observables. |
| `BellStatePrep` | Composite resource-state preparation from primitives (or later another backend protocol). |
| `KnillEC` | Composite encoded Bell measurement / teleportation, data-block relocation, and symbolic byproduct specification. |

A memory experiment is a **composition of existing primitives**, not a separately implemented module in the initial scope. Future parser support for a Stim-like logical-circuit text notation is explicitly **deferred**; see [`docs/future_logical_syntax.md`](docs/future_logical_syntax.md).

## External library policy

Prioritize the upstream [`stimflow`](https://github.com/quantumlib/Stim/tree/main/glue/stimflow) APIs (`StabilizerCode`, `Patch`, `Chunk`, `ChunkBuilder`, `ChunkCompiler`, `ChunkReflow`, `Flow`, `NoiseModel`, `NoiseRule`) for verified circuit composition. **Use composition/adapters first; subclass only when necessary and supported by stable behavior.** `stimflow` currently warns that its API is not backward compatible. The precise revision must be pinned before integration.

`surface-sim` may supply surface-code layouts and physical SE/gadget generators; Hex may supply Knill/Bell gadgets; `lomatching` is a decoder adapter candidate. These are **not yet integrated**. Locally cloned source for inspection may be placed under [`external_lib/`](external_lib/README.md); those copies are ignored by Git by default and are **not bundled** in this archive.

## Windows development quick start

Requirements: Git, Python **3.11 or later** with a compatible Stim wheel, and a terminal (PowerShell or Conda Prompt). From the extracted project directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
```

Alternatively, use Conda as described in [`docs/development.md`](docs/development.md). `pip install -e ".[dev]"` installs the scaffold and basic dependencies, **not** external `stimflow` or `surface-sim` integrations.

## Repository map

```text
src/logical_to_stim_converter/
  core/        code specification, physical patches, backend contract, compiler context
  operations/  abstract operation and the requested primitive/composite modules
  backends/    surface-code adapter, future color-code adapter
  noise/       high-level noise policy and injector
  compiler/    composition and compiled-circuit artifact (planned)
  decoding/    reserved decoder-facing interface; no decoder implementation
tests/         scaffold import smoke test; future physics/flow tests
docs/          architecture, development workflow, future logical syntax
external_lib/  optional read-only local copies of reference source (gitignored)
```

## Documentation and change tracking

- [`AGENTS.md`](AGENTS.md): Codex/developer operating instructions and directory responsibilities.
- [`STATUS.md`](STATUS.md): repository-wide implementation status and change log.
- Every Python-package subdirectory has its own `AGENTS.md` and `STATUS.md`: folder-specific contracts, per-file planned behavior, acceptance criteria, and implementation history.
- Before and after a scoped implementation task, update the affected `STATUS.md` files, identifying implemented/verified versus planned behavior. Update `AGENTS.md` when responsibilities or boundaries actually change.

## Non-goals of this scaffold

No parser, physical circuit generation, noise injection, decoder, Knill gadget, package CLI, or complete runtime API is implemented. There is no commitment yet to any particular physical noise model, decoder, or final text-DSL grammar. A license has not been selected; add an appropriate `LICENSE` before public distribution.
