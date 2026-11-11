"""Parallel, deterministic Knill oracle driver with separate A0–C2 evidence."""

import argparse
import json
import multiprocessing
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

from .fixtures import (
    HEX_COMMIT,
    environment,
    regenerate_fixtures,
    verify_hex_fixture,
    verify_reference_fixture,
)


def _live_hex(bundle, distance, basis, bit, hex_repo):
    # Serialize in a private directory using the same pure fixture adapter;
    # compare actual circuits/matrices, with no decoder output as ground truth.
    import tempfile

    from validation.golden_memory.normalize import require

    from .fixtures import hex_name
    from .hex_adapter import extract_hex, save_hex_bundle

    actual = extract_hex(distance, basis, bit=bit, hex_repo=Path(hex_repo))
    with tempfile.TemporaryDirectory(prefix="knill-hex-audit-") as temp:
        a, b = Path(temp) / "frozen.json", Path(temp) / "live.json"
        save_hex_bundle(bundle, a)
        save_hex_bundle(actual, b)
        require(
            json.loads(a.read_text(encoding="utf-8")) == json.loads(b.read_text(encoding="utf-8")),
            f"Live pinned Hex fixture differs: {hex_name(distance, basis, bit)}",
        )
    return actual


def run_task(task):
    distance, basis, level, options, hex_repo = task
    started = time.perf_counter()
    try:
        if level == "hex-ideal":
            from .compare import check_hex_ideal_semantics

            bit = options["bit"]
            bundle = verify_hex_fixture(distance, basis, bit)
            if hex_repo:
                bundle = _live_hex(bundle, distance, basis, bit, hex_repo)
            report = check_hex_ideal_semantics(distance, basis, bit=bit, hex_bundle=bundle)
        else:
            verify_reference_fixture(distance, basis, options.get("open_output", False))
            if level == "same-ideal":
                from .compare import check_same_schedule_ideal

                report = check_same_schedule_ideal(distance, basis, **options)
            elif level == "ordinary-noise":
                from .compare import check_same_schedule_noise

                report = check_same_schedule_noise(distance, basis, **options)
            else:
                from .compare import check_m9_noise

                report = check_m9_noise(distance, basis, **options)
        return {
            "status": "PASS",
            "level": level,
            "distance": distance,
            "basis": basis,
            "options": options,
            "hex_source": "live+pinned_fixture" if hex_repo else "frozen",
            "evidence": asdict(report),
            "wall_seconds": time.perf_counter() - started,
        }
    except Exception as error:
        return {
            "status": "FAIL",
            "level": level,
            "distance": distance,
            "basis": basis,
            "options": options,
            "error_type": type(error).__name__,
            "diagnostic": str(error),
            "wall_seconds": time.perf_counter() - started,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance", type=int, choices=(3, 5), default=3)
    parser.add_argument("--basis", choices=("X", "Z"), default="Z")
    parser.add_argument(
        "--level", choices=("hex-ideal", "same-ideal", "ordinary-noise", "m9", "all"), default="all"
    )
    parser.add_argument("--matrix", action="store_true", help="Both distances and both bases")
    parser.add_argument(
        "--hex-repo", type=Path, help="Read-only pinned Hex checkout for live audit"
    )
    parser.add_argument("--workers", type=int, default=8, help="1..8 spawned worker processes")
    parser.add_argument(
        "--bit",
        choices=("0", "1", "both"),
        default="both",
        help="Hex ideal input eigenvalue cases (default both)",
    )
    parser.add_argument(
        "--open-output", action="store_true", help="Noise cases omit final B readout"
    )
    parser.add_argument("--p-st", type=float, default=0.003, help="Single M9 case probability")
    parser.add_argument("--background", choices=("zero", "nonzero"), default="nonzero")
    parser.add_argument("--output", type=Path, help="Structured report path")
    parser.add_argument(
        "--regenerate-fixtures",
        action="store_true",
        help="Explicit maintenance: requires actual --hex-repo; rewrites oracles",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be 1..8")
    if args.regenerate_fixtures:
        if args.hex_repo is None:
            parser.error("--regenerate-fixtures requires --hex-repo at the pinned source commit")
        regenerate_fixtures(args.hex_repo)
    if args.hex_repo:
        commit = subprocess.check_output(
            ["git", "-C", str(args.hex_repo), "rev-parse", "HEAD"], text=True
        ).strip()
        if commit != HEX_COMMIT:
            parser.error(f"--hex-repo must be pinned {HEX_COMMIT}, got {commit}")
    cases = (
        [(d, b) for d in (3, 5) for b in ("X", "Z")]
        if args.matrix
        else [(args.distance, args.basis)]
    )
    levels = (
        ("hex-ideal", "same-ideal", "ordinary-noise", "m9") if args.level == "all" else [args.level]
    )
    tasks = []
    for distance, basis in cases:
        for level in levels:
            if level == "hex-ideal":
                options = [
                    {"bit": bit} for bit in ((0, 1) if args.bit == "both" else (int(args.bit),))
                ]
            elif level == "same-ideal":
                options = [{"open_output": mode} for mode in (False, True)]
            elif level == "ordinary-noise":
                options = [
                    {"heterogeneous": heterogeneous, "open_output": args.open_output}
                    for heterogeneous in (False, True)
                ]
            elif args.level == "all":
                options = [
                    {"p_st": probability, "background": background, "open_output": args.open_output}
                    for probability in (0, 0.003)
                    for background in (False, True)
                ]
            else:
                options = [
                    {
                        "p_st": args.p_st,
                        "background": args.background == "nonzero",
                        "open_output": args.open_output,
                    }
                ]
            tasks.extend(
                (
                    distance,
                    basis,
                    level,
                    variant,
                    str(args.hex_repo.resolve()) if args.hex_repo else None,
                )
                for variant in options
            )
    started = time.perf_counter()
    if args.workers == 1:
        reports = list(map(run_task, tasks))
    else:
        with ProcessPoolExecutor(
            max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            reports = list(pool.map(run_task, tasks))
    result = {
        "schema": 1,
        "workers": args.workers,
        "platform": platform.platform(),
        "python": sys.version,
        "environment": environment(),
        "converter_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "hex_source_commit": HEX_COMMIT,
        "wall_seconds": time.perf_counter() - started,
        "reports": reports,
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if all(report["status"] == "PASS" for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
