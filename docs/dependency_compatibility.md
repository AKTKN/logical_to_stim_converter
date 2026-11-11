# Minimum dependency versions and compatibility verification

## Policy and scope

The dependency-compatibility change is based on converter commit
`64e139d16dd5e66dd8ecb33a1baaf5ca4364d302`, on dedicated branch
`dependencies/minimum-version-compatibility` (2026-11-11). Package version 0.0.1
is unchanged. The four exact PyPI requirements become:

| Dependency | Requirement | Layer |
| --- | --- | --- |
| Stim | `stim>=1.15.0` | Runtime |
| Lark | `lark>=1.3.1` | Runtime |
| PyMatching | `pymatching>=2.3.1` | Development/examples |
| pytest-xdist | `pytest-xdist>=3.8.0` | Development |

All previously declared minimums remain unchanged. No upper bounds are added.
The stimflow source requirement remains exactly
`stimflow @ git+https://github.com/quantumlib/Stim.git@ffe0d043598ed5df0851a3e6b4920359a23fafbd#subdirectory=glue/stimflow`.
No circuit-generation, noise-insertion, decoding or Pauli-frame algorithm changes.
The ordinary-memory example's decoder label now reports the installed PyMatching
version. No other repository is modified.

Modified files are confined to dependency declarations, compatibility checks,
CI, version reporting and documentation:

- `pyproject.toml` and `.github/workflows/ci.yml`: minimums and the eight-job matrix.
- `validation/golden_memory/run.py`, `validation/golden_knill/fixtures.py`:
  PEP 440 acceptance while retaining provenance and physics checks.
- `tests/test_dependency_compatibility.py`, `tests/test_lstim_packaging.py`:
  dependency acceptance/source regressions and emitted metadata.
- `examples/memory_offline_decoding.py`: installed decoder version in the label.
- `README.md`, `docs/development.md`, `docs/architecture.md`, `docs/lstim_v1.md`,
  `docs/resource_preparation_noise.md`, `docs/research_beta_0.0.1_plan_and_verification.md`,
  both golden-suite READMEs and this record: current policy and historical context.
- Root, tests and package-root `AGENTS.md`; root, docs, examples, package-root,
  tests, validation and both golden-suite `STATUS.md`: guidance and evidence.

## Version acceptance and frozen references

Golden-memory and golden-Knill acceptance now compares
`Version(stim.__version__) >= Version("1.15.0")` using `packaging.version.Version`.
`packaging` is already supplied by the development pytest dependency. Generation
metadata is historical provenance, not the installed-version acceptance floor.
The existing stimflow package-version and exact Git-commit checks are retained.

All 20 oracle payloads and both manifests retain their original bytes, SHA-256
digests, source identities and Stim 1.15.0 generation metadata. No fixture is
regenerated. Generator hashes, signed physical/logical flows, complete affine
constraints, physical moments, noise-location multiplicities/probabilities,
forced-fault responses, survivor frames and exact native DEM comparisons remain
unchanged. The wheel metadata check now requires `lark>=1.3.1` and still compares
all emitted runtime requirements against pyproject.toml.

Twenty-four focused regressions exercise both version gates with 1.15.0, 1.16.0,
1.100.0, post/local releases and prereleases, reject versions below the original
minimum, keep manifest bytes unchanged and still reject a wrong stimflow commit.
The actual two-wheel runs below establish physics compatibility independently
of those version-string acceptance tests.

## Separate installed environments

Local verification uses Linux/WSL2, Python 3.12.7. The existing `.venv` is refreshed
using normal `pip install -e ".[dev]" stim==1.15.0` resolution, retaining its
installed dependency versions. A
separate fresh `/tmp/ltstim-dependency-stim116` venv resolves `.[dev]` together with
`stim==1.16.0`. Exact selectors here choose test environments; the package metadata
has minimum requirements.

