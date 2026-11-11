# STATUS — Documentation

## Parallel/deep Clifford consumer documentation — 2026-11-11

Updated API reference, LSTIM contract/guide, architecture and README for parallel
composites, transversal Paulis, primitive ideal noise, explicit init data noise,
signed terminal probes and exact metadata export. Documents M9/ordinary resource
policies, canonical-prefix/suffix separation and external noisy-decoder limits.
No dependency declaration or existing golden report/fixture was changed.
Root STATUS records execution evidence.


**As of:** 2026-11-11

Final complete local gate: **1,664 passed in 1,035.32 s** with eight workers,
no failures/skips. Ruff and pip checks pass; exact packaging and CI attribution
are in docs/parallel_knill_deep_clifford.md and root STATUS. All eight runtime
CI jobs (Ubuntu/Windows, Python 3.11/3.12, Stim 1.15/1.16) pass tests, builds and
all eleven examples at b74df32; this final follow-up changes documentation only.

## Minimum dependency compatibility (2026-11-11)

README now installs the current checkout. Development, architecture and LSTIM
contracts describe minimum PyPI versions and the unchanged exact stimflow source
pin. Original research-beta pin tables are explicitly labelled historical.
The [compatibility record](dependency_compatibility.md) records both separate
Stim environments and all verification results, without claiming unrun remote CI.

## Phase 5 — Final integration gate (2026-11-09)

The [final phase record](research_beta_0.0.1_plan_and_verification.md#phase-5--final-integration-gate-and-handoff-2026-11-09)
contains criterion-by-criterion #1–#5 acceptance, exact installation identities,
full local gate evidence, separate CI attribution, limitations and collaborator
commands. #1 remains partial with license decision pending; #2–#5 bounded internal
consumer/documentation acceptance is locally verified without issue edits or
release. The c45bf1f remote platform matrix remains PENDING at inspection;
its final conclusions must be observed separately.

Full eight-worker suite: **1373 passed in 401.70 s**; Ruff and all nine workflow
examples pass. Built wheel and actual uncached GitHub full-SHA install both pass
fresh runtime-only consumer cases and pip check. All 13 documentation Python
blocks pass against installed runtime with explicit supplied context/inputs where
needed. Final exact package/content and link review is in the phase ledger.

Narrow docs fixes use tested pushed c45bf1f, clarify own versus prior-cycle M9
channel ownership, label older CI counts as historical and describe implemented
LSTIM inspection APIs. README remains concise. No runtime/test/example code or
physics/dependency/version/license changes. Historical checkpoint outcomes below
remain unchanged; their pending-phase statements describe their original dates.

## Phase 4 — Installed consumers and tutorials (2026-11-09)

Added [ordinary memory](ordinary_memory_tutorial.md) and
[three-patch Knill](knill_memory_tutorial.md) tutorials with complete supplied
sources, external script/installation instructions, exact shape/order/label
conventions and explicit decoder limitations. README/index/API/examples/development
navigation links the workflows. The script and inputs are separate consumer
assets, not automatically installed wheel resources. Historical records below
retain their original checkpoint outcomes.

A fresh runtime-only installed wheel passes all six ideal/noisy/M9 CLI cases
and both tutorial snippets from outside the checkout with optional/example/test/
reference imports blocked. Full final metadata/archive/link evidence is in the
[Phase 4 ledger](research_beta_0.0.1_plan_and_verification.md#phase-4--installed-consumers-and-tutorials-2026-11-09).
Focused eight-worker physical/API/packaging regressions pass **117 tests in
146.14 s**; Ruff and whitespace checks pass. No runtime behavior/dependency/license
changes. Phase 5, license choice and detailed P1 worked guides remain deferred.

## Phase 2 + Phase 3 — 0.0.1 consumer documentation

The concise root README, documentation index/current implementation matrix,
public consumer API reference and ordinary/Clifford/Knill examples guide are
implemented. Existing architecture, development, deferred-work and language
milestone pages are reconciled with implemented M7 reuse, M8 LSTIM and M9 noise.
The Phase 1 integration is documented as pushed and reachable at the full pinned
0.0.1 commit. Historical checkpoint outcomes remain in the root/phase ledgers.

Verification and the original README-to-docs relocation map are recorded in the
[combined phase ledger](research_beta_0.0.1_plan_and_verification.md#phase-2--phase-3--documentation-and-public-consumer-api-2026-11-09).
README has 108 lines and one standalone 18-line Python quick start. Seven new
Python blocks pass from an isolated installed wheel outside the checkout with
runtime dependencies only and optional/example/test/reference imports blocked.
Ruff, wheel/sdist metadata/runtime-byte audits and the relative-link review pass.
Full parallel regression: `.venv/bin/python -m pytest -n 8 --tb=short
--durations=10` passes **1367 tests in 365.99 s**. The root ledger records
remaining verification limits.

No runtime physics/decoder behavior, dependency pin, version or license changes.
Phase 4 installed-consumer/tutorial work, Phase 5 final beta gate, license choice
and P1's detailed noise/DEM/frame worked examples remain separate tasks. This
phase does not close or edit issues, tag/release or publish artifacts.
