"""Ordinary memory MWPM demonstration; sampling and decoding stay outside the package.

R counts all syndrome rounds: one in LogicalInit and R-1 in SyndromeExtraction.
Run with .[dev] installed. --suite is five fixed demonstration cases, not a runner.
"""

import argparse
import csv
import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import pymatching
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    CompiledCircuit,
    DecoderView,
    DEMOptions,
    DetectorSelector,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    observable_local_views,
)
from logical_to_stim_converter.decoding import DEMConstructionError


class MatchingModelError(ValueError):
    """This example's matching approximation cannot represent the supplied model."""


def make_matching(model):
    """Reject undecomposed hyperedges before PyMatching can silently ignore them.

    ^ components are correlated suggestions, not independent physical faults.
    PyMatching's two-pass correlated MWPM uses them heuristically; it is not an
    exact maximum-likelihood decoder. The source DEM is never modified.
    """
    for instruction in model.flattened():
        if instruction.type != "error":
            continue
        detectors = set()
        for target in (*instruction.targets_copy(), stim.target_separator()):
            if target.is_separator():
                if len(detectors) > 2:
                    raise MatchingModelError(
                        "Undecomposed hyperedge: a matching component flips more than two "
                        "detectors. "
                        "Request Stim decomposition or supply a supported noise model; no faults "
                        "were removed."
                    )
                detectors.clear()
            elif target.is_relative_detector_id():
                detectors.symmetric_difference_update((target.val,))
    matching = pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
    # Preserve output width even for a noiseless/unflippable observable.
    matching.ensure_num_fault_ids(model.num_observables)
    return matching


def readonly(values):
    values = np.asarray(values, dtype=np.bool_)
    return np.frombuffer(values.tobytes(), dtype=np.bool_).reshape(values.shape)


@dataclass(frozen=True)
class DecodingResult:
    strategy: str
    view: DecoderView
    predicted_flips: np.ndarray
    failures: np.ndarray
    decoding_seconds: float

    @property
    def logical_errors(self):
        return int(np.count_nonzero(np.any(self.failures, axis=1)))

    @property
    def logical_error_rate(self):
        return self.logical_errors / len(self.failures)

    @property
    def per_observable_errors(self):
        return tuple(int(n) for n in np.count_nonzero(self.failures, axis=0))


@dataclass(frozen=True)
class MemoryRun:
    compiled: CompiledCircuit
    global_dem: stim.DetectorErrorModel
    parameters: dict
    raw_measurements: np.ndarray
    detection_events: np.ndarray
    observable_flips: np.ndarray
    strategies: tuple[DecodingResult, ...]
    sampling_seconds: float

    def summary(self):
        return {
            **self.parameters,
            "shots": len(self.raw_measurements),
            "source_fingerprint": self.strategies[0].view.source_fingerprint,
            "raw_batch_sha256": hashlib.sha256(self.raw_measurements.tobytes()).hexdigest(),
            "sampling_seconds": self.sampling_seconds,
            "global_dem_errors": self.global_dem.num_errors,
            "observable_metadata": [asdict(o) for o in self.compiled.observables],
            "decoder": "PyMatching 2.3.1 two-pass correlated MWPM (heuristic)",
            "strategies": [
                {
                    "strategy": result.strategy,
                    "global_detector_ids": result.view.detector_map.global_ids,
                    "global_observable_ids": result.view.observable_map.global_ids,
                    "logical_errors": result.logical_errors,
                    "logical_error_rate": result.logical_error_rate,
                    "per_observable_errors": result.per_observable_errors,
                    "decoding_seconds": result.decoding_seconds,
                    "dem_errors": result.view.detector_error_model.num_errors,
                    "correlated_error_instructions": sum(
                        any(t.is_separator() for t in inst.targets_copy())
                        for inst in result.view.detector_error_model.flattened()
                        if inst.type == "error"
                    ),
                }
                for result in self.strategies
            ],
        }


def build_memory(
    *, distance=3, rounds=3, bases=("Z",), noise_model=None, reverse_registration=False
):
    """One memory or two independent concurrent memories with stable physical IDs."""
    if type(rounds) is not int or rounds < 1:
        raise ValueError("rounds must be a positive total syndrome-round count")
    bases = tuple(bases)
    if len(bases) not in (1, 2) or any(b not in ("X", "Z") for b in bases):
        raise ValueError("Use one or two X/Z memory bases")
    code = CodeSpec.rotated_surface(distance)
    blocks = [LogicalBlock.placed(f"physical_{i}", code, patch_index=i) for i in range(len(bases))]
    # Logical ordering deliberately differs from physical ordering in the two-patch case.
    logicals = ("memory",) if len(bases) == 1 else ("z_input", "a_input")
    compiler = CircuitCompiler(
        blocks[::-1] if reverse_registration else blocks,
        logical_to_block={q: b.block_id for q, b in zip(logicals, blocks, strict=True)},
    )
    program = [[LogicalInit(q, b, 1) for q, b in zip(logicals, bases, strict=True)]]
    if rounds > 1:
        program.append(SyndromeExtraction(logicals, rounds - 1))
    program.append([LogicalMeasure(q, b) for q, b in zip(logicals, bases, strict=True)])
    return compiler.compile(program, noise_model=noise_model or NoiseModel())


