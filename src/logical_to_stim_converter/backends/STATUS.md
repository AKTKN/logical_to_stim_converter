# STATUS — Backends

**2026-11-07: RotatedSurfaceCodeBackend memory path implemented and verified.**

`surface_code.py` constructs a verified stimflow StabilizerCode, signed transversal
initialization/readout chunks, and one six-layer N/Z syndrome-measurement chunk.
The full stabilizer set and both logical Pauli flows are declared. Initialization
and terminal boundaries explicitly discard only the incompatible basis.

Validated dependency combination: Stim wheel 1.15.0 plus stimflow 1.17.dev0 from
Stim commit `ffe0d043598ed5df0851a3e6b4920359a23fafbd`. Surface-sim commit
`493f800a3b4e9f80a6a569eb92d3c962dd6b09ad` is a source geometry/schedule
reference, not a runtime dependency. No external source was modified.

Evidence: signed chunks at d=3/5, X/Z boundaries, corrupted gate/record/sign
rejection, ideal memory sampling/DEM, and noisy circuit fault distance d=3/5.
Exact test run results are in root STATUS. `color_code.py` remains a placeholder;
its docstring was wrapped only to remove an existing Ruff error.

Deferred: transversal H/CNOT, other layouts/bases/code families, Bell/Knill gadgets.
History: 2026-11-07 scaffold -> first verified memory backend.
