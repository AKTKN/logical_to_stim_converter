"""Frozen Knill oracles, import independence, LF checkout and read-only CLI.

The private Git checkout simulates Windows newline settings on the current
platform. It does not claim execution on an actual Windows operating system.
"""

import hashlib
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from validation.golden_knill.fixtures import (
    FIXTURES,
    HEX_COMMIT,
    counts,
    hex_name,
    reference_name,
    sha256,
    verify_hex_fixture,
    verify_manifest,
    verify_reference_fixture,
)
from validation.golden_knill.reference_same_schedule import build_reference
from validation.golden_memory.normalize import Mismatch

ROOT = Path(__file__).resolve().parents[1]
DIRECT_CASES = [(d, b, mode) for d in (3, 5) for b in "XZ" for mode in (False, True)]
HEX_CASES = [(d, b, bit) for d in (3, 5) for b in "XZ" for bit in (0, 1)]


def _fixture_bytes():
    return {path.name: path.read_bytes() for path in FIXTURES.iterdir() if path.is_file()}


def _reject_network(*args, **kwargs):
    raise AssertionError("Frozen Knill fixture verification attempted network access")


@pytest.mark.parametrize("distance,basis,open_output", DIRECT_CASES)
def test_frozen_independent_direct_oracle(distance, basis, open_output, monkeypatch):
    monkeypatch.setattr(socket, "create_connection", _reject_network)
    monkeypatch.setattr(socket.socket, "connect", _reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _reject_network)
    before = _fixture_bytes()
    manifest = verify_manifest()
    name = reference_name(distance, basis, open_output)
    expected = manifest["fixtures"][name]
    circuit = verify_reference_fixture(distance, basis, open_output)
    assert circuit == build_reference(distance, basis, open_output=open_output).circuit
    assert expected["oracle"] == "independent_direct_stim"
    assert expected["arguments"] == {
        "distance": distance,
        "basis": basis,
        "open_output": open_output,
    }
    assert counts(circuit) == expected["counts"]
    assert sha256(FIXTURES / name) == expected["sha256"]
    assert _fixture_bytes() == before


@pytest.mark.parametrize("distance,basis,bit", HEX_CASES)
def test_frozen_actual_hex_oracle_without_upstream_import(distance, basis, bit, monkeypatch):
    monkeypatch.setattr(socket, "create_connection", _reject_network)
    monkeypatch.setattr(socket.socket, "connect", _reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _reject_network)
    before = _fixture_bytes()
    manifest = verify_manifest()
    name = hex_name(distance, basis, bit)
    expected = manifest["fixtures"][name]
    bundle = verify_hex_fixture(distance, basis, bit)
    assert (bundle.distance, bundle.basis, bundle.bit) == (distance, basis, bit)
    assert bundle.provenance["commit"] == HEX_COMMIT
    assert bundle.provenance["surface_code"] is True
    assert set(bundle.sections) == {
        "input",
        "prep_A",
        "prep_B",
        "entangle",
        "bell_measure",
        "readout",
    }
    assert bundle.circuit.num_measurements > 0
    assert expected["oracle"] == "actual_pinned_hex_surface_code_true"
    assert expected["arguments"] == {
        "distance": distance,
        "basis": basis,
        "bit": bit,
        "surface_code": True,
    }
    assert sha256(FIXTURES / name) == expected["sha256"]
    assert _fixture_bytes() == before


def test_manifest_covers_all_reviewed_oracles_without_rewriting():
    before = _fixture_bytes()
    manifest = verify_manifest()
    names = {reference_name(*case) for case in DIRECT_CASES}
    names.update(hex_name(*case) for case in HEX_CASES)
    assert set(manifest["fixtures"]) == names
    assert set(before) == names | {"manifest.json"}
    assert manifest["hex_source_commit"] == HEX_COMMIT
    assert "no DUT export" in manifest["creator"]
    assert set(manifest["generator_sources"]) == {
        "spec.py",
        "reference_same_schedule.py",
        "reference_noise.py",
        "hex_adapter.py",
    }
    assert _fixture_bytes() == before


@pytest.mark.parametrize("oracle", ["direct", "hex"])
def test_corrupted_frozen_oracle_fails_its_checksum(tmp_path, oracle):
    directory = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, directory)
    name = reference_name(3, "Z") if oracle == "direct" else hex_name(3, "Z")
    path = directory / name
    if oracle == "direct":
        verify_reference_fixture(3, "Z", directory=directory)
    else:
        verify_hex_fixture(3, "Z", directory=directory)
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(Mismatch, match=f"Knill fixture checksum mismatch: {name}"):
        if oracle == "direct":
            verify_reference_fixture(3, "Z", directory=directory)
        else:
            verify_hex_fixture(3, "Z", directory=directory)
    assert (directory / "manifest.json").read_bytes() == (FIXTURES / "manifest.json").read_bytes()


