# Local reference source (`external_lib`)

This folder is reserved for user-supplied, locally cloned copies of reference implementations. **No third-party source code is bundled with the scaffold.** Copies are ignored by the root `.gitignore` by default, while this README and the local `AGENTS.md`/`STATUS.md` remain tracked.

**Local workspace (2026-11-07):** All four repositories below have been cloned
for source inspection. See [`STATUS.md`](STATUS.md) for exact commits and branches.
The declared Stim/stimflow dependencies are now installed and validated for memory;
the local source trees themselves remain read-only. Other libraries are references
only. See STATUS for the exact source-versus-wheel version distinction.

Suggested sources:

| Local folder | Upstream | Planned use |
|---|---|---|
| `stim/` | https://github.com/quantumlib/Stim | `glue/stimflow`: `Chunk`, flow verification, compiler, noise classes. |
| `surface-sim/` | https://github.com/MarcSerraPeralta/surface-sim | Surface-code layout/SE/generator reference and possible adapter. |
| `Hex/` | https://github.com/AKTKN/Hex | Existing Knill EC, Bell measurement, and other gadget reference. |
| `lomatching/` | https://github.com/MarcSerraPeralta/lomatching | Optional downstream logical-observable decoder adapter. |

Do not assume the presence of any directory until you add it locally. Record the exact revision, installation procedure, and compatibility observations in [`STATUS.md`](STATUS.md). Avoid editing these copies as part of implementing this package; prefer wrappers/adapters in `src/`.

If you later choose to distribute third-party source as part of this repository, review their licenses and adopt an explicit submodule/vendor policy before changing `.gitignore`.
