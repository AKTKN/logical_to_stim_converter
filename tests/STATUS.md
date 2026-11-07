# STATUS — Tests

**2026-11-07: 79 tests passed in the local Python 3.12.7 environment.**

- `test_code_layout.py`: d=3/5 CSS ranks/commutation/logical pairing and immutability,
  invalid specifications, GF(2)-versus-real rank, N/Z direction/control/target,
  local mappings, counts, and explicit pinned-reference d=3 support fixture.
- `test_flows.py`: full signed check/both-logical flow counts, init/readout discarded
  boundaries, ChunkLoop composition, ideal DEM/sampling, and deliberately corrupted
  gate/record/sign verification failures.
- `test_memory.py`: d=3/5, one/two/three patches and X/Z/mixed bases, SE rounds 1/3/5,
  exact detector/observable raw parity, first/intermediate/terminal records, physical
  distance 3/5 in both bases (compared with Stim's built-in memory distance),
  lifecycle/frame/preparation syndrome, registration-order invariance, final-index
  reordering, collisions, unequal rounds, waiting and mixed-phase operation layers.
  Adding a random preparation-sector outcome as a detector is rejected by Stim.
- `test_noise.py`: exact fault channels/targets/probabilities, concurrent idle,
  reset/result errors, one-qubit upstream rule, type/instance replacement, waiting
  and retired blocks, zero-noise equality, no reinjection, metadata preservation,
  and seeded noisy smoke sampling without statistical thresholds.
- `test_scaffold.py`: retained package import smoke test, renamed to reflect the
  now-functional public memory API.

Executed: `python -m pytest` -> **79 passed in 33.48 s**;
`python -m ruff check src tests` -> **all checks passed**. Build and the two-patch
example also pass; see root STATUS for versions and complete evidence.

No decoder/LER benchmark, Clifford/teleportation-frame test, or other code-family
physics is implemented. CI is configured for Ubuntu/Windows Python 3.11/3.12;
remote jobs have not run during this task. No upstream tests or sources were edited.

History: initial import-only scaffold -> full memory-core physics suite on 2026-11-07.
