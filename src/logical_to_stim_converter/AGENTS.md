# AGENTS.md — Python package root

The public memory API is exported from `__init__.py`: code/layout/block models,
backend/context/fragment contracts, three memory operations, compiler/artifact,
and noise types. Stim/stimflow are pinned required dependencies. Surface-sim,
Hex, lomatching, and knill_bench must not be imported here. Do not export future
placeholder operations until implemented with physics tests. Preserve the `src/`
layout and consult per-directory AGENTS/STATUS before changes.
