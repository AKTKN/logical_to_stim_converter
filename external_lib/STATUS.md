# STATUS — Local reference libraries

**2026-11-07:** All four reference repositories cloned locally from the URLs in
`README.md`. The source trees remain read-only references. Stim/stimflow now have validated
memory integration pins; the other libraries remain uninstalled and unintegrated.
No external source was modified.

| Library | Local folder | Revision / commit | API/compatibility notes | State |
|---|---|---|---|---|
| Stim / stimflow | `stim/` | `ffe0d043598ed5df0851a3e6b4920359a23fafbd` | `main`; stimflow metadata version `1.17.dev0`, used with the separately pinned Stim 1.15.0 wheel | Memory APIs/flows/noise verified |
| surface-sim | `surface-sim/` | `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` | `main`; metadata version `0.11.0`, Python >=3.10, Stim >=1.15.0 | Source geometry/schedule checked; no runtime adapter |
| Hex | `Hex/` | `5de58f2f80791054411ad3c0885a4fe3671ed56a` | Default branch `hex-adaptive`; distribution `hex-qec` version `0.1.0` | Cloned; runtime compatibility unverified |
| lomatching | `lomatching/` | `b55a7a65969a106a547622287b620f0da2cb5e39` | `main`; metadata version `0.3.0`, Python >=3.10 | Cloned; runtime compatibility unverified |

## Acquisition and inspection

Full Git clones (not shallow), run from the project root:

```text
git clone https://github.com/quantumlib/Stim external_lib/stim
git clone https://github.com/MarcSerraPeralta/surface-sim external_lib/surface-sim
git clone https://github.com/AKTKN/Hex external_lib/Hex
git clone https://github.com/MarcSerraPeralta/lomatching external_lib/lomatching
```

- Verified origin URLs, full HEAD hashes, current branches, clean working trees,
  and no declared submodules for all four clones.
- Read upstream README/build metadata. Confirmed stimflow source and setup at
  `stim/glue/stimflow/`; its `requirements.txt` lists `pygltflib` and `stim`.
  The planned chunk, flow, code, patch, and noise classes exist in the source;
  their behavior and cross-library compatibility have not been tested.
- No installation performed. For later deliberate local installation, inspected
  metadata provides `python -m pip install ./external_lib/stim/glue/stimflow`,
  `python -m pip install ./external_lib/surface-sim`,
  `python -m pip install ./external_lib/Hex`, and
  `python -m pip install ./external_lib/lomatching` as source-install entry points.
  These commands are untested and may resolve additional dependencies; installing
  stimflow does not itself install the cloned Stim revision.
- Next: choose validated integration revisions and test actual physical/flow APIs
  before implementing adapters. No physics or compiler functionality was added.

Update this file whenever a local library is cloned/updated or integration behavior is verified. Local reference copies are intentionally gitignored.

## Memory integration verification — 2026-11-07

- Installed the declared VCS dependency for stimflow from the exact Stim commit
  above and the Stim 1.15.0 wheel in the project virtual environment. The cloned
  Stim source's own 1.17.dev0 version is **not** the installed Stim wheel version.
- Validated public ChunkBuilder, Chunk/ChunkLoop, ChunkCompiler, StabilizerCode,
  Patch/Tile/PauliMap/Flow, NoiseModel/NoiseRule, tags, and final circuit mappings
  for the memory path. Signed flow verification, ideal/noisy DEMs, raw record
  parities, and d=3/5 fault-distance checks pass. See root STATUS for the full run.
- Inspected StimCircuitLoom: it requires matching physical instruction sequences.
  Mixed-basis boundaries use a small public-API physical-layer adapter instead.
- Checked the pinned surface-sim source's standard local numbering, boundary
  check geometry, and N/Z ordering; explicit d=3 fixtures are in the test suite.
  No surface-sim runtime import or adapter compatibility is claimed.
- Known upstream behavior: flow fusion averages non-None centers. Passive identity
  flows set center=None to avoid moving boundary detector coordinates. Fragment
  ChunkLoops are verified then expanded for exact per-layer/record metadata.
- CI installs the pinned VCS dependency directly; no external_lib path is required.
  The earlier untested source-install notes above describe the acquisition stage.
  Hex/lomatching remain untouched references; all four source working trees stay clean.
