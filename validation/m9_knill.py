"""Eight-worker, research-only M9 Knill fault enumeration and memory fits."""

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
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pymatching
import stim

from examples.knill_memory_offline_decoding import analyze_knill
from validation.code_capacity import fit_points, wilson
from validation.m9_knill_faults import (
    Case,
    assignments,
    audit_boundary_ownership,
    audit_conditional_singles,
    audit_direct_physical_samples,
    audit_epoch_clearing,
    audit_pair_action,
    make_experiment,
    pattern_counts,
    scan_locations,
    simulate_assignments,
)

SCHEMA_VERSION = 1
IMPLEMENTATION_VERSION = "phase3-1"


def peak_rss_bytes() -> int | None:
    """Read Linux process high-water RSS when available; keep Windows optional."""
    status = Path("/proc/self/status")
    if not status.exists():
        return None
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) * 1024
    return None


def task_seed(seed: int, *identifiers: int) -> int:
    if seed < 0:
        raise ValueError("seed must be nonnegative")
    return int(np.random.SeedSequence([seed, *identifiers]).generate_state(1, dtype=np.uint64)[0])


def _mask(bits) -> str:
    return np.packbits(np.asarray(bits, dtype=np.uint8), bitorder="little").tobytes().hex()


def _enumeration_task(task):
    case, batch_size, branches, seed, chunks, expected_fingerprint = task
    experiment = make_experiment(case, case.reference_probability)
    compiled = experiment.compiled
    if experiment.frame_plan.source_fingerprint != expected_fingerprint:
        raise AssertionError("worker reconstructed a different M9 source")
    locations = scan_locations(experiment, case.reference_probability)
    singles = tuple(pattern for pattern in assignments(len(locations)) if pattern.weight == 1)
    single_actions = simulate_assignments(experiment, locations, singles, seed=task_seed(seed, 7))
    rows = []
    physical_pairs = 0
    start = time.perf_counter()
    for chunk_id, chunk in chunks:
        patterns = tuple(chunk)
        actions = simulate_assignments(
            experiment, locations, patterns, seed=task_seed(seed, case.cycles, chunk_id, 11)
        )
        raw_delta, detectors, observables, support = actions
        pair_indices = [i for i, pattern in enumerate(patterns) if pattern.weight == 2]
        if pair_indices:
            physical_pairs += audit_pair_action(
                tuple(patterns[i] for i in pair_indices),
                raw_delta[pair_indices],
                detectors[pair_indices],
                observables[pair_indices],
                support[pair_indices],
                single_actions,
            )
        branch_seed = task_seed(seed, case.cycles, chunk_id, 23)
        ideal_sampler = compiled.ideal_circuit.compile_sampler(seed=branch_seed)
        base = ideal_sampler.sample(len(patterns) * branches).reshape(
            len(patterns), branches, compiled.circuit.num_measurements
        )
        raw = (base ^ raw_delta[:, None, :]).reshape(-1, compiled.circuit.num_measurements)
        before = raw.copy()
        result = analyze_knill(experiment, raw)
        if not np.array_equal(raw, before) or result.raw_measurements.flags.writeable:
            raise AssertionError("decoder modified the physical raw record")
        if result.failures.shape != (len(raw), 1):
            raise AssertionError("unexpected final logical failure shape")
        if not np.array_equal(
            result.physical_observable_flips.reshape(len(patterns), branches, -1),
            np.broadcast_to(observables[:, None, :], (len(patterns), branches, 1)),
        ):
            raise AssertionError("physical observable truth differs across ideal branches")
        if not np.array_equal(result.failures, result.logical_values):
            raise AssertionError("|0> failure convention disagrees with corrected final readout")
        failures = result.failures.reshape(len(patterns), branches).sum(axis=1)
        for i, pattern in enumerate(patterns):
            padded = tuple(pattern.atoms) + ((-1, ""),) * (2 - pattern.weight)
            left, right = padded[:2]
            rows.append(
                (
                    pattern.rank,
                    pattern.weight,
                    left[0],
                    left[1],
                    right[0],
                    right[1],
                    int(failures[i]),
                    branches,
                    _mask(raw_delta[i]),
                    _mask(detectors[i]),
                    _mask(observables[i]),
                    ";".join(
                        _mask(support[i, cycle, axis])
                        for cycle in range(case.cycles)
                        for axis in range(2)
                    ),
                )
            )
    return rows, physical_pairs, time.perf_counter() - start, peak_rss_bytes()


