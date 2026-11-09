"""Exact rotated-surface code-capacity census and physical Stim/MWPM experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import multiprocessing
import os
import subprocess
import time
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, islice
from pathlib import Path

import numpy as np
import pymatching
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    SyndromeExtraction,
)

SCHEMA_VERSION = 1
# Hand-transcribed Z plaquettes, in north-then-east D1..D(d*d) data order.
# This table is deliberately independent of CodeSpec and decoder-view projection.
REFERENCE = {
    3: ((1, 2, 4, 5), (3, 6), (4, 7), (5, 6, 8, 9)),
    5: (
        (1, 2, 6, 7),
        (3, 4, 8, 9),
        (5, 10),
        (6, 11),
        (7, 8, 12, 13),
        (9, 10, 14, 15),
        (11, 12, 16, 17),
        (13, 14, 18, 19),
        (15, 20),
        (16, 21),
        (17, 18, 22, 23),
        (19, 20, 24, 25),
    ),
}
IMPLEMENTATION_VERSION = "phase1-2"


def reference_matrix(d: int) -> tuple[np.ndarray, np.ndarray]:
    if d not in REFERENCE:
        raise ValueError("Only hand-checked distances 3 and 5 are supported")
    hz = np.zeros((len(REFERENCE[d]), d * d), dtype=np.uint8)
    for row, support in enumerate(REFERENCE[d]):
        hz[row, np.array(support) - 1] = 1
    lz = np.zeros((1, d * d), dtype=np.uint8)
    lz[0, :d] = 1
    return hz, lz


def _masks(d: int) -> tuple[tuple[int, ...], int]:
    hz, lz = reference_matrix(d)
    return tuple(sum(int(hz[r, j]) << r for r in range(len(hz))) for j in range(d * d)), sum(
        int(lz[0, j]) << j for j in range(d * d)
    )


def syndrome(pattern: int, columns: tuple[int, ...]) -> int:
    value = 0
    while pattern:
        bit = pattern & -pattern
        value ^= columns[bit.bit_length() - 1]
        pattern -= bit
    return value


def patterns(d: int, weights: range | tuple[int, ...]):
    for weight in weights:
        for sites in combinations(range(d * d), weight):
            yield sum(1 << site for site in sites)


def minimum_syndrome_classes(d: int, max_weight: int) -> tuple[dict[int, tuple[int, int]], int]:
    """Independent exhaustive minimum-weight syndrome solver; no PyMatching call."""
    columns, logical = _masks(d)
    table: dict[int, tuple[int, int]] = {}
    ties = 0
    for weight in range(max_weight + 1):
        for error in patterns(d, (weight,)):
            key = syndrome(error, columns)
            parity = (error & logical).bit_count() & 1
            previous = table.get(key)
            if previous is None:
                table[key] = weight, parity
            elif previous[0] == weight:
                ties += 1
                if previous[1] != parity:
                    raise AssertionError("minimum-weight tie changes logical class")
    return table, ties


def enumerate_failures(d: int) -> dict:
    max_weight = d * d if d == 3 else 4
    # For each included error, a correction no heavier than that error exists.
    table, ties = minimum_syndrome_classes(d, max_weight)
    columns, logical = _masks(d)
    counts = Counter()
    visited = Counter()
    for error in patterns(d, range(max_weight + 1)):
        weight = error.bit_count()
        visited[weight] += 1
        correction_class = table[syndrome(error, columns)][1]
        counts[weight] += ((error & logical).bit_count() & 1) ^ correction_class
    assert all(visited[w] == math.comb(d * d, w) for w in visited)
    return {
        "distance": d,
        "counts": [counts[w] for w in range(max_weight + 1)],
        "visited": [visited[w] for w in range(max_weight + 1)],
        "syndrome_classes": len(table),
        "minimum_ties": ties,
        "t": (d + 1) // 2,
        "A": counts[(d + 1) // 2],
        "B": counts[(d + 1) // 2 + 1] - (d * d - (d + 1) // 2) * counts[(d + 1) // 2],
        "power_coefficients": (
            power_coefficients([counts[w] for w in range(max_weight + 1)], d * d)
            if d == 3
            else None
        ),
    }


def power_coefficients(counts: list[int], n: int) -> list[int]:
    """Exact binomial-to-power basis expansion, retaining integer arithmetic."""
    result = [0] * (n + 1)
    for w, count in enumerate(counts):
        for j in range(n - w + 1):
            result[w + j] += count * math.comb(n - w, j) * (-1) ** j
    return result


def probability_bounds(d: int, q: float | Fraction, census: dict) -> tuple[float, float]:
    if not 0 <= q <= 0.5:
        raise ValueError("q must be in [0, 0.5]")
    n = d * d
    lower = sum(count * q**w * (1 - q) ** (n - w) for w, count in enumerate(census["counts"]))
    if d == 3:
        return float(lower), float(lower)
    upper = lower + sum(math.comb(n, w) * q**w * (1 - q) ** (n - w) for w in range(5, n + 1))
    return float(lower), min(1.0, float(upper))


@dataclass(frozen=True)
class PhysicalMemory:
    compiled: object
    prefix: stim.Circuit
    suffix: stim.Circuit
    data_wires: tuple[int, ...]
    syndrome_detector_ids: tuple[int, ...]
    cut: int


def physical_memory(d: int) -> PhysicalMemory:
    code = CodeSpec.rotated_surface(d)
    block = LogicalBlock.placed("physical0", code)
    compiled = CircuitCompiler([block], logical_to_block={"q": "physical0"}).compile(
        [LogicalInit("q", "Z", 1), SyndromeExtraction("q", 1), LogicalMeasure("q", "Z")]
    )
    instructions = list(compiled.ideal_circuit)
    extraction = next(f for f in compiled.fragments if f.operation_type == "SyndromeExtraction")
    cut = next(i for i, op in enumerate(instructions) if op.tag == extraction.module_id)
    if instructions[cut - 1].name != "TICK" or instructions[cut].name not in {"RX", "R"}:
        raise AssertionError("unverified fault boundary")
    if not any(op.name == "M" for op in instructions[:cut]):
        raise AssertionError("preparation is not complete before fault boundary")
    prefix, suffix = stim.Circuit(), stim.Circuit()
    for op in instructions[:cut]:
        prefix.append(op)
    for op in instructions[cut:]:
        suffix.append(op)
    wires = tuple(compiled.physical_qubit_map["physical0", f"D{j + 1}"] for j in range(d * d))
    detectors = tuple(
        info.index
        for info in compiled.detectors
        if info.check_id.startswith("Z") and info.anchor_module_id == extraction.module_id
    )
    if len(detectors) != len(REFERENCE[d]):
        raise AssertionError("syndrome detector projection is incomplete")
    if any("ERROR" in op.name or op.name.startswith("DEPOLARIZE") for op in instructions):
        raise AssertionError("ideal memory contains physical noise")
    if compiled.circuit != compiled.ideal_circuit or len(set(wires)) != d * d:
        raise AssertionError("not an ideal single-block experiment")
    return PhysicalMemory(compiled, prefix, suffix, wires, detectors, cut)


def edited_circuit(memory: PhysicalMemory, q: float, *, depolarize: bool = False) -> stim.Circuit:
    if not math.isfinite(q) or not 0 <= q <= 0.5:
        raise ValueError("q must be finite and in [0, 0.5]")
    circuit = memory.prefix.copy()
    circuit.append("DEPOLARIZE1" if depolarize else "X_ERROR", memory.data_wires, q)
    circuit += memory.suffix
    if (
        circuit.num_measurements != memory.compiled.ideal_circuit.num_measurements
        or circuit.num_detectors != memory.compiled.ideal_circuit.num_detectors
    ):
        raise AssertionError("fault insertion changed record or detector count")
    edited = list(circuit)
    if edited[: memory.cut] + edited[memory.cut + 1 :] != list(memory.compiled.ideal_circuit):
        raise AssertionError("fault insertion changed ideal instructions or annotations")
    circuit.detector_error_model()
    return circuit


def physical_patterns(
    d: int, errors: list[int], batch_size: int = 4096
) -> tuple[np.ndarray, np.ndarray]:
    memory = physical_memory(d)
    all_syndromes, all_logicals = [], []
    for start in range(0, len(errors), batch_size):
        chunk = errors[start : start + batch_size]
        sim = stim.FlipSimulator(
            batch_size=len(chunk), num_qubits=memory.compiled.ideal_circuit.num_qubits
        )
        sim.do(memory.prefix)
        mask = np.zeros((memory.compiled.ideal_circuit.num_qubits, len(chunk)), dtype=bool)
        for shot, error in enumerate(chunk):
            for data, wire in enumerate(memory.data_wires):
                mask[wire, shot] = bool(error & (1 << data))
        sim.broadcast_pauli_errors(pauli="X", mask=mask)
        sim.do(memory.suffix)
        all_syndromes.append(sim.get_detector_flips()[list(memory.syndrome_detector_ids)].T.copy())
        all_logicals.append(sim.get_observable_flips()[0].copy())
        other = np.delete(sim.get_detector_flips(), memory.syndrome_detector_ids, axis=0)
        if other.any():
            raise AssertionError("fault layer changed an unrelated detector")
    return np.concatenate(all_syndromes), np.concatenate(all_logicals)


def verify_physical_patterns(d: int, max_weight: int | None = None) -> dict:
    errors = list(patterns(d, range(d * d + 1 if max_weight is None else max_weight + 1)))
    actual_s, actual_l = physical_patterns(d, errors)
    columns, logical = _masks(d)
    expected_s = np.array(
        [[bool(syndrome(e, columns) & (1 << r)) for r in range(len(REFERENCE[d]))] for e in errors]
    )
    expected_l = np.array([bool((e & logical).bit_count() & 1) for e in errors])
    if not np.array_equal(actual_s, expected_s) or not np.array_equal(actual_l, expected_l):
        raise AssertionError("physical syndrome/logical response disagrees with reference")
    return {"distance": d, "patterns": len(errors), "syndrome_rows": len(REFERENCE[d])}


def wilson(failures: int, shots: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if shots <= 0 or not 0 <= failures <= shots:
        raise ValueError("invalid binomial count")
    p = failures / shots
    scale = 1 + z * z / shots
    center = (p + z * z / (2 * shots)) / scale
    radius = z * math.sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / scale
    return (
        0.0 if failures == 0 else max(0.0, center - radius),
        1.0 if failures == shots else min(1.0, center + radius),
    )


def fit_points(
    points: list[dict], *, fixed_beta: int | None = None, curvature: bool = False
) -> dict:
    good = [p for p in points if p["failures"] > 0 and p["shots"] > p["failures"]]
    k = (1 if fixed_beta is not None else 2) + int(curvature)
    if len(good) <= k:
        return {"status": "insufficient_nonzero_points", "n": len(good)}
    q = np.asarray([p["q"] for p in good], dtype=float)
    rate = np.asarray([p["failures"] / p["shots"] for p in good])
    y = np.log(rate)
    if fixed_beta is not None:
        y -= fixed_beta * np.log(q)
        x = np.column_stack(([np.ones(len(q))] + ([q] if curvature else [])))
    else:
        x = np.column_stack(([np.ones(len(q)), np.log(q)] + ([q] if curvature else [])))
    # Delta-method binomial variance of log(f/N), with observed nonzero f.
    weights = np.asarray([p["failures"] / (1 - p["failures"] / p["shots"]) for p in good])
    gram = x.T @ (weights[:, None] * x)
    covariance = np.linalg.inv(gram)
    params = covariance @ x.T @ (weights * y)
    errors = np.sqrt(np.diag(covariance))
    beta_idx = None if fixed_beta is not None else 1
    c_idx = k - 1 if curvature else None
    return {
        "status": "ok",
        "n": len(good),
        "A": float(np.exp(params[0])),
        "A_95": [
            float(np.exp(params[0] - 1.96 * errors[0])),
            float(np.exp(params[0] + 1.96 * errors[0])),
        ],
        "beta": fixed_beta if beta_idx is None else float(params[beta_idx]),
        "beta_95": None
        if beta_idx is None
        else [
            float(params[beta_idx] - 1.96 * errors[beta_idx]),
            float(params[beta_idx] + 1.96 * errors[beta_idx]),
        ],
        "c": None if c_idx is None else float(params[c_idx]),
        "c_95": None
        if c_idx is None
        else [
            float(params[c_idx] - 1.96 * errors[c_idx]),
            float(params[c_idx] + 1.96 * errors[c_idx]),
        ],
        "weighted_log_residual": float(np.sum(weights * (y - x @ params) ** 2)),
        "interval_method": "delta-method binomial, conditional on positive counts",
    }


def _sample_task(task: tuple[int, float, str, int, int, int]) -> tuple[int, int, float]:
    d, q, mode, shots, seed, task_id = task
    start = time.perf_counter()
    # Task streams are independent of worker assignment and completion order.
    rng = np.random.default_rng(
        np.random.SeedSequence(
            [seed, d, int(round(q * 1e9)), task_id, 0 if mode == "algebra" else 1]
        )
    )
    hz, lz = reference_matrix(d)
    matching = pymatching.Matching.from_check_matrix(
        hz, faults_matrix=lz, weights=math.log((1 - q) / q)
    )
    if mode == "algebra":
        errors = rng.random((shots, d * d)) < q
        events = (errors.astype(np.uint8) @ hz.T) & 1
        truth = ((errors.astype(np.uint8) @ lz.T) & 1).reshape(-1)
    elif mode == "physical":
        memory = physical_memory(d)
        circuit = edited_circuit(memory, q)
        # Stim's own sampler is independent of NumPy's Bernoulli generator.
        stim_seed = int(rng.integers(1, 2**63 - 1))
        dets, obs = circuit.compile_detector_sampler(seed=stim_seed).sample(
            shots, separate_observables=True
        )
        events = dets[:, memory.syndrome_detector_ids].astype(np.uint8)
        truth = obs[:, 0]
        if np.delete(dets, memory.syndrome_detector_ids, axis=1).any():
            raise AssertionError("physical sample has unrelated detector events")
    else:
        raise ValueError("unknown sampling mode")
    prediction = matching.decode_batch(events).reshape(-1).astype(bool)
    return int(np.count_nonzero(prediction ^ truth)), shots, time.perf_counter() - start


def _ordered_results(executor, tasks, workers):
    """Bound outstanding tasks and yield in task-ID order."""
    source = iter(tasks)
    pending = deque(executor.submit(_sample_task, task) for task in islice(source, workers))
    try:
        while pending:
            result = pending.popleft().result()
            yield result
            try:
                pending.append(executor.submit(_sample_task, next(source)))
            except StopIteration:
                pass
    finally:
        for future in pending:
            future.cancel()


def run_point(
    d: int,
    q: float,
    mode: str,
    *,
    workers: int,
    seed: int,
    batch_size: int,
    max_shots: int,
    target_failures: int,
    max_seconds: float,
    executor: ProcessPoolExecutor | None = None,
) -> dict:
    if d not in REFERENCE or not math.isfinite(q) or not 0 < q < 0.5:
        raise ValueError("unsupported distance or q")
    if (
        any(
            isinstance(v, bool) or not isinstance(v, int) or v <= 0
            for v in (workers, batch_size, max_shots, seed)
        )
        or isinstance(target_failures, bool)
        or not isinstance(target_failures, int)
        or target_failures < 0
    ):
        raise ValueError("invalid worker, seed, shot or target cap")
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("max_seconds must be positive")
    start = time.perf_counter()
    completed = 0
    failures = 0
    task_times = 0.0
    # Ordered task IDs and map results make worker-count invariant for fixed caps.
    tasks = (
        (d, q, mode, min(batch_size, max_shots - i * batch_size), seed, i)
        for i in range(math.ceil(max_shots / batch_size))
    )
    if executor is None:
        results = map(_sample_task, tasks)
    else:
        results = _ordered_results(executor, tasks, workers)
    try:
        for count, shots, duration in results:
            completed += shots
            failures += count
            task_times += duration
            if (
                target_failures and failures >= target_failures
            ) or time.perf_counter() - start >= max_seconds:
                break
    finally:
        if executor is not None:
            results.close()
    # At most workers-1 batches can finish after a time stop; counts exclude them.
    ci = wilson(failures, completed)
    return {
        "distance": d,
        "q": q,
        "mode": mode,
        "shots": completed,
        "failures": failures,
        "rate": failures / completed,
        "wilson_95": ci,
        "complete": completed == max_shots or bool(target_failures and failures >= target_failures),
        "stop_reason": (
            "target_failures"
            if target_failures and failures >= target_failures
            else "max_shots"
            if completed == max_shots
            else "max_seconds"
        ),
        "wall_seconds": time.perf_counter() - start,
        "sum_task_seconds": task_times,
    }


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def depolarizing_check(d: int, q: float = 0.04, shots: int = 20000) -> dict:
    """Independent physical samples after the exact single-site X/Y/Z response test."""
    if d not in REFERENCE or not 0 < q < 0.5 or shots < 1:
        raise ValueError("invalid channel check")
    memory = physical_memory(d)
    hz, lz = reference_matrix(d)
    matching = pymatching.Matching.from_check_matrix(
        hz, faults_matrix=lz, weights=math.log((1 - q) / q)
    )
    results = {}
    for channel, probability, seed in (("X_ERROR", q, 371 + d), ("DEPOLARIZE1", 1.5 * q, 971 + d)):
        circuit = edited_circuit(memory, probability, depolarize=channel == "DEPOLARIZE1")
        dets, obs = circuit.compile_detector_sampler(seed=seed).sample(
            shots, separate_observables=True
        )
        prediction = matching.decode_batch(dets[:, memory.syndrome_detector_ids]).reshape(-1)
        count = int(np.count_nonzero(prediction ^ obs[:, 0]))
        results[channel] = {
            "probability": probability,
            "shots": shots,
            "failures": count,
            "wilson_95": wilson(count, shots),
            "circuit_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
        }
    return {
        "q": q,
        "p": 1.5 * q,
        "channels": results,
        "scope": "selected Z-check detectors and logical-Z only; X-check response differs",
    }


def run_experiment(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    censuses = {d: enumerate_failures(d) for d in args.distances}
    physical_checks = {
        d: verify_physical_patterns(d, None if d == 3 else 4) for d in args.distances
    }
    channel_checks = {d: depolarizing_check(d) for d in args.distances}
    points = []
    pool = (
        ProcessPoolExecutor(
            max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
        )
        if args.workers > 1
        else None
    )
    try:
        for d in args.distances:
            for q in args.q_values:
                for mode in ("algebra", "physical"):
                    point = run_point(
                        d,
                        q,
                        mode,
                        workers=args.workers,
                        seed=args.seed,
                        batch_size=args.batch_size,
                        max_shots=args.max_shots,
                        target_failures=args.target_failures,
                        max_seconds=args.max_seconds,
                        executor=pool,
                    )
                    low, high = probability_bounds(d, q, censuses[d])
                    point.update(
                        reference_lower=low,
                        reference_upper=high,
                        normalized_rate=point["rate"] / q ** censuses[d]["t"],
                        exact_inside_wilson=(point["wilson_95"][0] <= low <= point["wilson_95"][1])
                        if d == 3
                        else None,
                        bounds_overlap_wilson=(
                            point["wilson_95"][0] <= high and point["wilson_95"][1] >= low
                        ),
                    )
                    points.append(point)
                    print(
                        f"d={d} q={q:g} {mode}: {point['failures']}/{point['shots']} "
                        f"CI={tuple(round(v, 6) for v in point['wilson_95'])} "
                        f"wall={point['wall_seconds']:.2f}s",
                        flush=True,
                    )
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
    fits = {
        f"d{d}_{mode}": {
            "free_power": fit_points(
                [p for p in points if p["distance"] == d and p["mode"] == mode]
            ),
            "free_curvature": fit_points(
                [p for p in points if p["distance"] == d and p["mode"] == mode], curvature=True
            ),
            "fixed_power": fit_points(
                [p for p in points if p["distance"] == d and p["mode"] == mode],
                fixed_beta=(d + 1) // 2,
            ),
            "fixed_curvature": fit_points(
                [p for p in points if p["distance"] == d and p["mode"] == mode],
                fixed_beta=(d + 1) // 2,
                curvature=True,
            ),
        }
        for d in args.distances
        for mode in ("algebra", "physical")
    }
    circuit_info = {}
    for d in args.distances:
        memory = physical_memory(d)
        circuit_info[d] = {
            "ideal_sha256": hashlib.sha256(str(memory.compiled.ideal_circuit).encode()).hexdigest(),
            "cut_instruction": memory.cut,
            "data_wires": memory.data_wires,
            "cut_convention": (
                "after LogicalInit final TICK, before SyndromeExtraction ancilla reset"
            ),
            "inserted_circuit_sha256_at_first_q": hashlib.sha256(
                str(edited_circuit(memory, args.q_values[0])).encode()
            ).hexdigest(),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "compiler_source_sha": git_sha(),
        "versions": {
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
        },
        "settings": {
            "workers": args.workers,
            "seed": args.seed,
            "batch_size": args.batch_size,
            "max_shots": args.max_shots,
            "target_failures": args.target_failures,
            "max_seconds": args.max_seconds,
            "cpu_count": os.cpu_count(),
        },
        "census": censuses,
        "physical_checks": physical_checks,
        "depolarizing_checks": channel_checks,
        "circuits": circuit_info,
        "points": points,
        "fits": fits,
        "wall_seconds": time.perf_counter() - started,
        "assumptions": [
            "ideal Z memory with one post-preparation independent data X layer",
            "uniform-prior MWPM, same syndrome and reference-relative logical-Z failure",
            "edited Stim circuit is verification-only and has no compiled source fingerprint",
        ],
    }


def save_plot(report: dict, output: Path) -> None:
    """Optional dev-only figure; it never enters the installed runtime."""
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for axis, d in zip(axes, (3, 5), strict=True):
        points = [p for p in report["points"] if p["distance"] == d]
        if not points:
            axis.set_visible(False)
            continue
        census = report["census"][d]
        q_grid = np.geomspace(min(p["q"] for p in points), max(p["q"] for p in points), 200)
        lower, upper = zip(*(probability_bounds(d, q, census) for q in q_grid), strict=True)
        axis.plot(q_grid, lower, color="black", label="exact" if d == 3 else "w≤4 lower")
        if d == 5:
            axis.fill_between(
                q_grid,
                lower,
                upper,
                color="gray",
                alpha=0.2,
                label="rigorous remainder bound",
            )
        for mode, marker in (("algebra", "o"), ("physical", "s")):
            selected = sorted((p for p in points if p["mode"] == mode), key=lambda p: p["q"])
            axis.errorbar(
                [p["q"] for p in selected],
                [p["rate"] for p in selected],
                yerr=[
                    [p["rate"] - p["wilson_95"][0] for p in selected],
                    [p["wilson_95"][1] - p["rate"] for p in selected],
                ],
                fmt=marker,
                capsize=2,
                label=mode,
            )
        axis.set(
            xscale="log",
            yscale="log",
            xlabel="data X probability q",
            ylabel="MWPM logical-Z failure",
            title=f"distance {d}",
        )
        axis.legend(fontsize=8)
    figure.savefig(output, dpi=160)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--seed", type=int, default=731)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--shots", "--max-shots", dest="max_shots", type=int, default=100000)
    parser.add_argument("--target-failures", type=int, default=100)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--distances", type=int, nargs="+", default=[3, 5])
    parser.add_argument("--q-values", type=float, nargs="+", default=[0.008, 0.015, 0.03, 0.05])
    parser.add_argument("--output-dir", type=Path, default=Path("validation/output"))
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--plot", action="store_true", help="write optional PNG via Matplotlib")
    args = parser.parse_args(argv)
    if args.quick:
        args.max_shots = min(args.max_shots, 8192)
        args.target_failures = 0
        args.q_values = [0.02, 0.04, 0.06, 0.08]
    if (
        args.workers < 1
        or args.workers > 8
        or args.seed <= 0
        or args.batch_size < 1
        or args.max_shots < 1
        or args.target_failures < 0
        or args.max_seconds <= 0
        or not args.distances
        or not args.q_values
        or any(d not in REFERENCE for d in args.distances)
        or any(not math.isfinite(q) or not 0 < q < 0.5 for q in args.q_values)
    ):
        parser.error("invalid worker, seed, shot, distance, probability, or time setting")
    report = run_experiment(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)
    with (args.output_dir / "points.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[k for k in report["points"][0] if k != "wilson_95"]
            + ["wilson_low", "wilson_high"],
            lineterminator="\n",
        )
        writer.writeheader()
        for point in report["points"]:
            row = {k: v for k, v in point.items() if k != "wilson_95"}
            row.update(wilson_low=point["wilson_95"][0], wilson_high=point["wilson_95"][1])
            writer.writerow(row)
    if args.plot:
        save_plot(report, args.output_dir / "rates.png")
    print(
        f"report={args.output_dir / 'report.json'} wall={report['wall_seconds']:.2f}s "
        f"workers={args.workers} cpus={os.cpu_count()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
