# AGENTS.md — Python package root

No public physics API is implemented yet. Preserve a clean `src/` layout; avoid importing optional unpinned `stimflow`, surface-sim, or Hex into package `__init__.py`. Public exports must be added only after corresponding classes and tests are ready. Source subdirectories carry their own `AGENTS.md` and `STATUS.md`. `knill_bench` may consume this package but this package must not import `knill_bench`.