def analyze_memory(compiled, raw_measurements, *, parameters=None, sampling_seconds=0):
    """Decode an existing global batch using only public converter/view APIs."""
    if not compiled.observables or compiled.bell_measurements:
        raise ValueError("This example requires reliable ordinary-memory outputs")
    # The canonical fault model remains undecomposed. Only decoder views request decomposition.
    global_dem = compiled.circuit.detector_error_model()
    options = DEMOptions(decompose_errors=True)
    try:
        full = compiled.make_decoder_view(dem_options=options)
        local = observable_local_views(compiled, dem_options=options)
        strict = tuple(
            compiled.make_decoder_view(
                detector_selector=DetectorSelector(
                    block_ids=(o.block_id,), block_membership="strict"
                ),
                observable_selector=(o.index,),
                dem_options=options,
            )
            for o in compiled.observables
        )
    except DEMConstructionError as ex:
        raise MatchingModelError(f"Stim graphlike decomposition failed: {ex}") from ex
    raw = readonly(full.project_raw_measurements(raw_measurements))
    if not len(raw):
        raise ValueError("At least one shot is required")
    events, truth = compiled.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    views = [("global", full)]
    views += [
        (f"observable/{o.logical_id}", v) for o, v in zip(compiled.observables, local, strict=True)
    ]
    views += [
        (f"patch/{o.logical_id}", v) for o, v in zip(compiled.observables, strict, strict=True)
    ]
    results = []
    for name, view in views:
        matching = make_matching(view.detector_error_model)
        inputs = view.project_detection_events(events, source_fingerprint=full.source_fingerprint)
        started = perf_counter()
        predicted = matching.decode_batch(inputs, enable_correlations=True).astype(bool)
        elapsed = perf_counter() - started
        labels = view.project_observable_flips(truth)
        if predicted.shape != labels.shape:
            raise ValueError("Decoder predictions disagree with the selected observable ordering")
        results.append(
            DecodingResult(name, view, readonly(predicted), readonly(predicted ^ labels), elapsed)
        )
    return MemoryRun(
        compiled,
        global_dem,
        dict(parameters or {}),
        raw,
        readonly(events),
        readonly(truth),
        tuple(results),
        sampling_seconds,
    )


def run_memory(
    *,
    distance=3,
    rounds=None,
    basis="Z",
    two_patch=False,
    p=None,
    noise_model=None,
    shots=1000,
    seed=7,
    reverse_registration=False,
):
    """Sample once, then compare offline decoders. Custom noise is reported with p=None."""
    if type(shots) is not int or shots < 1:
        raise ValueError("shots must be positive")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be an integer in [0, 2**64)")
    if noise_model is not None and p is not None:
        raise ValueError("Supply either p or an explicit noise_model")
    if noise_model is None:
        p = 0.001 if p is None else p
        noise_model = NoiseModel.uniform_depolarizing(p)
    rounds = distance if rounds is None else rounds
    bases = ("X", "Z") if two_patch else (basis,)
    compiled = build_memory(
        distance=distance,
        rounds=rounds,
        bases=bases,
        noise_model=noise_model,
        reverse_registration=reverse_registration,
    )
    started = perf_counter()
    raw = compiled.circuit.compile_sampler(seed=seed).sample(shots=shots)
    elapsed = perf_counter() - started
    parameters = {
        "distance": distance,
        "rounds": rounds,
        "basis": "".join(bases),
        "p": p,
        "seed": seed,
        "noise": {
            "default": asdict(noise_model.default),
            "operation_overrides": {
                k: asdict(v) for k, v in noise_model.operation_overrides.items()
            },
        },
    }
    return analyze_memory(compiled, raw, parameters=parameters, sampling_seconds=elapsed)


def wilson_interval(errors, shots):
    """95% Wilson binomial interval; zero observed errors still has an upper bound."""
    z = 1.959963984540054
    p = errors / shots
    center = (p + z * z / (2 * shots)) / (1 + z * z / shots)
    half = z * np.sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / (1 + z * z / shots)
    return min(p, max(0.0, center - half)), max(p, min(1.0, center + half))


