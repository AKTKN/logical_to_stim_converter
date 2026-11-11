"""Deterministic A/B/C driver and explicitly gated fixture maintenance."""

import argparse
import hashlib
import importlib.metadata
import json
import multiprocessing
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

import stim

from .compare import (
    common_noise_equivalence,
    compile_dut,
    exact_schedule_equivalence,
    ideal_semantic_equivalence,
)
from .normalize import require
from .reference_same_schedule import FULL_NOISE, ReferenceNoise, build_reference

FIXTURES = Path(__file__).parent / "fixtures"
UPSTREAM = "ffe0d043598ed5df0851a3e6b4920359a23fafbd"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regenerate_fixtures(directory=FIXTURES):
    """Call only from the explicit --regenerate-fixtures maintenance path."""
    directory.mkdir(parents=True, exist_ok=True)
    entries = {}
    for distance in (3, 5):
        for basis in ("X", "Z"):
            name = f"d{distance}_{basis.lower()}.stim"
            circuit = build_reference(distance, basis)
            path = directory / name
            path.write_text(str(circuit) + "\n", encoding="utf-8", newline="\n")
            entries[name] = {
                "sha256": digest(path),
                "occupied_sites": 2 * distance**2 - 1,
                "measurements": circuit.num_measurements,
                "detectors": circuit.num_detectors,
                "observables": circuit.num_observables,
                "ticks": circuit.num_ticks,
            }
    manifest = {
        "schema": 1,
        "generation_source": "validation/golden_memory/reference_same_schedule.py",
        "generator_sha256": digest(Path(__file__).with_name("reference_same_schedule.py")),
        "converter_baseline_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "stim_version": stim.__version__,
        "stimflow_version": importlib.metadata.version("stimflow"),
        "stimflow_source_commit": UPSTREAM,
        "stimflow_direct_url": json.loads(
            importlib.metadata.distribution("stimflow").read_text("direct_url.json")
        ),
        "provenance": "Independent elementary plaquettes and written physical schedule; "
        "no converter output or third-party source copied. "
        "d3 supports, CSS algebra, four layers, counts and signed flows reviewed in tests.",
        "fixtures": entries,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def verify_fixture(distance, basis, directory=FIXTURES):
    """Read-only: CI never generates or rewrites a fixture."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    name = f"d{distance}_{basis.lower()}.stim"
    path = directory / name
    require(
        digest(path) == manifest["fixtures"][name]["sha256"],
        f"Fixture checksum mismatch {name}; explicit reviewed maintenance required",
    )
    require(
        digest(Path(__file__).with_name("reference_same_schedule.py"))
        == manifest["generator_sha256"],
        "Golden generator source changed; review fixtures",
    )
    require(
        manifest["stim_version"] == stim.__version__
        and manifest["stimflow_version"] == importlib.metadata.version("stimflow"),
        "Golden dependency version mismatch; inspect pinned API and review fixtures",
    )
    installed_source = json.loads(
        importlib.metadata.distribution("stimflow").read_text("direct_url.json")
    )
    require(
        installed_source["vcs_info"]["commit_id"] == manifest["stimflow_source_commit"],
        "Golden stimflow source commit mismatch; inspect pinned API and review fixtures",
    )
    circuit = stim.Circuit(path.read_text(encoding="utf-8"))
    require(
        circuit == build_reference(distance, basis), f"Independent fixture/generator drift {name}"
    )
    return circuit


def run_task(task):
    distance, basis, level = task
    fixture = verify_fixture(distance, basis)
    noise = {
        "A": None,
        "B": ReferenceNoise(reset=0.01, measurement=0.01),
        "C1": None,
        "C2": FULL_NOISE,
    }[level]
    compiled = compile_dut(distance, basis, noise)
    if level == "A":
        report = ideal_semantic_equivalence(compiled, distance, basis)
    elif level == "B":
        report = common_noise_equivalence(compiled, distance, basis)
    else:
        report = exact_schedule_equivalence(
            compiled,
            distance,
            basis,
            noisy=level == "C2",
            reference=fixture if level == "C1" else None,
        )
    return asdict(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance", type=int, choices=(3, 5), default=3)
    parser.add_argument("--basis", choices=("X", "Z"), default="Z")
    parser.add_argument("--level", choices=("A", "B", "C1", "C2", "all"), default="all")
    parser.add_argument("--matrix", action="store_true", help="All four distance/basis pairs")
    parser.add_argument(
        "--workers", type=int, default=8, help="Spawned worker processes (default 8)"
    )
    parser.add_argument("--output", type=Path, help="Write exact structured evidence as JSON")
    parser.add_argument(
        "--regenerate-fixtures",
        action="store_true",
        help="Explicit maintenance: rewrite all four independent fixtures/manifest",
    )
    args = parser.parse_args(argv)
    if args.workers < 1 or args.workers > 8:
        parser.error("--workers must be between 1 and 8")
    if args.regenerate_fixtures:
        regenerate_fixtures()
    cases = (
        [(d, b) for d in (3, 5) for b in ("X", "Z")]
        if args.matrix
        else [(args.distance, args.basis)]
    )
    levels = ("A", "B", "C1", "C2") if args.level == "all" else (args.level,)
    tasks = [(d, b, level) for d, b in cases for level in levels]
    if args.workers == 1:
        reports = list(map(run_task, tasks))
    else:
        with ProcessPoolExecutor(
            max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            reports = list(pool.map(run_task, tasks))
    result = {"schema": 1, "workers": args.workers, "reports": reports}
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