| Package | Stim 1.15.0 environment | Stim 1.16.0 environment |
| --- | --- | --- |
| Converter | 0.0.1 editable | 0.0.1 editable |
| Stim | 1.15.0 | 1.16.0 |
| stimflow | 1.17.dev0, exact commit above | 1.17.dev0, exact commit above |
| PyMatching | 2.3.1 | 2.4.0 (fresh dependency resolution) |
| Lark | 1.3.1 | 1.3.1 |
| NumPy / SciPy | 2.5.4 / 1.18.1 | 2.5.4 / 1.18.1 |
| pytest / pytest-xdist | 9.2.0 / 3.8.0 | 9.2.0 / 3.8.0 |
| packaging / build / Ruff | 26.3 / 1.6.1 / 0.17.4 | 26.3 / 1.6.1 / 0.17.4 |

Both editable installations and `python -m pip check` passed. Both environments
report the exact pinned stimflow VCS commit in installed `direct_url.json`.

## Commands and results

Use each environment's Python executable for these commands:

```sh
python -m pip check
python -m pytest -n 8
python -m pytest -n 8 tests/test_dependency_compatibility.py \
  tests/test_validation_golden_memory.py tests/test_validation_golden_knill.py \
  tests/test_validation_golden_knill_hex.py tests/test_validation_golden_knill_fixtures.py \
  tests/test_lstim_packaging.py
python -m ruff check src tests examples validation
python -m build --outdir /tmp/ltstim-deps-build-VERSION
```

The focused command contains all **177** existing golden-memory/Knill tests,
**24** dependency regressions and the existing built-wheel/sdist/isolated-consumer
test. It validates actual circuits/DEMs under the selected Stim wheel, with
unchanged physical assertions. Tests use eight xdist workers; the two full runs
execute sequentially. Build output is kept outside the tracked source tree.

| Verification | Stim 1.15.0 / PyMatching 2.3.1 | Stim 1.16.0 / PyMatching 2.4.0 |
| --- | --- | --- |
| Normal editable dependency resolution | PASS | PASS, fresh venv |
| `pip check` | PASS | PASS |
| Complete `pytest -n 8` | **1,598 passed, 538.12 s** | **1,598 passed, 482.09 s** |
| Focused golden/dependency/packaging `pytest -n 8` | **202 passed, 114.54 s** | **202 passed, 117.26 s** |
| Ruff, src/tests/examples/validation | PASS | PASS |
| Source distribution and wheel build | PASS, 3.98 s | PASS, 3.88 s |
| Wheel minimums and exact stimflow URL audit | PASS | PASS |

**Compatibility failures: none observed.** All existing 1,574 tests and all
24 new cases pass in both environments, without skips. Every existing golden
physics assertion remains intact. Frozen payload/manifest diffs against the
baseline are empty; source/generator and fixture SHA-256 checks pass. Documentation
links and whitespace checks pass. No newer-version discrepancy was hidden by
fixture maintenance, decomposition, probability rounding or changed algorithms.

Builds used isolated PEP 517 build environments and produced wheel/sdist pairs in
`/tmp/ltstim-deps-build-115` and `/tmp/ltstim-deps-build-116`. Both wheels' parsed
metadata contains the four exact requested minimum constraints and the original
stimflow source URL, and permits both tested Stim releases. The existing isolated
wheel consumer regression also verifies runtime-source/grammar bytes, metadata,
real memory/Knill circuits and DEMs without optional decoder/repository imports.

## CI and compatibility limits

`.github/workflows/ci.yml` now crosses Stim 1.15.0/1.16.0 with Python 3.11/3.12
and Ubuntu/Windows: **eight independent jobs**. Each job installs the selected
Stim release with `.[dev]`, checks its actual PEP 440 version and dependency
consistency, runs the entire suite including both golden suites, lints
src/tests/examples/validation, builds both distributions and retains all existing
workflow examples. The exact Stim matrix selectors are intentional isolation,
not exact requirements imposed on package consumers.

Remote jobs for this unpushed dependency branch have not run. Local evidence is
Linux/Python 3.12; CI configuration does not establish Windows/Python 3.11 results.
Later dependency versions must pass the same assertions. A changed circuit, DEM,
flow or fault response is a compatibility failure to investigate, never grounds
for automatic fixture regeneration or relaxed physics checks. Broader future
versions are permitted by metadata but are not certified by these two test runs.