def save_report(runs, directory):
    """Write small aggregate results and a figure, with no persistent raw-shot dataset."""
    from matplotlib import __version__ as matplotlib_version
    from matplotlib.figure import Figure

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    summaries = [r.summary() for r in runs]
    payload = {
        "versions": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib_version,
            "machine": platform.machine(),
        },
        "rounds_convention": "R total syndrome rounds, including one LogicalInit round",
        "failure_convention": "any predicted XOR actual Stim observable flip in the view",
        "interval": "95% Wilson binomial; views reuse paired samples",
        "experiments": summaries,
    }
    (directory / "memory_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    with (directory / "memory_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            (
                "distance",
                "rounds",
                "basis",
                "p",
                "seed",
                "shots",
                "strategy",
                "global_observable_ids",
                "logical_errors",
                "logical_error_rate",
            )
        )
        for run in summaries:
            for result in run["strategies"]:
                writer.writerow(
                    [run[k] for k in ("distance", "rounds", "basis", "p", "seed", "shots")]
                    + [
                        result[k]
                        for k in (
                            "strategy",
                            "global_observable_ids",
                            "logical_errors",
                            "logical_error_rate",
                        )
                    ]
                )
    fig = Figure(figsize=(11, 4.5), layout="constrained")
    left, right = fig.subplots(1, 2)
    singles = [r for r in runs if len(r.compiled.observables) == 1]
    for basis in ("X", "Z"):
        group = sorted(
            [r for r in singles if r.parameters["basis"] == basis],
            key=lambda r: r.parameters["distance"],
        )
        if not group:
            continue
        points = [r.strategies[0].logical_error_rate for r in group]
        intervals = np.array(
            [
                wilson_interval(r.strategies[0].logical_errors, len(r.raw_measurements))
                for r in group
            ]
        ).T
        left.errorbar(
            [r.parameters["distance"] for r in group],
            points,
            yerr=np.array([points - intervals[0], intervals[1] - points]),
            fmt="o-",
            capsize=4,
            label=f"{basis} memory",
        )
        for r, y in zip(group, points, strict=True):
            left.annotate(
                f"R={r.parameters['rounds']}",
                (r.parameters["distance"], y),
                xytext=(4, 7),
                textcoords="offset points",
                fontsize=8,
            )
    left.set(
        xlabel="Code distance d",
        ylabel="Logical failure probability per memory",
        title="Single patch: global correlated MWPM",
        ylim=(0, None),
    )
    if singles:
        left.legend()
    mixed = next((r for r in runs if len(r.compiled.observables) == 2), None)
    if mixed is not None:
        positions = np.arange(2)
        for offset, strategy in zip(
            (-0.22, 0, 0.22), ("global", "observable", "patch"), strict=True
        ):
            errors = []
            for o in mixed.compiled.observables:
                result = next(
                    r
                    for r in mixed.strategies
                    if r.strategy
                    == ("global" if strategy == "global" else f"{strategy}/{o.logical_id}")
                )
                errors.append(
                    result.per_observable_errors[
                        result.view.observable_map.global_to_local[o.index]
                    ]
                )
            rates = np.array(errors) / len(mixed.raw_measurements)
            intervals = np.array(
                [wilson_interval(k, len(mixed.raw_measurements)) for k in errors]
            ).T
            right.errorbar(
                positions + offset,
                rates,
                yerr=[rates - intervals[0], intervals[1] - rates],
                fmt="o",
                capsize=4,
                label=strategy,
            )
        right.set_xticks(
            positions,
            [f"{o.logical_id}\n{o.basis}, global L{o.index}" for o in mixed.compiled.observables],
        )
        right.set(
            title=f"Mixed patches: same raw batch, d={mixed.parameters['distance']}, "
            f"R={mixed.parameters['rounds']}",
            ylabel="Per-observable failure probability",
            ylim=(0, None),
        )
        right.legend()
    else:
        right.axis("off")
        right.text(
            0.05,
            0.8,
            "One raw batch reused for global,\nobservable-local and strict patch views.\n"
            "95% Wilson intervals; no threshold claim.",
            transform=right.transAxes,
        )
    probabilities = sorted({r.parameters["p"] for r in runs if r.parameters["p"] is not None})
    shots = sorted({len(r.raw_measurements) for r in runs})
    fig.suptitle(
        f"Rotated surface-code memory | p={probabilities} | shots/case={shots}\n"
        "95% Wilson intervals; correlated MWPM approximation",
        fontsize=12,
    )
    fig.savefig(directory / "memory_ler.png", dpi=180)
    fig.savefig(directory / "memory_ler.svg", metadata={"Date": None})
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance", type=int, default=3)
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--basis", choices=("X", "Z"), default="Z")
    parser.add_argument("--p", type=float, default=0.001)
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--two-patch", action="store_true")
    parser.add_argument(
        "--suite", action="store_true", help="Fixed X/Z d=3/5 R=d and mixed-patch demo"
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.suite:
        cases = [dict(distance=d, rounds=d, basis=b) for d in (3, 5) for b in ("X", "Z")]
        cases.append(dict(distance=3, rounds=3, two_patch=True))
        runs = [
            run_memory(**case, p=args.p, shots=args.shots, seed=args.seed + i)
            for i, case in enumerate(cases)
        ]
    else:
        runs = [
            run_memory(
                distance=args.distance,
                rounds=args.rounds,
                basis=args.basis,
                two_patch=args.two_patch,
                p=args.p,
                shots=args.shots,
                seed=args.seed,
            )
        ]
    for run in runs:
        print(json.dumps(run.summary()))
    if args.output_dir is not None:
        save_report(runs, args.output_dir)


if __name__ == "__main__":
    main()