def parallel_enumeration(
    case: Case,
    *,
    workers: int,
    batch_size: int,
    branches: int,
    seed: int,
    max_patterns: int | None = None,
):
    if not 1 <= workers <= 8 or batch_size < 1 or branches < 1 or seed < 0:
        raise ValueError("invalid enumeration settings")
    experiment = make_experiment(case, case.reference_probability)
    locations = scan_locations(experiment, case.reference_probability)
    zero = make_experiment(case, 0)
    if zero.compiled.circuit != zero.compiled.ideal_circuit:
        raise AssertionError("enabled p=0 did not retain the ideal M9-only circuit")
    scan_locations(zero, 0)
    ideal_raw = zero.compiled.circuit.compile_sampler(seed=task_seed(seed, case.cycles, 1)).sample(
        512
    )
    baseline = analyze_knill(zero, ideal_raw)
    if (
        baseline.errors
        or baseline.physical_events.any()
        or baseline.physical_observable_flips.any()
    ):
        raise AssertionError("ideal random-gauge or Bell branch failed |0> memory")
    frozen_baseline = analyze_knill(experiment, ideal_raw)
    if frozen_baseline.errors or frozen_baseline.physical_events.any():
        raise AssertionError("frozen decoder fails an ideal random branch")
    if any(
        (result.net_sector is not None and result.net_sector.any())
        or (result.net_sector is None and result.correction.bits.any())
        for _, _, result, _ in frozen_baseline.diagnostics
    ):
        raise AssertionError("ideal stage equations leave a sector or readout correction")
    single_patterns = tuple(
        pattern for pattern in assignments(len(locations)) if pattern.weight == 1
    )
    single_actions = simulate_assignments(experiment, locations, single_patterns)
    conditional = audit_conditional_singles(
        experiment, locations, single_patterns, single_actions[0], single_actions[3]
    )
    ownership = audit_boundary_ownership(experiment, locations)
    epoch = audit_epoch_clearing(experiment, locations, single_patterns)
    all_patterns = tuple(assignments(len(locations)))
    total = sum(pattern_counts(len(locations)))
    if len(all_patterns) != total or tuple(p.rank for p in all_patterns) != tuple(range(total)):
        raise AssertionError("ranked M9 assignments are not complete or unique")
    limit = total if max_patterns is None else min(total, max_patterns)
    if limit < 1:
        raise ValueError("max_patterns must be positive")
    selected = all_patterns[:limit]
    chunks = tuple(
        (i // batch_size, selected[i : i + batch_size]) for i in range(0, limit, batch_size)
    )
    task_groups = tuple(tuple(chunks[worker::workers]) for worker in range(workers))
    fingerprint = experiment.frame_plan.source_fingerprint
    task_args = tuple(
        (case, batch_size, branches, seed, group, fingerprint) for group in task_groups if group
    )
    start = time.perf_counter()
    if len(task_args) == 1:
        results = [_enumeration_task(task_args[0])]
    else:
        with ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            results = list(pool.map(_enumeration_task, task_args))
    rows = sorted((row for batch, _, _, _ in results for row in batch), key=lambda row: row[0])
    if [row[0] for row in rows] != list(range(limit)):
        raise AssertionError("parallel enumeration skipped or duplicated a pattern rank")
    if sum(pairs for _, pairs, _, _ in results) != sum(row[1] == 2 for row in rows):
        raise AssertionError("not every pair received a direct physical composition check")
    direct_patterns = [all_patterns[i] for i in (1, 2, 3, total // 3, total // 2, total - 1)]
    direct_actions = simulate_assignments(experiment, locations, tuple(direct_patterns))
    direct = audit_direct_physical_samples(experiment, locations, direct_patterns, direct_actions)
    diagnostics = {
        "case": asdict(case),
        "source_fingerprint": fingerprint,
        "ideal_sha256": hashlib.sha256(str(experiment.compiled.ideal_circuit).encode()).hexdigest(),
        "noisy_sha256": hashlib.sha256(str(experiment.compiled.circuit).encode()).hexdigest(),
        "num_qubits": experiment.compiled.circuit.num_qubits,
        "num_measurements": experiment.compiled.circuit.num_measurements,
        "num_detectors": experiment.compiled.circuit.num_detectors,
        "num_observables": experiment.compiled.circuit.num_observables,
        "num_ticks": experiment.compiled.circuit.num_ticks,
        "num_uses": len(experiment.compiled.block_uses),
        "num_relocations": len(experiment.compiled.relocation_history),
        "num_boundaries": len(experiment.compiled.resource_preparation_boundaries),
        "num_stages": len(experiment.requests.order),
        "stage_order": experiment.requests.order,
        "locations": [asdict(location) for location in locations],
        "resource_boundaries": [
            {
                "block_use_id": asdict(boundary.block_use_id),
                "preparation_module_id": boundary.preparation_module_id,
                "resource_entangling_module_id": boundary.resource_entangling_module_id,
                "first_layer": boundary.first_layer,
                "final_se_layer": boundary.final_se_layer,
                "ideal_boundary_instruction": boundary.ideal_boundary_instruction,
                "channel_instruction": boundary.channel_instruction,
                "channel_tag": boundary.channel_tag,
            }
            for boundary in experiment.compiled.resource_preparation_boundaries
        ],
        "conditional_models": [
            {
                "composite_id": model.composite_id,
                "start_instruction": model.start_instruction,
                "end_instruction": model.end_instruction,
                "fault_atoms": len(model.faults),
                "exclusive_groups": len({fault.exclusive_group for fault in model.faults}),
            }
            for model in experiment.conditional_models
        ],
        "conditional": conditional,
        "ownership": ownership,
        "epoch": epoch,
        "direct": direct,
        "ideal_branch_baseline": {
            "shots": len(ideal_raw),
            "failures": baseline.errors,
            "frozen_decoder_failures": frozen_baseline.errors,
            "stage_net_sectors_and_readout_corrections_zero": True,
            "random_raw_columns": int(np.count_nonzero(np.any(ideal_raw != ideal_raw[0], axis=0))),
        },
        "location_count": len(locations),
        "pattern_counts": pattern_counts(len(locations)),
        "evaluated_patterns": len(rows),
        "remaining_patterns": total - len(rows),
        "physical_pair_checks": sum(pairs for _, pairs, _, _ in results),
        "branches_per_pattern": branches,
        "wall_seconds": time.perf_counter() - start,
        "sum_worker_seconds": sum(seconds for _, _, seconds, _ in results),
        "max_worker_peak_rss_bytes": max(
            (rss for _, _, _, rss in results if rss is not None), default=None
        ),
    }
    return experiment, locations, rows, diagnostics


def k_estimates(rows, location_count: int, *, alpha: float = 0.05) -> dict:
    """Estimate branch-averaged K and give conservative concentration intervals."""
    if not 0 < alpha < 1:
        raise ValueError("invalid confidence level")
    expected = pattern_counts(location_count)
    by_weight = {w: [row for row in rows if row[1] == w] for w in range(3)}
    result = {}
    for weight in range(3):
        selected = by_weight[weight]
        if not selected:
            result[f"K{weight}"] = {"status": "not_evaluated"}
            continue
        branches = selected[0][7]
        if any(row[7] != branches for row in selected):
            raise AssertionError("branch sample count changed within one weight")
        failures = sum(row[6] for row in selected)
        estimate = failures / branches
        complete = len(selected) == expected[weight]
        # The independent ideal-branch draws across assignments permit a
        # Hoeffding bound for their sum despite unequal conditional probabilities.
        radius = math.sqrt(len(selected) * math.log(2 * 3 / alpha) / (2 * branches))
        lower = max(0.0, estimate - radius)
        upper = min(len(selected), estimate + radius)
        if failures == 0:
            upper = min(upper, -math.log(alpha / 3) / branches)
        if weight == 0 and complete:
            if failures:
                raise AssertionError("ideal K0 baseline has a sampled failure")
            lower = upper = 0.0
        result[f"K{weight}"] = {
            "status": "complete_pattern_set_estimated_branches"
            if complete
            else "partial_pattern_set",
            "assignment_count": len(selected),
            "ideal_branch_draws_per_assignment": branches,
            "observed_failed_branches": failures,
            "estimate": estimate,
            "confidence_interval": [lower, upper],
            "mixed_branch_assignments": sum(0 < row[6] < row[7] for row in selected),
            "interval_method": "independent-branch Hoeffding; zero-success exponential bound",
            "ideal_baseline_basis": (
                "verified ideal flow, zero event stage equations and exact Bell byproducts"
                if weight == 0
                else None
            ),
        }
    if all(
        result[f"K{w}"].get("status") == "complete_pattern_set_estimated_branches" for w in range(3)
    ):
        k1 = result["K1"]
        k2 = result["K2"]
        result["a1"] = {
            "estimate": k1["estimate"] / 3,
            "confidence_interval": [x / 3 for x in k1["confidence_interval"]],
        }
        result["a2"] = {
            "estimate": k2["estimate"] / 9 - (location_count - 1) * k1["estimate"] / 3,
            "confidence_interval": [
                k2["confidence_interval"][0] / 9
                - (location_count - 1) * k1["confidence_interval"][1] / 3,
                k2["confidence_interval"][1] / 9
                - (location_count - 1) * k1["confidence_interval"][0] / 3,
            ],
            "formula": "K2/9-(N-1)*K1/3",
        }
    return result


def binomial_tail(location_count: int, p: float) -> float:
    if isinstance(p, bool) or not 0 <= p <= 1:
        raise ValueError("p must be in [0,1]")
    return math.fsum(
        math.comb(location_count, weight) * p**weight * (1 - p) ** (location_count - weight)
        for weight in range(3, location_count + 1)
    )


def resolved_failure_counts(rows, locations) -> dict:
    """Retain location/axis and cycle-pair failure counts without hiding aliases."""
    singles = []
    axis_pairs = Counter()
    boundary_pairs = Counter()
    cycle_pairs = Counter()
    mixed = []
    for row in rows:
        rank, weight, l0, a0, l1, a1, failed, samples = row[:8]
        if 0 < failed < samples:
            mixed.append(rank)
        if weight == 1:
            loc = locations[l0]
            singles.append(
                {
                    "rank": rank,
                    "location_id": l0,
                    "axis": a0,
                    "block_use": f"{loc.block_id}:{loc.epoch}",
                    "failed_branches": failed,
                    "branch_samples": samples,
                }
            )
        elif weight == 2:
            axis_pairs[a0 + a1] += failed
            boundary_pairs[f"{locations[l0].boundary_id},{locations[l1].boundary_id}"] += failed
            cycle_pairs[f"{locations[l0].boundary_id // 2},{locations[l1].boundary_id // 2}"] += (
                failed
            )
    return {
        "single_location_axis_rows": singles,
        "pair_failed_branch_counts_by_axis_order": dict(sorted(axis_pairs.items())),
        "pair_failed_branch_counts_by_boundary_pair": dict(sorted(boundary_pairs.items())),
        "pair_failed_branch_counts_by_cycle_pair": dict(sorted(cycle_pairs.items())),
        "mixed_branch_ranks": mixed,
        "failure_count_unit": "failed ideal-branch draws; divide by branches per assignment for K",
    }


def low_weight_prediction(estimates, location_count: int, p: float) -> dict:
    if any(
        estimates[f"K{w}"].get("status") != "complete_pattern_set_estimated_branches"
        for w in range(3)
    ):
        return {"status": "incomplete_enumeration"}
    coefficients = (
        (1 - p) ** location_count,
        (p / 3) * (1 - p) ** (location_count - 1),
        (p / 3) ** 2 * (1 - p) ** (location_count - 2),
    )
    partial = sum(estimates[f"K{w}"]["estimate"] * coefficients[w] for w in range(3))
    low = sum(estimates[f"K{w}"]["confidence_interval"][0] * coefficients[w] for w in range(3))
    high = sum(estimates[f"K{w}"]["confidence_interval"][1] * coefficients[w] for w in range(3))
    tail = binomial_tail(location_count, p)
    return {
        "status": "estimated_partial_plus_rigorous_tail",
        "partial_estimate": partial,
        "partial_confidence_interval": [low, high],
        "omitted_weight_tail_upper": tail,
        "full_probability_interval": [low, min(1.0, high + tail)],
    }


def _assert_frozen_compatible(reference, actual):
    if reference.requests.order != actual.requests.order:
        raise AssertionError("M9 probability changed causal stage order")
    old = {r.module_id: r for r in reference.requests.boundaries}
    new = {r.module_id: r for r in actual.requests.boundaries}
    for key in old:
        if old[key].view.detector_map.global_ids != new[key].view.detector_map.global_ids:
            raise AssertionError("frozen temporal MWPM saw a different detector layout")
    old_readouts = {r.readout.module_id: r for r in reference.requests.readouts}
    new_readouts = {r.readout.module_id: r for r in actual.requests.readouts}
    for key in old_readouts:
        if old_readouts[key].record_ids != new_readouts[key].record_ids:
            raise AssertionError("frozen capacity MWPM saw a different record layout")


def _monte_carlo_task(task):
    case, p, batch_size, seed, max_shots, target_failures, max_seconds = task
    start = time.perf_counter()
    actual = make_experiment(case, p)
    reference = (
        actual
        if p == case.reference_probability
        else make_experiment(case, case.reference_probability)
    )
    _assert_frozen_compatible(reference, actual)
    sampler = actual.compiled.circuit.compile_sampler(
        seed=task_seed(seed, case.cycles, int(p * 1e9), 41)
    )
    shots = failures = batches = 0
    sampling_seconds = replay_seconds = 0.0
    while shots < max_shots:
        count = min(batch_size, max_shots - shots)
        began = time.perf_counter()
        raw = sampler.sample(count)
        sampling_seconds += time.perf_counter() - began
        before = raw.copy()
        began = time.perf_counter()
        result = analyze_knill(
            actual,
            raw,
            boundary_decoders=reference.boundary_decoders,
            readout_decoders=reference.readout_decoders,
        )
        if batches == 0 and reference is not actual:
            compared = analyze_knill(reference, raw[: min(len(raw), 64)])
            current = analyze_knill(
                actual,
                raw[: min(len(raw), 64)],
                boundary_decoders=reference.boundary_decoders,
                readout_decoders=reference.readout_decoders,
            )
            if not np.array_equal(compared.failures, current.failures) or any(
                not np.array_equal(left[2].correction.bits, right[2].correction.bits)
                for left, right in zip(compared.diagnostics, current.diagnostics, strict=True)
            ):
                raise AssertionError("frozen MWPM decision changed with the sampling prior")
        replay_seconds += time.perf_counter() - began
        if not np.array_equal(raw, before):
            raise AssertionError("Monte Carlo decoder mutated the sampled physical records")
        failures += result.errors
        shots += count
        batches += 1
        if (
            target_failures and failures >= target_failures
        ) or time.perf_counter() - start >= max_seconds:
            break
    elapsed = time.perf_counter() - start
    return {
        "case": case.name,
        "probability": p,
        "shots": shots,
        "failures": failures,
        "rate": failures / shots,
        "wilson_95": wilson(failures, shots),
        "batches": batches,
        "stop_reason": "target_failures"
        if target_failures and failures >= target_failures
        else "max_shots"
        if shots == max_shots
        else "max_seconds",
        "wall_seconds": elapsed,
        "sampling_seconds": sampling_seconds,
        "replay_seconds": replay_seconds,
        "shots_per_second": shots / elapsed,
        "worker_peak_rss_bytes": peak_rss_bytes(),
        "source_fingerprint": actual.frame_plan.source_fingerprint,
        "frozen_prior": case.reference_probability,
        "frozen_decision_invariance_checked": True,
    }


def parallel_monte_carlo(
    case, p_values, *, workers, batch_size, seed, max_shots, target_failures, max_seconds
):
    if not 1 <= workers <= 8 or not p_values or max_shots < 1 or batch_size < 1:
        raise ValueError("invalid Monte Carlo settings")
    tasks = [(case, p, batch_size, seed, max_shots, target_failures, max_seconds) for p in p_values]
    if workers == 1:
        return [_monte_carlo_task(task) for task in tasks]
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        return list(pool.map(_monte_carlo_task, tasks))


def save_assignment_table(path, rows, locations, revision, fingerprint):
    fields = (
        "source_revision",
        "source_fingerprint",
        "rank",
        "weight",
        "location_0",
        "axis_0",
        "use_0",
        "site_0",
        "location_1",
        "axis_1",
        "use_1",
        "site_1",
        "failed_branches",
        "branch_samples",
        "raw_flip_hex",
        "global_detector_hex",
        "global_observable_hex",
        "survivor_xz_hex_by_cycle",
    )
    with path.open("wb") as binary:
        with gzip.GzipFile(fileobj=binary, mode="wb", filename="", mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                for row in rows:
                    rank, weight, l0, a0, l1, a1, failed, samples, raw, det, obs, survivor = row
                    first = locations[l0] if l0 >= 0 else None
                    second = locations[l1] if l1 >= 0 else None
                    writer.writerow(
                        dict(
                            zip(
                                fields,
                                (
                                    revision,
                                    fingerprint,
                                    rank,
                                    weight,
                                    l0,
                                    a0,
                                    "" if first is None else f"{first.block_id}:{first.epoch}",
                                    "" if first is None else first.site,
                                    l1,
                                    a1,
                                    "" if second is None else f"{second.block_id}:{second.epoch}",
                                    "" if second is None else second.site,
                                    failed,
                                    samples,
                                    raw,
                                    det,
                                    obs,
                                    survivor,
                                ),
                                strict=True,
                            )
                        )
                    )
    return {
        "path": path.name,
        "rows": len(rows),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--shot-batch-size", type=int, default=8192)
    parser.add_argument("--seed", type=int, default=9903)
    parser.add_argument("--branches", type=int, default=128)
    parser.add_argument("--max-patterns", type=int)
    parser.add_argument("--max-shots", type=int, default=131072)
    parser.add_argument("--target-failures", type=int, default=0)
    parser.add_argument("--max-seconds", type=float, default=180.0)
    parser.add_argument(
        "--p-values", type=float, nargs="+", default=[0.002, 0.004, 0.006, 0.008, 0.012]
    )
    parser.add_argument("--reference-probability", type=float, default=0.01)
    parser.add_argument("--cycles", type=int, nargs="+", default=[1, 3])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("validation/output/phase3"))
    args = parser.parse_args(argv)
    if args.quick:
        args.cycles = [1]
        args.branches = min(args.branches, 8)
        args.max_patterns = min(args.max_patterns or 64, 64)
        args.max_shots = min(args.max_shots, 512)
        args.p_values = [0.008]
    if (
        not 1 <= args.workers <= 8
        or args.batch_size < 1
        or args.shot_batch_size < 1
        or args.seed < 0
        or args.branches < 1
        or args.max_shots < 1
        or args.target_failures < 0
        or args.max_patterns is not None
        and args.max_patterns < 1
        or not math.isfinite(args.max_seconds)
        or args.max_seconds <= 0
        or not 0 < args.reference_probability <= 0.75
        or not args.p_values
        or any(not math.isfinite(p) or not 0 < p <= 0.75 for p in args.p_values)
        or not args.cycles
        or any(c not in (1, 3) for c in args.cycles)
    ):
        parser.error("invalid Phase 3 worker, probability, branch, pattern, shot or time setting")
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    started = time.perf_counter()
    reports = []
    for cycles in args.cycles:
        case = Case(cycles, args.reference_probability)
        began = time.perf_counter()
        experiment, locations, rows, census = parallel_enumeration(
            case,
            workers=args.workers,
            batch_size=args.batch_size,
            branches=args.branches,
            seed=args.seed,
            max_patterns=args.max_patterns,
        )
        estimates = k_estimates(rows, len(locations))
        resolved = resolved_failure_counts(rows, locations)
        table = save_assignment_table(
            output / f"assignments_{case.name}.csv.gz",
            rows,
            locations,
            revision,
            experiment.frame_plan.source_fingerprint,
        )
        print(
            f"enumerated {case.name}: {len(rows)}/{sum(pattern_counts(len(locations)))} "
            f"patterns, {census['physical_pair_checks']} physical pairs, "
            f"wall={census['wall_seconds']:.2f}s "
            f"throughput={len(rows) / census['wall_seconds']:.0f} patterns/s",
            flush=True,
        )
        points = parallel_monte_carlo(
            case,
            args.p_values,
            workers=args.workers,
            batch_size=args.shot_batch_size,
            seed=args.seed,
            max_shots=args.max_shots,
            target_failures=args.target_failures,
            max_seconds=args.max_seconds,
        )
        for point in points:
            point["low_weight_prediction"] = low_weight_prediction(
                estimates, len(locations), point["probability"]
            )
            interval = point["low_weight_prediction"].get("full_probability_interval")
            point["prediction_interval_overlaps_wilson"] = (
                None
                if interval is None
                else max(interval[0], point["wilson_95"][0])
                <= min(interval[1], point["wilson_95"][1])
            )
            print(
                f"sample {case.name} p={point['probability']:g}: "
                f"{point['failures']}/{point['shots']} "
                f"wall={point['wall_seconds']:.2f}s "
                f"throughput={point['shots_per_second']:.0f} shots/s",
                flush=True,
            )
        fit_input = [
            dict(q=p["probability"], shots=p["shots"], failures=p["failures"]) for p in points
        ]
        fits = (
            {
                "free_power": fit_points(fit_input),
                "free_curvature": fit_points(fit_input, curvature=True),
            }
            if len(points) >= 4
            else {}
        )
        reports.append(
            {
                "case": asdict(case),
                "census": census,
                "table": table,
                "coefficients": estimates,
                "resolved_failures": resolved,
                "memory_points": points,
                "fits": fits,
                "wall_seconds": time.perf_counter() - began,
                "decoder": {
                    "identity": "frozen M6-D restricted/modular MWPM",
                    "reference_probability": case.reference_probability,
                    "boundary": (
                        "correlated temporal MWPM plus unit-weight CSS sector capacity MWPM"
                    ),
                    "readout": "conditional unit-weight per-patch capacity MWPM",
                    "weights": "temporal DEM at fixed reference prior; capacity unit weights",
                    "tie_break": f"PyMatching {pymatching.__version__} implementation default",
                    "truth_input": False,
                    "model_only_mpp_input": False,
                },
            }
        )
    report = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "compiler_baseline_sha": revision,
        "versions": {
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
        },
        "settings": {
            "workers": args.workers,
            "cpu_count": os.cpu_count(),
            "batch_size": args.batch_size,
            "shot_batch_size": args.shot_batch_size,
            "seed": args.seed,
            "branches": args.branches,
            "max_patterns": args.max_patterns,
            "max_shots": args.max_shots,
            "target_failures": args.target_failures,
            "max_seconds": args.max_seconds,
            "p_values": args.p_values,
        },
        "cases": reports,
        "wall_seconds": time.perf_counter() - started,
        "counterexamples": [],
        "limitations": [
            "All weight-0/1/2 assignments are ranked; branch averages are sampled, not exact.",
            "A zero sampled single-fault failure count does not prove K1=0 across all branches.",
            "No claim of optimal joint Knill inference or an exact asymptotic exponent.",
            "Finite-p partial probability excludes weight>=3; a binomial tail bounds it.",
        ],
    }
    with (output / "report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)
    with (output / "memory_points.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(
            (
                "case",
                "p",
                "shots",
                "failures",
                "rate",
                "wilson_low",
                "wilson_high",
                "partial_estimate",
                "tail_upper",
                "stop_reason",
                "wall_seconds",
            )
        )
        for case in reports:
            for point in case["memory_points"]:
                prediction = point["low_weight_prediction"]
                writer.writerow(
                    (
                        point["case"],
                        point["probability"],
                        point["shots"],
                        point["failures"],
                        point["rate"],
                        *point["wilson_95"],
                        prediction.get("partial_estimate"),
                        prediction.get("omitted_weight_tail_upper"),
                        point["stop_reason"],
                        point["wall_seconds"],
                    )
                )
    print(
        f"report={output / 'report.json'} wall={report['wall_seconds']:.2f}s workers={args.workers}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
