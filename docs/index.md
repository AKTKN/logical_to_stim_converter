# Documentation

Internal research beta **0.0.1**, current documentation review 2026-11-09.
The [README quick start](../README.md#quick-start) and
[installation guide](development.md#install-the-001-internal-research-beta)
pin the reachable Phase 1 runtime integration; this documentation phase changes
no runtime behavior. Version 0.0.1 is an internal integration target, without a
durable stability promise for all low-level exports. License decision pending.

## Find a contract or example

| Area | Read first | Detail |
| --- | --- | --- |
| Installation / quick start | [README](../README.md) | [Development and upstream pins](development.md) |
| Language / APIs | [Public consumer API and glossary](api_reference.md) | [LSTIM usage](lstim.md), [v1 specification](lstim_v1.md) |
| Physical architecture / identity / time | [Architecture](architecture.md) | [Use/lifecycle glossary](architecture.md#identity-and-lifecycle-glossary-m7-a), [parallel time](architecture.md#parallel-assembly-and-time) |
| Noise / M9 | [Noise policy API](api_reference.md#noise-policy) | [Ordinary noise](architecture.md#noise), [resource preparation](resource_preparation_noise.md) |
| DEMs / conditional models / frames | [Decoder views](api_reference.md#decoder-views-and-index-maps) | [Stages](api_reference.md#temporal-and-readout-stage-requests), [frames](api_reference.md#offline-frame-plans-and-corrections), [conditional Bell actions](api_reference.md#conditional-bell-fault-actions) |
| Installed consumers | [Ordinary memory tutorial](ordinary_memory_tutorial.md) | [Three-patch Knill tutorial](knill_memory_tutorial.md), [standalone script](../examples/installed_consumer.py) |
| Practical examples | [Memory, Clifford and Knill examples](examples.md) | [Three-patch reuse](three_patch_knill.md), [physical circuit inspection (Japanese)](../examples/stim_circuit_guide_ja.md) |
| Development / certification | [Development](development.md) | [LSTIM physical/simulation certification](lstim_certification.md), [tests ledger](../tests/STATUS.md) |
| Roadmap / history | [Deferred work](deferred_work.md) | [Language milestones](future_logical_syntax.md), [root status](../STATUS.md), [beta phase ledger](research_beta_0.0.1_plan_and_verification.md) |

## Current implementation and limitations

This matrix separates installed converter behavior from external example algorithms.
Tests are evidence for their bounded cases, not certification of arbitrary codes,
hardware timing or numerical error thresholds.

| Capability | Current implementation / limitation | Source and focused evidence |
| --- | --- | --- |
| Rotated-surface memory | Odd square d >= 3 factory, explicit layouts, signed flows, initialization/SE/destructive X/Z readout; physical regressions emphasize d=3/5 | [Backend](../src/logical_to_stim_converter/backends/surface_code.py), [memory](../tests/test_memory.py), [flows](../tests/test_flows.py) |
| Clifford and Knill | Logical H/CNOT, physical or virtual X/Y/Z, Bell preparation, Knill relocation, random readout and open continuation; no S or universal gate set | [Operations](../src/logical_to_stim_converter/operations/__init__.py), [Clifford](../tests/test_clifford_compiler.py), [teleportation](../tests/test_knill_teleportation.py) |
| M7 physical reuse | Explicit BindPatch, fresh temporary names, reset-assigned epochs, persistent logical identity and historical metadata; no automatic allocator | [Lifecycle](../src/logical_to_stim_converter/core/lifecycle.py), [reuse tests](../tests/test_patch_reuse.py), [three-patch E2E](../tests/test_patch_reuse_knill_e2e.py) |
| M8 `.lstim` | v1 parsing, static validation/bounded lowering, public text/file/format/compile APIs; static REPEAT and explicit PARALLEL barriers | [Frontend](../src/logical_to_stim_converter/language/program.py), [API tests](../tests/test_lstim_api.py), [certification](lstim_certification.md) |
| M9 resource preparation | Opt-in Bell-owned ideal reset/SE plus post-SE data-only depolarization; finite non-boolean p in [0,.75], including disabled configurations; enabled zero still suppresses prep noise | [Policy](../src/logical_to_stim_converter/noise/model.py), [exact-location tests](../tests/test_resource_preparation_noise.py), [model tests](../tests/test_resource_preparation_models.py) |
| Canonical physical models | Every verified global detector, observable and physical/noise instruction retained; metadata tracks records, uses, timing and causal ancestry | [Compiler](../src/logical_to_stim_converter/compiler/circuit_compiler.py), [provenance tests](../tests/test_global_detector_provenance.py) |
| Decoder-neutral offline interfaces | Exact annotation-selected physical marginals, index maps, typed stages, source-bound frame maps and categorical Bell fault actions; caller chooses corrections | [Decoding exports](../src/logical_to_stim_converter/decoding/__init__.py), [views](../tests/test_decoder_views.py), [epoch stages/frames](../tests/test_epoch_stages_frames.py) |
| External decoder examples | Ordinary-memory MWPM and restricted modular Knill MWPM/capacity demonstrations, including repeated three-patch cycles and same-raw replay; optional dev/example layer, no production decoder or threshold guarantee | [Example guide](examples.md), [memory checks](../tests/test_memory_offline_decoding.py), [replay checks](../tests/test_patch_reuse_offline_replay.py) |
| Intermediate operand SE in conditional M9 windows | Enabled nonzero widened Bell windows reject intermediate operand preparation/SE measurements with UnsupportedProjectionError; gate/idle waiting and canonical circuit/global DEM remain supported | [Boundary contract](resource_preparation_noise.md#boundary-provenance-and-offline-decoding), [model tests](../tests/test_resource_preparation_models.py) |
| Other families / non-Clifford | Color/QLDPC backends, non-Clifford gates and a general quantum-programming frontend are unsupported; a CSS mathematical model does not supply physical compilation | [Deferred work](deferred_work.md), [code-family placeholder](../src/logical_to_stim_converter/backends/color_code.py) |
| Allocation / adaptive execution | Caller selects patches and static barriers; no allocator, factory scheduler, shot-dependent gates, retries/postselection policy or runtime branching; rounds expand, so record/history size grows | [Architecture](architecture.md#parallel-assembly-and-time), [language limits](future_logical_syntax.md#deferred-features) |

Phase 4 supplies the public-only installed-consumer workflows and tutorials
([#2](https://github.com/AKTKN/logical_to_stim_converter/issues/2),
[#5](https://github.com/AKTKN/logical_to_stim_converter/issues/5)); its observed-sector / identity-readout baseline is deliberately
limited under noise. The [Phase 5 final gate and handoff](research_beta_0.0.1_plan_and_verification.md#phase-5--final-integration-gate-and-handoff-2026-11-09)
records current verification; the license decision remains pending. This index/reference addresses
[#3](https://github.com/AKTKN/logical_to_stim_converter/issues/3) and
[#4](https://github.com/AKTKN/logical_to_stim_converter/issues/4) without claiming
the detailed worked examples requested by P1
[#6](https://github.com/AKTKN/logical_to_stim_converter/issues/6) and
[#7](https://github.com/AKTKN/logical_to_stim_converter/issues/7) are complete.
