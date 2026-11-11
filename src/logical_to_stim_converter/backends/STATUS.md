# STATUS — Backends

## Data-wide signed Paulis — 2026-11-11

Added transversal_pauli on every rotated-code data site, with signed Stim
conjugation flows for every check and both logical axes. Tests cover d3/5/7,
X/Y/Z, both H orientations and missing-site negative controls. Representative
pauli implementation remains unchanged. Root STATUS records final evidence.


## M5 verification — 2026-11-07

The unchanged signed memory/Clifford backend primitives now support BellStatePrep
and KnillEC through composition. No dedicated Knill physical implementation or
upstream source modification was added. Required d=3/5 resource/teleportation
physics and all orientation pairings are verified by the new tests; root STATUS
records final evidence. Other code families remain deferred.

## M3 update — 2026-11-07

M3: surface_code.py now verifies transversal H, CNOT, and physical X/Y/Z.
H is a physical data-H layer plus a binary orientation change; the clockwise
code template is metadata, with fixed physical sites and no implicit SWAP. The
next SE flips bases/CX directions at the same ancillas and physical edge layers.
CNOT uses canonical-coordinate pairing in each current frame, with all four
orientation pairs supported at equal distance. Stim conjugation supplies complete
signed check/logical flows; ChunkReflow restores the canonical check basis and
proves the intended logical action modulo checks. Syndrome-dependent H representative
corrections are exposed as symbolic check products. Different distances, invalid
orientations, unsupported local geometry, and overlapping operands are rejected.
Physical Pauli Y combines X/Z with Y on the intersection, up to global phase.

Evidence: the extended 173-test suite, Ruff, and both examples; exact final
commands/results are in root STATUS. Dependencies remain pinned to Stim 1.15.0
and stimflow commit ffe0d043598ed5df0851a3e6b4920359a23fafbd. External
source trees are unchanged.

## Prior memory implementation record

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
