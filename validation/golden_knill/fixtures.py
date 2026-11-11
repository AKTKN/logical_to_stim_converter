"""Read-only fixture verification and explicit, independent oracle maintenance."""

import hashlib
import importlib.metadata
import json
import subprocess
from pathlib import Path

import stim
from packaging.version import Version

ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures"
HEX_COMMIT = "5de58f2f80791054411ad3c0885a4fe3671ed56a"
STIMFLOW_COMMIT = "ffe0d043598ed5df0851a3e6b4920359a23fafbd"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_name(distance, basis, open_output=False):
    return f"same_d{distance}_{basis.lower()}_{'open' if open_output else 'closed'}.stim"


def hex_name(distance, basis, bit=0):
    return f"hex_d{distance}_{basis.lower()}_bit{bit}.json"


def counts(circuit):
    addressed = {
        target.value
        for instruction in circuit.flattened()
        if instruction.name
        not in ("QUBIT_COORDS", "DETECTOR", "OBSERVABLE_INCLUDE", "SHIFT_COORDS")
        for target in instruction.targets_copy()
        if target.is_qubit_target
    }
    coordinates = circuit.get_final_qubit_coordinates()
    return {
        "occupied_sites": len(coordinates) if coordinates else len(addressed),
        "addressed_physical_sites": len(addressed),
        "native_coordinate_annotations": len(coordinates),
        "qubit_index_width": circuit.num_qubits,
        "measurements": circuit.num_measurements,
        "detectors": circuit.num_detectors,
        "observables": circuit.num_observables,
        "ticks": circuit.num_ticks,
        "CX_pairs": sum(
            len(inst.targets_copy()) // 2 for inst in circuit.flattened() if inst.name == "CX"
        ),
    }


def environment():
    result = {}
    for name in (
        "logical-to-stim-converter",
        "stim",
        "stimflow",
        "numpy",
        "scipy",
        "pymatching",
        "pytest",
        "pytest-xdist",
        "ldpc",
        "stimbposd",
        "sinter",
    ):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "not installed (optional live extraction dependency)"
    result["stimflow_direct_url"] = json.loads(
        importlib.metadata.distribution("stimflow").read_text("direct_url.json")
    )
    return result


def verify_manifest(directory=FIXTURES):
    from validation.golden_memory.normalize import require

    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["schema"] == 1, "Knill fixture manifest schema mismatch")
    require(
        Version(stim.__version__) >= Version("1.15.0"),
        f"Knill fixture Stim version {stim.__version__} is below required minimum 1.15.0",
    )
    require(
        importlib.metadata.version("stimflow") == manifest["environment"]["stimflow"],
        "Knill fixture stimflow version mismatch",
    )
    direct = json.loads(importlib.metadata.distribution("stimflow").read_text("direct_url.json"))
    require(
        direct["vcs_info"]["commit_id"] == manifest["stimflow_source_commit"],
        "Knill fixture stimflow source mismatch",
    )
    for name, digest in manifest["generator_sources"].items():
        require(
            sha256(ROOT / name) == digest,
            f"Knill independent generator source changed: {name}; review fixtures explicitly",
        )
    return manifest


def verify_file(name, directory=FIXTURES):
    from validation.golden_memory.normalize import require

    manifest = verify_manifest(directory)
    path = directory / name
    expected = manifest["fixtures"][name]
    require(sha256(path) == expected["sha256"], f"Knill fixture checksum mismatch: {name}")
    return path


def verify_reference_fixture(distance, basis, open_output=False, directory=FIXTURES):
    from validation.golden_memory.normalize import require

    from .reference_same_schedule import build_reference

    path = verify_file(reference_name(distance, basis, open_output), directory)
    circuit = stim.Circuit(path.read_text(encoding="utf-8"))
    generated = build_reference(distance, basis, open_output=open_output).circuit
    require(circuit == generated, f"Independent direct-Stim fixture drift: {path.name}")
    return circuit


def verify_hex_fixture(distance, basis, bit=0, directory=FIXTURES):
    from .hex_adapter import load_hex_bundle

    path = verify_file(hex_name(distance, basis, bit), directory)
    return load_hex_bundle(path)


def regenerate_fixtures(hex_repo, directory=FIXTURES):
    """Explicit maintenance only: never import or serialize a DUT construction."""
    from validation.golden_memory.normalize import require

    from .hex_adapter import extract_hex, save_hex_bundle
    from .reference_same_schedule import build_reference

    repo = Path(hex_repo).resolve()
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    require(
        commit == HEX_COMMIT, f"Hex source commit mismatch: expected={HEX_COMMIT}, actual={commit}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    entries = {}
    for d in (3, 5):
        for basis in ("X", "Z"):
            for open_output in (False, True):
                name = reference_name(d, basis, open_output)
                bundle = build_reference(d, basis, open_output=open_output)
                path = directory / name
                path.write_text(str(bundle.circuit) + "\n", encoding="utf-8", newline="\n")
                entries[name] = {
                    "oracle": "independent_direct_stim",
                    "sha256": sha256(path),
                    "arguments": {"distance": d, "basis": basis, "open_output": open_output},
                    "counts": counts(bundle.circuit),
                }
            for bit in (0, 1):
                name = hex_name(d, basis, bit)
                bundle = extract_hex(d, basis, bit=bit, hex_repo=repo)
                path = directory / name
                save_hex_bundle(bundle, path)
                entries[name] = {
                    "oracle": "actual_pinned_hex_surface_code_true",
                    "sha256": sha256(path),
                    "arguments": {"distance": d, "basis": basis, "bit": bit, "surface_code": True},
                    "closed_counts": counts(bundle.closed_circuit),
                    "open_counts": counts(bundle.open_circuit),
                    "allocated_patch_sites": 3 * (2 * d * d - 1),
                }
    generators = ("spec.py", "reference_same_schedule.py", "reference_noise.py", "hex_adapter.py")
    manifest = {
        "schema": 1,
        "creator": "Explicit independent oracle maintenance; no DUT export",
        "converter_baseline_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "hex_source_commit": commit,
        "hex_source_version": "0.1.0",
        "stimflow_source_commit": STIMFLOW_COMMIT,
        "environment": environment(),
        "generator_sources": {name: sha256(ROOT / name) for name in generators},
        "fixtures": entries,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest
