# STATUS — Repository-wide development ledger

**As of:** 2026-11-07  
**Package:** `logical_to_stim_converter`  
**Overall state:** `SCAFFOLDED` (no quantum operations or compiler implemented)

## Implemented and checked

- [x] Python `src/` package skeleton and package metadata (`pyproject.toml`).
- [x] Root and per-package-directory `AGENTS.md` / `STATUS.md` documents.
- [x] Baseline README, architecture/development documentation, and local reference-library policy.
- [x] Minimal package-import smoke test and CI workflow definitions.
- [ ] Any physical Stim circuit construction or logical operation.
- [ ] Any stimflow integration, complete detector generation, or end-to-end simulation.
- [ ] Any noise injector, parser, decoder, or Knill implementation.

## Planned implementation order (provisional)

| Milestone | Components | Acceptance evidence | Status |
|---|---|---|---|
| M0 | Scaffold, packaging, documentation | Editable-install/import/build smoke | Scaffolded |
| M1 | `CodeSpec`, `PhysicalLayout`, `LogicalBlock`, `CodeBackend` | CSS algebra, validated rotated-surface patch/physical mapping | Not started |
| M2 | `OperationModule`, `LogicalInit`, `SyndromeExtraction`, `LogicalMeasure` | Verified ideal memory-flow / deterministic detectors / terminal observables | Not started |
| M3 | `TransversalCNOT`, `TransversalH`, logical Pauli modules | Physical gates match logical/stabilizer flows | Not started |
| M4 | `NoiseModel`, `NoiseInjector`, global timing | Target-specific overrides, idle behavior, no double injection | Not started |
| M5 | `BellStatePrep`, `KnillEC` | Verified resource/teleport flows, block relocation, frame correctness | Not started |
| M6 | decoder-facing compiled artifact / `knill_bench` integration | Same samples for local and joint decoding | Not started |
| Deferred | Stim-like text parser, other code families, runtime policies | Requirements and tests to be defined later | Deferred |

## Dependencies and architectural decisions pending verification

- Pin a specific `stim` and `stimflow` revision; `stimflow` has no guaranteed backwards compatibility.
- Verify surface-sim physical generator/flow metadata behavior for chosen rotated surface-code layout.
- Verify exact logical action of transversal H on chosen layout (including any coordinate transformation).
- Decide how parallel fragments are combined into global time layers before idle noise insertion.
- Decide minimal frame-rule and decoder-independent measurement/observable metadata schemas.
- Define rules for propagating stage-level noise overrides through composite operations.
- Select license and external dependency inclusion strategy before publishing.

## Changelog

- **2026-11-07** — Prepared the current scaffold for its initial GitHub upload:
  initialized local Git on `main` and created the private repository
  `https://github.com/AKTKN/logical_to_stim_converter` as `origin`.
  Only this status ledger changed during upload preparation; source placeholders
  remain unchanged. Verified that all four external source clones, caches, build
  output, and package metadata artifacts are excluded by `.gitignore`.
  With temporary verification tools outside the repository, `python -m build`
  produced the `0.0.0` source distribution and wheel, and
  `PYTHONPATH=src python -m pytest` passed the one scaffold import test.
  `python -m ruff check src tests` found **22 existing E501 docstring line-length
  errors**; these remain unresolved in this snapshot and affect CI.
  No physics functionality or runtime dependency integration was added or
  verified. Next: address the scaffold lint findings and begin M1 separately.
- **2026-11-07** — Read the package scaffold/design and external-reference guidance;
  cloned Stim/stimflow, surface-sim, Hex, and lomatching into the documented
  `external_lib/` folders. Updated `external_lib/README.md` and
  `external_lib/STATUS.md` with local availability, full commits, branches,
  source metadata, and untested installation entry points. Verified origin URLs,
  clean upstream working trees, and the presence of stimflow source classes.
  `PYTHONPATH=src python -m pytest`: **1 passed** (scaffold import only).
  Plain `python -m pytest` could not collect because the package is not installed;
  `python -m ruff check src tests` could not run because Ruff is absent.
  The workspace itself has no `.git` directory. No upstream source or package
  implementation changed; dependencies remain uninstalled and integration pins,
  physics/flow validation, and M1 remain pending.
- **2026-11-07** — Initialized documentation-first project scaffold. All source modules contain only explanatory docstrings; there is no implementation of requested QEC functionality. Initial status entries are plans, not verified results.

## Status update convention

For any implementation PR/task, record: date, changed source files, functionality added, tests run/results, upstream revision if used, outstanding issues, and next task. Update both this file and each affected folder's `STATUS.md`.
