# Development environment and workflow

The repository contains placeholders, packaging, and a smoke test. The setup below installs a development environment; it does not create working QEC circuit generators.

## Windows, PowerShell

```powershell
cd logical_to_stim_converter
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
```

If PowerShell blocks script activation, use `cmd.exe` with `.venv\Scripts\activate.bat`, or invoke `.venv\Scripts\python.exe` directly. Do not weaken execution policy globally just to activate this environment.

## Conda alternative

```powershell
conda create -n logical_to_stim python=3.11 -y
conda activate logical_to_stim
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
```

For Linux/macOS, create and activate a normal `.venv`, then run the same `pip`, `pytest`, and `ruff` commands. Use Python 3.11+ but verify that your selected Python version is supported by installed Stim wheels.

## Reference source in `external_lib`

Suggested local folders (the contents are **not** provided):

```text
external_lib/
  stim/           # optional full Stim repository; stimflow is at glue/stimflow
  surface-sim/    # https://github.com/MarcSerraPeralta/surface-sim
  Hex/            # https://github.com/AKTKN/Hex
  lomatching/     # https://github.com/MarcSerraPeralta/lomatching
```

The `.gitignore` excludes these folders from accidental commits. Add a source revision/commit to `external_lib/STATUS.md` when copied; do not assume an unpinned checkout stays compatible. For stimflow from a Stim checkout, inspect `external_lib/stim/glue/stimflow/setup.py` and its dependencies. It is not a regular declared PyPI dependency of this project. When you deliberately choose a revision, either install the local stimflow package (if its checked-out build configuration supports it) or add its `src` path to `PYTHONPATH` **in your local environment**. Do not put absolute Windows paths in project code.

## Git upload from the local PC

```powershell
git init
git add .
git status
git commit -m "Initialize logical_to_stim_converter scaffold"
git branch -M main
# Create a remote repository first, then:
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

`external_lib` source contents should not appear in `git status` by default. If you intentionally want to version upstream sources, choose pinned submodules/subtrees or explicit vendor policy first.

## Codex implementation cycle

1. Read root `AGENTS.md`, global `STATUS.md`, `docs/architecture.md`, and the destination folder's `AGENTS.md` + `STATUS.md`.
2. Implement **one narrowly specified milestone**; check pinned upstream APIs before adapter work.
3. Add deterministic unit/physics/flow tests, run `pytest` and `ruff` (CI currently runs these on Ubuntu/Python 3.11).
4. Update the affected folder's `STATUS.md` and global `STATUS.md` with exact files changed, behavior verified, and remaining limitations.
5. Review changes and commit them. Keep scientific claims conditional until validated on actual Stim circuits.

## Packaging notes

- Distribution name: `logical-to-stim-converter`.
- Python import: `logical_to_stim_converter`.
- Present version: `0.0.0` (scaffold; **not production-ready**).
- Runtime dependency declarations provide Stim/NumPy/SciPy groundwork only; do not imply that integrations are implemented.
- No license has yet been chosen.
