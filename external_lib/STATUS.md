# STATUS — Local reference libraries

**2026-11-07:** All four reference repositories cloned locally from the URLs in
`README.md`. These are source references only: no external package was installed,
modified, or integrated. Commits below identify the inspected snapshots, not
validated dependency pins.

| Library | Local folder | Revision / commit | API/compatibility notes | State |
|---|---|---|---|---|
| Stim / stimflow | `stim/` | `ffe0d043598ed5df0851a3e6b4920359a23fafbd` | `main`; Stim and stimflow setup metadata report `1.17.dev0`; stimflow has no backwards-compatibility guarantee | Cloned; runtime compatibility unverified |
| surface-sim | `surface-sim/` | `493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` | `main`; metadata version `0.11.0`, Python >=3.10, Stim >=1.15.0 | Cloned; runtime compatibility unverified |
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
