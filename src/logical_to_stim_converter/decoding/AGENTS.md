# AGENTS.md — `decoding`

Scope: `src/logical_to_stim_converter/decoding/`. Root `AGENTS.md` and `docs/architecture.md` also apply.

## Responsibility

Reserved shared interface to decoder inputs/outputs; no decoder algorithm in this package initially.

- Preserve decoder-independent detector, observable, measurement, and scope metadata.
- Do not force every decoder to output a physical correction; allow observable flips and optional extra data.
- Keep fitting, Monte Carlo orchestration, LER aggregations and experimental sweeps in knill_bench.

## Files and intended responsibilities

- `interfaces.py` — planned **Decoder-facing contracts**: Future local/joint scope, observable prediction and optional correction/soft output schemas; intentionally deferred.

All `.py` files in this folder are **docstring-only placeholders** as of 2026-11-07. Do not treat documented methods as implemented. Implement the minimum validated surface-code path first unless the user requests otherwise. Update this folder's `STATUS.md` after changes; update root status for completed milestones.
