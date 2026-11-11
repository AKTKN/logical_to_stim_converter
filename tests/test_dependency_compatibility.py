"""Dependency acceptance changes must preserve frozen bytes and source provenance."""

import importlib.metadata
import json
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
import stim
from packaging.requirements import Requirement

from validation.golden_knill.fixtures import FIXTURES as KNILL_FIXTURES
from validation.golden_knill.fixtures import verify_reference_fixture
from validation.golden_memory.normalize import Mismatch
from validation.golden_memory.run import FIXTURES as MEMORY_FIXTURES
from validation.golden_memory.run import verify_fixture

ORACLES = [(verify_fixture, MEMORY_FIXTURES), (verify_reference_fixture, KNILL_FIXTURES)]


@pytest.mark.parametrize("verify,directory", ORACLES, ids=["memory", "knill"])
@pytest.mark.parametrize(
    "installed,accepted",
    [
        ("1.15.0", True),
        ("1.16.0", True),
        ("1.100.0", True),
        ("1.15.0.post1", True),
        ("1.15.0+build1", True),
        ("1.16.0rc1", True),
        ("1.15.0rc1", False),
        ("1.14.999", False),
        ("1.9.0", False),
    ],
)
def test_golden_stim_minimum_is_pep440_and_keeps_generation_metadata(
    verify, directory, installed, accepted, monkeypatch
):
    # Establish a valid circuit/fixture baseline with the actual installed wheel.
    baseline = verify(3, "Z")
    manifest = directory / "manifest.json"
    before = manifest.read_bytes()
    monkeypatch.setattr(stim, "__version__", installed)
    if accepted:
        assert verify(3, "Z") == baseline
    else:
        with pytest.raises(Mismatch, match="below required minimum 1.15.0"):
            verify(3, "Z")
    assert manifest.read_bytes() == before


@pytest.mark.parametrize("verify,directory", ORACLES, ids=["memory", "knill"])
def test_golden_source_commit_remains_exact(verify, directory, monkeypatch):
    verify(3, "Z")
    before = (directory / "manifest.json").read_bytes()
    original = importlib.metadata.distribution

    def wrong_source(name):
        actual = original(name)
        if name != "stimflow":
            return actual

        def read_text(filename):
            text = actual.read_text(filename)
            if filename == "direct_url.json":
                direct = json.loads(text)
                direct["vcs_info"]["commit_id"] = "0" * 40
                return json.dumps(direct)
            return text

        return SimpleNamespace(version=actual.version, read_text=read_text)

    monkeypatch.setattr(importlib.metadata, "distribution", wrong_source)
    with pytest.raises(Mismatch, match="stimflow source.*mismatch"):
        verify(3, "Z")
    assert (directory / "manifest.json").read_bytes() == before


@pytest.mark.parametrize(
    "name,minimum",
    [("stim", "1.15.0"), ("lark", "1.3.1"), ("pymatching", "2.3.1"), ("pytest-xdist", "3.8.0")],
)
def test_declared_dependency_minimums(name, minimum):
    project = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    requirements = [
        Requirement(text)
        for text in (project["dependencies"] + project["optional-dependencies"]["dev"])
    ]
    requirement = next(r for r in requirements if r.name == name)
    assert str(requirement.specifier) == f">={minimum}"
