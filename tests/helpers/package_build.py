"""Private build trees keep wheel/sdist checks safe under pytest-xdist."""

import shutil
from pathlib import Path


def copy_package_source(destination: Path) -> Path:
    """Copy build inputs without environments, build products or reference clones."""
    root = Path(__file__).resolve().parents[2]
    destination.mkdir()
    for name in ("pyproject.toml", "MANIFEST.in", "README.md", "AGENTS.md", "STATUS.md"):
        shutil.copy2(root / name, destination / name)
    for name in ("src", "docs", "tests", "examples"):
        shutil.copytree(
            root / name, destination / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
        )
    (destination / "external_lib").mkdir()
    for name in ("README.md", "AGENTS.md", "STATUS.md"):
        shutil.copy2(root / "external_lib" / name, destination / "external_lib" / name)
    return destination
