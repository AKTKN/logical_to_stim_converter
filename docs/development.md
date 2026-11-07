# Development environment and verification

The memory-core implementation uses Python 3.11+ and a `src/` package layout.
Create a local virtual environment and install the editable package:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests examples
python -m build
python examples/two_patch_memory.py
python examples/two_patch_bell_roundtrip.py
python examples/knill_ec_single_round.py
```

In Windows `cmd.exe`, activate with `.venv\Scripts\activate.bat`. Alternatively,
invoke `.venv\Scripts\python.exe` directly. A Conda environment with Python 3.11
or 3.12 also works with the same installation commands; activation-policy changes
are not required.

## Reproducible upstream integration

`pyproject.toml` pins these validated integration dependencies:

- `stim==1.15.0` (wheel).
- `stimflow @ git+https://github.com/quantumlib/Stim.git@ffe0d043598ed5df0851a3e6b4920359a23fafbd#subdirectory=glue/stimflow`
  (`stimflow.__version__ == "1.17.dev0"`).

Git and network access to GitHub are required when pip installs the pinned source
package. The stimflow source checkout itself reports a development Stim version;
we deliberately use the separately pinned **1.15.0** Stim wheel. This combination
is checked using the APIs actually used by this package, not a promise that every
upstream stimflow feature is compatible. NumPy/SciPy and dev tooling retain bounded
minimum versions; this is an integration pin, not a full transitive lockfile.

CI installs directly from these declarations without relying on local paths. It
is configured for Ubuntu and Windows, Python 3.11 and 3.12, with tests, Ruff, build,
and all three memory/Bell/Knill examples. Local verification results/platforms are recorded in STATUS;
CI configuration alone is not evidence that those remote jobs ran.

`surface-sim` commit `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` supplies the
reference for column-major data numbering, check geometry, and N/Z interaction
ordering. The implementation uses its mathematical convention, with explicit
small-distance support fixtures and independent Stim flow/fault checks. It does
not import surface-sim. Hex/lomatching remain references only.

Optional local source checkouts are described in `external_lib/README.md` and
`external_lib/STATUS.md`. Do not edit, vendor, or commit those copies. Package
imports and tests must not depend on their presence or machine-specific paths.

## Contracts to preserve

- Mathematical code matrices contain no physical indices or hardware/noise data.
- Logical ID, block ID, local key, stable `(block_id, local_key)` site identity,
  placement coordinate, and final Stim index are separate.
- Use signed `Chunk.verify()` and `ChunkCompiler`; retain both logical Pauli flows.
  Initialization/readout discard only the explicitly incompatible basis.
- Align disjoint physical layers before computing global idle noise. The current
  adapter expands loops to retain exact record/provenance and timing metadata.
- Export final indices from assembled circuit coordinates, not from local chunks.
- Preserve first conjugate-basis syndrome records without inventing a correction.
- Noise rules replace inherited channels and apply once. Preserve the ideal circuit.
- Public memory inputs use explicit parallel layers and same-basis memory readout.

For every implementation task, read AGENTS/STATUS, add a focused physics or
metadata regression, run the applicable checks, and update affected status files.
No decoder, parser, generic Clifford operation, or scheduling optimization should
be added as an incidental extension. Commit and push at the maintainer's direction
after review and verification. No project license has been chosen.


## M3 regression requirements

Keep the existing memory tests. Add backend-level signed H/CNOT/Pauli proofs at
both distances and all four CNOT orientation pairs, corruption tests, independent
logical truth tables, affine frame tests, cross-block parity and exact noise tests.
The Bell example must independently inspect physical intermediate XX/ZZ and local
expectations, then reconstruct raw final outputs. A gate followed by its own
inverse alone is insufficient evidence of the intended Clifford action.

The pinned dependencies are unchanged for M3. ChunkReflow and Stim signed Pauli
conjugation/tableau APIs are used directly. No local external source import is
required. Commit/push only at explicit maintainer direction; the user authorized
both after this milestone's implementation and verification.

## M5 regression requirements

The development extra pins **PyMatching 2.3.1**; tests import it unconditionally.
It is absent from mandatory runtime dependencies and production imports. CI runs
the full physics suite and all three examples on Ubuntu/Windows Python 3.11/3.12.
The Knill example generates circuits without any decoder.

Keep the 173 M1–M3 regressions. M5 tests must resolve nonzero preparation sectors
from actual semantic records, check the CSS equations, inspect physical Bell and
teleported-state expectations at d=3/5, and preserve encoded reference entanglement.
The explicit-correction reference simulator must remain separate from binary
frame propagation. Exercise all random Bell branches, rotated pairing, subsequent
gates, open artifacts, relocation, stage-boundary rejection, and exact once-only
gate/idle fault locations. No noisy recovery or LER claim follows from the
noiseless final-sector helper. Deferred tasks are in `docs/deferred_work.md`.

## M6-A regression requirements

Retain every M1–M5 physics test. The intentional annotation migration affects
only the explicit Knill region tests: principal circuits now retain global
cross-stage detectors; boundary rejection applies to the derived legacy view.
Preserve CompilerContext's existing affine Pauli rules independently of the new
causal ancestry graph. Add d=3/5 full-detector raw-parity reconstruction and
Stim order checks, spectator/parallel isolation, actual CNOT/reference ancestry,
pre-existing resources, repeated relocation, open continuation, noisy hypotheses
and negative metadata/edge/sign tests. Compare all physical/noise instructions
between canonical and derived views. Pinned public FlowMetadata tags carry IDs;
keep detector coordinates at three dimensions. No external source is modified.
