"""Eight-worker ordinary circuit-level fault census and bounded MWPM study."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import multiprocessing
import os
import subprocess
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from itertools import islice
from pathlib import Path

import numpy as np
import pymatching
import stim

from logical_to_stim_converter import DEMOptions
from validation.code_capacity import fit_points, wilson
from validation.ordinary_faults import (
    Case,
    atoms_from_locations,
    audit_dem_marginal,
    audit_first_order,
    audit_pair_subset,
    audit_schedule,
    audit_signed_reference,
    build_case,
    circuit_identity,
    dem_events,
    fourier_table,
    project_signature,
    scan_noisy,
    simulate_atoms,
)

SCHEMA_VERSION = 1
IMPLEMENTATION_VERSION = "phase2-1"
RATIOS = (1.0, 2.0, 3.0, 4.0, 5.0)


class UnsupportedMatchingModel(ValueError):
    """The declared graphlike/correlated matching approximation cannot encode the DEM."""


def matching_for_dem(model: stim.DetectorErrorModel) -> pymatching.Matching:
    for probability, _, _, components in dem_events(model):
        if not 0 <= probability <= 1:
            raise UnsupportedMatchingModel("invalid DEM probability")
        if any(detectors.bit_count() > 2 for detectors, _ in components):
            raise UnsupportedMatchingModel("undecomposed hyperedge in matching component")
    matching = pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
    matching.ensure_num_fault_ids(model.num_observables)
    return matching


def _census_task(task: tuple[Case, int, int, int, str]) -> tuple[int, int, tuple]:
    case, start, stop, batch_size, fingerprint = task
    compiled, _ = build_case(case)
    if circuit_identity(compiled)["source_fingerprint"] != fingerprint:
        raise AssertionError("worker reconstructed a different compiler source")
    atoms = atoms_from_locations(scan_noisy(compiled))
    subset = atoms[start:stop]
    if len(subset) != stop - start:
        raise AssertionError("census partition exceeds atom count")
    signatures = simulate_atoms(compiled, subset, batch_size=batch_size)
    return start, stop, tuple((atom_id, *signatures[atom_id]) for atom_id in range(start, stop))


def parallel_census(
    case: Case,
    *,
    workers: int = 8,
    batch_size: int = 512,
    executor: ProcessPoolExecutor | None = None,
):
    if workers < 1 or batch_size < 1:
        raise ValueError("invalid census workers/batch size")
    compiled, model = build_case(case)
    locations = scan_noisy(compiled)
    schedule = audit_schedule(compiled, model, locations)
    atoms = atoms_from_locations(locations)
    fingerprint = circuit_identity(compiled)["source_fingerprint"]
    edges = [round(i * len(atoms) / workers) for i in range(workers + 1)]
    tasks = [
        (case, edges[i], edges[i + 1], batch_size, fingerprint)
        for i in range(workers)
        if edges[i] < edges[i + 1]
    ]
    own = executor is None and workers > 1
    if own:
        executor = ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
    try:
        results = (
            map(_census_task, tasks) if executor is None else executor.map(_census_task, tasks)
        )
        signatures = {}
        visited = []
        for start, stop, rows in results:
            if tuple(row[0] for row in rows) != tuple(range(start, stop)):
                raise AssertionError("census task skipped or duplicated atom IDs")
            visited.extend(range(start, stop))
            signatures.update({row[0]: row[1:] for row in rows})
        if visited != list(range(len(atoms))) or len(signatures) != len(atoms):
            raise AssertionError("census partition skipped or duplicated atoms")
    finally:
        if own:
            executor.shutdown(wait=True, cancel_futures=True)
    return compiled, locations, atoms, signatures, schedule


def _ids(mask: int) -> str:
    return ";".join(str(i) for i in range(mask.bit_length()) if mask & (1 << i))


def save_atom_table(path: Path, compiled, locations, atoms, signatures, revision: str) -> dict:
    """Deterministic gzip CSV with every physical alternative and absolute signature."""
    fingerprint = circuit_identity(compiled)["source_fingerprint"]
    fields = (
        "source_revision",
        "source_fingerprint",
        "atom_id",
        "location_id",
        "instruction_index",
        "instruction_tag",
        "source_module",
        "ideal_cut",
        "time_layer",
        "operation",
        "kind",
        "channel",
        "target_position",
        "physical_targets",
        "physical_sites",
        "epochs",
        "record_index",
        "alternative",
        "alternative_probability",
        "identity_probability",
        "exclusive_group",
        "insertion_convention",
        "global_detectors",
        "global_observables",
    )
    with path.open("wb") as binary:
        with gzip.GzipFile(fileobj=binary, mode="wb", filename="", mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                for atom in atoms:
                    location = locations[atom.location_id]
                    detectors, observables = signatures[atom.atom_id]
                    convention = (
                        "reported bit at measurement"
                        if location.kind == "measurement"
                        else "after reset"
                        if location.kind == "reset"
                        else "after gate"
                        if location.kind.startswith("after_")
                        else "at end of active TICK layer"
                    )
                    writer.writerow(
                        {
                            "source_revision": revision,
                            "source_fingerprint": fingerprint,
                            "atom_id": atom.atom_id,
                            "location_id": location.location_id,
                            "instruction_index": location.instruction_index,
                            "instruction_tag": location.instruction_tag,
                            "source_module": location.source_module,
                            "ideal_cut": location.ideal_cut,
                            "time_layer": location.layer,
                            "operation": location.operation,
                            "kind": location.kind,
                            "channel": location.channel,
                            "target_position": location.target_position,
                            "physical_targets": ";".join(map(str, location.targets)),
                            "physical_sites": ";".join(f"{b}:{s}" for b, s in location.sites),
                            "epochs": ";".join(
                                "" if epoch is None else str(epoch) for epoch in location.epochs
                            ),
                            "record_index": "" if atom.record_index is None else atom.record_index,
                            "alternative": atom.alternative,
                            "alternative_probability": format(atom.probability, ".17g"),
                            "identity_probability": format(location.identity_probability, ".17g"),
                            "exclusive_group": location.location_id,
                            "insertion_convention": convention,
                            "global_detectors": _ids(detectors),
                            "global_observables": _ids(observables),
                        }
                    )
    return {
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(atoms),
        "bytes": path.stat().st_size,
    }


def categorical_distribution(
    locations,
    atoms,
    signatures,
    detector_ids,
    observable_ids,
    *,
    shots: int,
    seed: int,
    batch_size: int = 8192,
) -> dict:
    """Sample the independent per-location categorical model, separate from Stim."""
    if shots < 1 or batch_size < 1:
        raise ValueError("invalid categorical sample size")
    by_location = defaultdict(list)
    for atom in atoms:
        projected = project_signature(signatures[atom.atom_id][:2], detector_ids, observable_ids)
        by_location[atom.location_id].append((atom.probability, projected))
    rng = np.random.default_rng(seed)
    width = 1 << (len(detector_ids) + len(observable_ids))
    counts = np.zeros(width, dtype=np.int64)
    for start in range(0, shots, batch_size):
        size = min(batch_size, shots - start)
        outcomes = np.zeros(size, dtype=np.uint16)
        for location in locations:
            alts = by_location[location.location_id]
            # Zero is identity, subsequent entries are mutually exclusive atoms.
            threshold = np.cumsum([location.identity_probability] + [p for p, _ in alts])[:-1]
            choice = np.searchsorted(threshold, rng.random(size), side="right")
            for index, (_, signature) in enumerate(alts, start=1):
                outcomes[choice == index] ^= signature
        counts += np.bincount(outcomes, minlength=width)
    fourier = fourier_table(locations, atoms, signatures, detector_ids, observable_ids)
    exact = np.array(
        [
            sum(
                moment * (-1 if (state & probe).bit_count() & 1 else 1)
                for probe, moment in enumerate(fourier)
            )
            / width
            for state in range(width)
        ]
    )
    expected = exact * shots
    assessed = expected >= 5
    z = np.abs(counts[assessed] - expected[assessed]) / np.sqrt(
        np.maximum(expected[assessed] * (1 - exact[assessed]), 1e-15)
    )
    return {
        "shots": shots,
        "seed": seed,
        "global_detector_ids": detector_ids,
        "global_observable_ids": observable_ids,
        "counts": counts.tolist(),
        "exact_probabilities": exact.tolist(),
        "max_binomial_z_when_expected_ge_5": float(np.max(z, initial=0)),
        "total_variation": float(np.abs(counts / shots - exact).sum() / 2),
    }


def _ordered_results(executor, tasks, workers):
    source = iter(tasks)
    pending = deque(executor.submit(_memory_task, task) for task in islice(source, workers))
    try:
        while pending:
            result = pending.popleft().result()
            yield result
            try:
                pending.append(executor.submit(_memory_task, next(source)))
            except StopIteration:
                pass
    finally:
        for future in pending:
            future.cancel()


def _memory_task(task: tuple[Case, int, int, int]) -> tuple[int, int, float]:
    case, shots, seed, task_id = task
    start = time.perf_counter()
    compiled, _ = build_case(case)
    view = compiled.make_decoder_view(dem_options=DEMOptions(decompose_errors=True))
    matching = matching_for_dem(view.detector_error_model)
    stream = np.random.SeedSequence(
        [
            seed,
            case.distance,
            ord(case.basis),
            case.rounds,
            task_id,
            int(round(case.probabilities[0] * 1e9)),
        ]
    )
    stim_seed = int(np.random.default_rng(stream).integers(1, 2**63 - 1))
    detectors, truth = compiled.circuit.compile_detector_sampler(seed=stim_seed).sample(
        shots, separate_observables=True
    )
    predicted = matching.decode_batch(detectors, enable_correlations=True)
    if predicted.shape != truth.shape:
        raise AssertionError("decoder output shape mismatch")
    failures = int(np.count_nonzero(np.any(predicted.astype(bool) ^ truth, axis=1)))
    return failures, shots, time.perf_counter() - start


def run_memory_point(
    case: Case,
    *,
    workers: int,
    batch_size: int,
    seed: int,
    max_shots: int,
    target_failures: int,
    max_seconds: float,
    executor: ProcessPoolExecutor | None = None,
) -> dict:
    if (
        workers < 1
        or batch_size < 1
        or seed < 1
        or max_shots < 1
        or target_failures < 0
        or not math.isfinite(max_seconds)
        or max_seconds <= 0
    ):
        raise ValueError("invalid Monte Carlo settings")
    own = executor is None and workers > 1
    if own:
        executor = ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        )
    tasks = (
        (case, min(batch_size, max_shots - i * batch_size), seed, i)
        for i in range(math.ceil(max_shots / batch_size))
    )
    start = time.perf_counter()
    failures = shots = 0
    worker_seconds = 0.0
    try:
        results = (
            map(_memory_task, tasks)
            if executor is None
            else _ordered_results(executor, tasks, workers)
        )
        try:
            for count, size, duration in results:
                failures += count
                shots += size
                worker_seconds += duration
                if (
                    target_failures and failures >= target_failures
                ) or time.perf_counter() - start >= max_seconds:
                    break
        finally:
            if executor is not None:
                results.close()
    finally:
        if own:
            executor.shutdown(wait=True, cancel_futures=True)
    elapsed = time.perf_counter() - start
    return {
        "case": case.name,
        "shots": shots,
        "failures": failures,
        "rate": failures / shots,
        "wilson_95": wilson(failures, shots),
        "stop_reason": "target_failures"
        if target_failures and failures >= target_failures
        else "max_shots"
        if shots == max_shots
        else "max_seconds",
        "wall_seconds": elapsed,
        "shots_per_second": shots / elapsed,
        "sum_worker_seconds": worker_seconds,
    }


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=9201)
    parser.add_argument("--max-shots", type=int, default=131072)
    parser.add_argument("--target-failures", type=int, default=100)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--p-values", type=float, nargs="+", default=[0.002, 0.004, 0.008, 0.012])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("validation/output/phase2"))
    args = parser.parse_args(argv)
    if args.quick:
        args.max_shots = min(args.max_shots, 1024)
        args.target_failures = 0
        args.p_values = [0.006]
    if (
        not 1 <= args.workers <= 8
        or args.batch_size < 1
        or args.seed < 1
        or args.max_shots < 1
        or args.target_failures < 0
        or not math.isfinite(args.max_seconds)
        or args.max_seconds <= 0
        or not args.p_values
        or any(not math.isfinite(p) or not 0 < p <= 0.015 for p in args.p_values)
    ):
        parser.error("invalid worker, probability, shot, seed or time setting")
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    revision = git_sha()
    nonuniform = (0.001, 0.002, 0.003, 0.004, 0.005)
    cases = [
        Case(3, "Z", 1, nonuniform),
        Case(3, "X", 3, (0.001,) * 5),
        Case(5, "Z", 1, (0.001,) * 5),
        Case(5, "X", 5, (0.001,) * 5),
        Case(3, "X", 1, nonuniform, "h"),
        Case(3, "Z", 1, nonuniform, "signed"),
        Case(3, "Z", 3, nonuniform, "spectator"),
    ]
    if args.quick:
        cases = cases[:1]
    census = []
    with ProcessPoolExecutor(
        max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
    ) as executor:
        for case in cases:
            began = time.perf_counter()
            compiled, locations, atoms, signatures, schedule = parallel_census(
                case, workers=args.workers, batch_size=args.batch_size, executor=executor
            )
            identity = circuit_identity(compiled)
            marginal = audit_dem_marginal(compiled, locations, atoms, signatures)
            first_order = audit_first_order(case, atoms, signatures)
            table = save_atom_table(
                args.output_dir / f"atoms_{case.name}.csv.gz",
                compiled,
                locations,
                atoms,
                signatures,
                revision,
            )
            aliases = Counter(signatures[atom.atom_id][:2] for atom in atoms)
            item = {
                "case": asdict(case),
                "name": case.name,
                "identity": identity,
                "schedule": schedule,
                "atom_count": len(atoms),
                "signed_reference": audit_signed_reference(compiled),
                "distinct_signatures": len(aliases),
                "zero_signature_atoms": aliases[(0, 0)],
                "aliased_signature_groups": sum(v > 1 for v in aliases.values()),
                "marginal": marginal,
                "first_order": first_order,
                "table": table,
                "wall_seconds": time.perf_counter() - began,
            }
            item["atoms_per_second"] = len(atoms) / item["wall_seconds"]
            if case.variant == "ordinary" and case.distance == 3 and case.rounds == 1:
                item["pair_subset"] = audit_pair_subset(compiled, atoms, signatures, seed=args.seed)
                item["categorical_sample"] = categorical_distribution(
                    locations,
                    atoms,
                    signatures,
                    (0, 1, 2),
                    (0,),
                    shots=20000 if args.quick else 100000,
                    seed=args.seed,
                )
            if case.variant == "ordinary" and case.rounds == case.distance:
                item["shortest_graphlike_faults"] = len(compiled.circuit.shortest_graphlike_error())
                reference = stim.Circuit.generated(
                    f"surface_code:rotated_memory_{case.basis.lower()}",
                    distance=case.distance,
                    rounds=case.rounds,
                    after_clifford_depolarization=0.001,
                    before_measure_flip_probability=0.001,
                )
                item["stim_generated_reference"] = {
                    "shortest_graphlike_faults": len(reference.shortest_graphlike_error()),
                    "num_ticks": reference.num_ticks,
                    "same_physical_schedule": reference.num_ticks == compiled.circuit.num_ticks
                    and reference.num_qubits == compiled.circuit.num_qubits,
                }
            census.append(item)
            print(
                f"census {case.name}: {len(locations)} locations {len(atoms)} atoms "
                f"wall={item['wall_seconds']:.2f}s "
                f"throughput={item['atoms_per_second']:.0f} atoms/s",
                flush=True,
            )
        memory_points = []
        study_cases = [Case(3, "Z", 3, (p,) * 5) for p in args.p_values]
        if not args.quick:
            study_cases += [Case(5, "Z", 5, (p,) * 5) for p in args.p_values]
            study_cases += [Case(3, "X", 3, (0.008,) * 5), Case(5, "X", 5, (0.012,) * 5)]
        for case in study_cases:
            p = run_memory_point(
                case,
                workers=args.workers,
                batch_size=args.batch_size,
                seed=args.seed,
                max_shots=args.max_shots,
                target_failures=args.target_failures,
                max_seconds=args.max_seconds,
                executor=executor,
            )
            p.update(
                distance=case.distance,
                basis=case.basis,
                rounds=case.rounds,
                probability=case.probabilities[0],
                per_shot_normalization=True,
            )
            memory_points.append(p)
            print(
                f"sample {case.name} p={case.probabilities[0]:g}: "
                f"{p['failures']}/{p['shots']} wall={p['wall_seconds']:.2f}s "
                f"throughput={p['shots_per_second']:.0f} shots/s",
                flush=True,
            )
    fits = {}
    for distance in (3, 5):
        selected = [
            dict(q=p["probability"], shots=p["shots"], failures=p["failures"])
            for p in memory_points
            if p["basis"] == "Z" and p["distance"] == distance
        ]
        if selected:
            fits[f"d{distance}_Z"] = {
                "free_power": fit_points(selected),
                "free_curvature": fit_points(selected, curvature=True),
            }
    report = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "compiler_source_sha": revision,
        "versions": {
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
        },
        "settings": {
            "workers": args.workers,
            "cpu_count": os.cpu_count(),
            "batch_size": args.batch_size,
            "seed": args.seed,
            "max_shots": args.max_shots,
            "target_failures": args.target_failures,
            "max_seconds": args.max_seconds,
        },
        "census": census,
        "memory_points": memory_points,
        "fits": fits,
        "wall_seconds": time.perf_counter() - started,
        "assumptions": [
            "ordinary rotated-surface ideal physical schedule",
            "independent per-location categorical reset/gate/measurement/idle channels",
            "two-pass correlated PyMatching only for decomposed graphlike components",
            "failure is any decoded observable XOR physical truth per shot",
            "no circuit-level analytic exponent/coefficient asserted",
        ],
    }
    with (args.output_dir / "report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)
    with (args.output_dir / "memory_points.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[k for k in memory_points[0] if k != "wilson_95"]
            + ["wilson_low", "wilson_high"],
            lineterminator="\n",
        )
        writer.writeheader()
        for point in memory_points:
            row = {k: v for k, v in point.items() if k != "wilson_95"}
            row.update(wilson_low=point["wilson_95"][0], wilson_high=point["wilson_95"][1])
            writer.writerow(row)
    print(
        f"report={args.output_dir / 'report.json'} wall={report['wall_seconds']:.2f}s "
        f"workers={args.workers} cpus={os.cpu_count()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