def test_independent_build_noise_and_frozen_load_block_production_and_hex_imports():
    script = r"""
import importlib.abc
import socket
import sys

class RejectProduction(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'logical_to_stim_converter', 'hex_qec', 'tests'}:
            raise AssertionError('Golden oracle crossed import boundary: ' + fullname)
        return None

sys.meta_path.insert(0, RejectProduction())
def reject_network(*args, **kwargs):
    raise AssertionError('Golden oracle attempted network access')
socket.create_connection = reject_network
socket.socket.connect = reject_network
socket.socket.connect_ex = reject_network
from validation.golden_knill.reference_same_schedule import build_reference
from validation.golden_knill.reference_noise import FULL_NOISE, ReferenceNoise, add_noise
from validation.golden_knill.fixtures import verify_reference_fixture, verify_hex_fixture
for d in (3, 5):
    for basis in 'XZ':
        for open_output in (False, True):
            bundle = build_reference(d, basis, open_output=open_output)
            add_noise(bundle, FULL_NOISE).detector_error_model()
            for background in (ReferenceNoise(), FULL_NOISE):
                for probability in (0, .003):
                    add_noise(bundle, background, m9_enabled=True,
                              p_st=probability).detector_error_model()
            verify_reference_fixture(d, basis, open_output)
        for bit in (0, 1):
            verify_hex_fixture(d, basis, bit)
assert not any(name.split('.')[0] in {'logical_to_stim_converter', 'hex_qec', 'tests'}
               for name in sys.modules)
print('independent direct/noise/M9/frozen PASS')
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "independent direct/noise/M9/frozen PASS"


def test_frozen_lf_bytes_survive_private_git_crlf_checkout(tmp_path):
    """Exercise actual Git conversion with Windows-like config in a private repo."""
    repository = tmp_path / "newline-check"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)

    def git(*arguments):
        return subprocess.run(
            ["git", "-C", str(repository), *arguments], capture_output=True, check=True
        ).stdout

    git("config", "core.autocrlf", "true")
    git("config", "core.eol", "crlf")
    (repository / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    relative = Path("validation/golden_knill/fixtures")
    destination = repository / relative
    destination.mkdir(parents=True)
    originals = _fixture_bytes()
    for name, data in originals.items():
        assert b"\r\n" not in data, f"Frozen source is not LF: {name}"
        (destination / name).write_bytes(data)
    git("add", ".gitattributes", relative.as_posix())
    paths = [(relative / name).as_posix() for name in originals]
    attributes = git("check-attr", "-z", "text", "eol", "--", *paths).split(b"\0")[:-1]
    assert len(attributes) == 6 * len(paths)
    for offset in range(0, len(attributes), 3):
        _, attribute, value = attributes[offset : offset + 3]
        assert (attribute, value) in ((b"text", b"set"), (b"eol", b"lf"))
    for name in originals:
        (destination / name).unlink()
    git("checkout-index", "--all", "--force")
    for name, original in originals.items():
        restored = (destination / name).read_bytes()
        assert restored == original, f"Git CRLF checkout changed frozen bytes: {name}"
        assert git("show", f":{(relative / name).as_posix()}") == original
        assert hashlib.sha256(restored).hexdigest() == sha256(FIXTURES / name)


def test_same_ideal_cli_stdout_matches_saved_report_and_preserves_fixtures(tmp_path):
    output = tmp_path / "same-ideal.json"
    before = _fixture_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "validation.golden_knill.run",
            "--distance",
            "3",
            "--basis",
            "Z",
            "--level",
            "same-ideal",
            "--workers",
            "1",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report == json.loads(output.read_text(encoding="utf-8"))
    assert report["workers"] == 1
    assert len(report["reports"]) == 2
    assert {item["options"]["open_output"] for item in report["reports"]} == {False, True}
    for item in report["reports"]:
        assert item["status"] == "PASS", item
        assert item["level"] == "same-ideal"
        assert item["distance"] == 3 and item["basis"] == "Z"
        for level in ("B1", "B2"):
            assert item["evidence"]["verified"][level]["passed"]
    assert _fixture_bytes() == before


def test_fixture_regeneration_requires_explicit_pinned_hex_repo(capsys):
    from validation.golden_knill.run import main

    before = _fixture_bytes()
    with pytest.raises(SystemExit) as error:
        main(["--regenerate-fixtures"])
    assert error.value.code == 2
    assert "--regenerate-fixtures requires --hex-repo" in capsys.readouterr().err
    assert _fixture_bytes() == before
