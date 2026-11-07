"""Static Knill memory, replaceable offline stage decoding and exclusive wall times.

The conditional Bell capacity baseline approximates correlated circuit noise by
unit-weight per-patch matching. Its exact conditional fault actions are exported;
no canonical fault, detector or raw measurement is deleted or rewritten.
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
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    SyndromeExtraction,
)
from logical_to_stim_converter.decoding import (
    CorrectionBatch,
    StageInputs,
    StageResult,
    make_conditional_readout_model,
    make_stage_requests,
)
from logical_to_stim_converter.decoding.frames import readonly

try:
    from .memory_offline_decoding import make_matching, wilson_interval
except ImportError:  # Direct script execution; both examples ship in the source distribution.
    from memory_offline_decoding import make_matching, wilson_interval


def build_knill(
    *,
    distance=3,
    basis="Z",
    bit=0,
    teleportations=1,
    resource_rounds=None,
    input_rounds=None,
    post_rounds=1,
    noise_model=None,
    allow_open_outputs=False,
):
    if basis not in ("X", "Z") or bit not in (0, 1):
        raise ValueError("Use X/Z basis and binary input bit")
    if type(teleportations) is not int or teleportations < 1:
        raise ValueError("teleportations must be positive")
    if type(post_rounds) is not int or post_rounds < 0:
        raise ValueError("post_rounds must be nonnegative")
    code = CodeSpec.rotated_surface(distance)
    names = ["D"] + [q for t in range(teleportations) for q in (f"A{t}", f"B{t}")]
    blocks = [
        LogicalBlock.placed(f"physical_{q}", code, patch_index=i) for i, q in enumerate(names)
    ]
    compiler = CircuitCompiler(
        blocks, logical_to_block={q: b.block_id for q, b in zip(names, blocks, strict=True)}
    )
    program = [LogicalInit("D", basis, distance if input_rounds is None else input_rounds)]
    if bit:
        program.append(LogicalPauli("D", "Z" if basis == "X" else "X", mode="physical"))
    for t in range(teleportations):
        program.append(KnillEC("D", f"A{t}", f"B{t}", rounds=resource_rounds))
        if post_rounds:
            program.append(SyndromeExtraction("D", post_rounds))
    if not allow_open_outputs:
        program.append(LogicalMeasure("D", basis))
    return compiler.compile(
        program, noise_model=noise_model or NoiseModel(), allow_open_outputs=allow_open_outputs
    )


class BoundaryMatching:
    """Temporal last-record error inference, then a separate sector representative.

    Ideal probe targets define actual boundary syndrome XOR last recorded syndrome
    and (for preparations) the known prepared logical error. Their predicted values
    are hypotheses, never sampled probes. CSS capacity matching supplies a physical
    representative; the prepared eigenvalue constraint fixes its logical ambiguity.
    """

    identity = "correlated temporal MWPM + CSS sector capacity MWPM"

    def __init__(self, request):
        self.temporal = make_matching(request.detector_error_model)
        self.x = pymatching.Matching.from_check_matrix(request.check_matrix("Z"))
        self.z = pymatching.Matching.from_check_matrix(request.check_matrix("X"))

    def decode_batch(self, request, inputs):
        started = perf_counter()
        predicted = self.temporal.decode_batch(inputs.events, enable_correlations=True).astype(bool)
        temporal_seconds = perf_counter() - started
        started = perf_counter()
        mapping = request.view.measurement_map.global_to_local
        observed = inputs.records[:, [mapping[i] for i in request.last_record_ids]]
        sector = observed ^ predicted[:, : len(request.checks)]
        sx = sector[:, [i for i, c in enumerate(request.checks) if c.basis == "X"]]
        sz = sector[:, [i for i, c in enumerate(request.checks) if c.basis == "Z"]]
        x = self.x.decode_batch(sz).astype(bool)
        z = self.z.decode_batch(sx).astype(bool)
        prep = request.preparation
        if prep is not None:
            support = prep.logical_x if prep.basis == "X" else prep.logical_z
            vector = z if prep.basis == "X" else x
            parity = np.bitwise_xor.reduce(
                vector[:, [prep.data_ids.index(q) for q in support]], axis=1
            )
            difference = parity ^ predicted[:, -1]
            opposite = prep.logical_z if prep.basis == "X" else prep.logical_x
            for q in opposite:
                vector[:, prep.data_ids.index(q)] ^= difference
        bits = np.concatenate((x, z), axis=1)
        effect = np.zeros_like(sector)
        for i, check in enumerate(request.checks):
            vector = z if check.basis == "X" else x
            effect[:, i] = np.bitwise_xor.reduce(
                vector[:, [request.data_ids.index(q) for q in check.support]], axis=1
            )
        return StageResult(
            CorrectionBatch(inputs.source_fingerprint, request.module_id, bits),
            predicted[:, : len(request.checks)],
            sector ^ effect,
            (("temporal_decode", temporal_seconds), ("capacity_decode", perf_counter() - started)),
        )


class ReadoutMatching:
    """Conditional per-patch capacity baseline; not a joint circuit-noise decoder."""

    identity = "conditional unit-weight per-patch capacity MWPM"

    def __init__(self, request, weights=None):
        self.matching = pymatching.Matching.from_check_matrix(request.check_matrix, weights=weights)

    def decode_batch(self, request, inputs):
        started = perf_counter()
        syndrome = (inputs.records.astype(np.uint8) @ request.check_matrix.T % 2).astype(bool)
        syndrome ^= inputs.expected_sector
        flips = self.matching.decode_batch(syndrome).astype(bool)
        return StageResult(
            CorrectionBatch(inputs.source_fingerprint, request.readout.module_id, flips),
            diagnostics=(("capacity_decode", perf_counter() - started),),
        )


@dataclass(frozen=True)
class KnillExperiment:
    compiled: object
    global_dem: object
    frame_plan: object
    requests: object
    conditional_models: tuple
    boundary_decoders: dict
    readout_decoders: dict
    setup_timings: dict
    parameters: dict


def prepare_experiment(
    *,
    distance=3,
    basis="Z",
    bit=0,
    teleportations=1,
    resource_rounds=None,
    input_rounds=None,
    post_rounds=1,
    p=None,
    noise_model=None,
):
    if p is not None and noise_model is not None:
        raise ValueError("Supply p or noise_model, not both")
    if noise_model is None:
        p = 0.001 if p is None else p
        noise_model = NoiseModel.uniform_depolarizing(p)
    timings = {}
    started = perf_counter()
    compiled = build_knill(
        distance=distance,
        basis=basis,
        bit=bit,
        teleportations=teleportations,
        resource_rounds=resource_rounds,
        input_rounds=input_rounds,
        post_rounds=post_rounds,
        noise_model=noise_model,
    )
    timings["compile"] = perf_counter() - started
    parameters = dict(
        distance=distance,
        basis=basis,
        bit=bit,
        teleportations=teleportations,
        resource_rounds=distance if resource_rounds is None else resource_rounds,
        input_rounds=distance if input_rounds is None else input_rounds,
        post_rounds=post_rounds,
        p=p,
        noise={
            "default": asdict(noise_model.default),
            "operation_overrides": {
                k: asdict(v) for k, v in noise_model.operation_overrides.items()
            },
        },
    )
    return prepare_compiled(compiled, parameters=parameters, compile_seconds=timings["compile"])


def prepare_compiled(compiled, *, parameters=None, compile_seconds=0):
    """External consumer setup, also usable with open or reference-entangled artifacts."""
    timings = {"compile": compile_seconds}
    started = perf_counter()
    dem = compiled.circuit.detector_error_model()
    timings["global_dem"] = perf_counter() - started
    started = perf_counter()
    plan = compiled.make_frame_plan()
    timings["frame_map_setup"] = perf_counter() - started
    started = perf_counter()
    requests = make_stage_requests(compiled)
    timings["stage_view_models"] = perf_counter() - started
    started = perf_counter()
    conditional = tuple(
        make_conditional_readout_model(compiled, b) for b in compiled.bell_measurements
    )
    timings["conditional_fault_models"] = perf_counter() - started
    started = perf_counter()
    boundary_decoders = {r.module_id: BoundaryMatching(r) for r in requests.boundaries}
    readout_decoders = {r.readout.module_id: ReadoutMatching(r) for r in requests.readouts}
    timings["matching_setup"] = perf_counter() - started
    parameters = dict(parameters or {})
    return KnillExperiment(
        compiled,
        dem,
        plan,
        requests,
        conditional,
        boundary_decoders,
        readout_decoders,
        timings,
        parameters,
    )


@dataclass(frozen=True)
class KnillAnalysis:
    raw_measurements: np.ndarray
    physical_events: np.ndarray
    physical_observable_flips: np.ndarray
    interpreted_measurements: np.ndarray
    logical_values: np.ndarray
    failures: np.ndarray
    diagnostics: tuple
    timings: dict
    final_x: np.ndarray
    final_z: np.ndarray

    @property
    def errors(self):
        return int(np.count_nonzero(np.any(self.failures, axis=1)))

    @property
    def logical_error_rate(self):
        return self.errors / len(self.raw_measurements)


def analyze_knill(experiment, raw, *, boundary_decoders=None, readout_decoders=None):
    """Replay unchanged physical records; adapters see only public causal inputs."""
    c, plan, requests = experiment.compiled, experiment.frame_plan, experiment.requests
    decoders = experiment.boundary_decoders if boundary_decoders is None else boundary_decoders
    readout_decoders = experiment.readout_decoders if readout_decoders is None else readout_decoders
    timings = dict.fromkeys(
        ("event_inputs", "temporal_decode", "capacity_decode", "frame_updates"), 0.0
    )
    started = perf_counter()
    converter = c.circuit.compile_m2d_converter()
    timings["m2d_compile"] = perf_counter() - started
    started = perf_counter()
    events, truth = converter.convert(measurements=raw, separate_observables=True)
    timings["m2d_convert"] = perf_counter() - started
    started = perf_counter()
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    timings["frame_updates"] += perf_counter() - started
    sectors = np.zeros((len(raw), len(requests.sector_input_ids)), dtype=bool)
    boundaries = {r.module_id: r for r in requests.boundaries}
    readouts = {r.readout.module_id: r for r in requests.readouts}
    diagnostics = []
    for kind, module in requests.order:
        started = perf_counter()
        request = boundaries[module] if kind == "boundary" else readouts[module]
        interpreted = state.interpreted_measurements
        local_events = state.events(request.view)
        local_records = request.view.project_raw_measurements(interpreted)
        expected = (
            request.sector_map.apply(sectors) ^ request.sector_constant
            if kind == "readout"
            else None
        )
        inputs = StageInputs(
            plan.source_fingerprint,
            readonly(local_events),
            readonly(local_records),
            None if expected is None else readonly(expected),
        )
        timings["event_inputs"] += perf_counter() - started
        result = (
            decoders[module] if kind == "boundary" else readout_decoders[module]
        ).decode_batch(request, inputs)
        if result.correction.boundary_id != module:
            raise ValueError("Decoder returned a different stage boundary")
        for label, seconds in result.diagnostics:
            if label in ("temporal_decode", "capacity_decode"):
                timings[label] += seconds
        started = perf_counter()
        state.apply(result.correction)
        timings["frame_updates"] += perf_counter() - started
        if kind == "boundary":
            if result.net_sector is None or result.net_sector.shape != (
                len(raw),
                len(request.checks),
            ):
                raise ValueError("Boundary decoder must predict net post-correction sectors")
            for j, check in enumerate(request.checks):
                sectors[:, requests.sector_input_ids.index((module, check.check_id))] = (
                    result.net_sector[:, j]
                )
        diagnostics.append((module, readonly(local_events), result, inputs.expected_sector))
    started = perf_counter()
    interpreted = state.interpreted_measurements
    values = np.empty((len(raw), len(c.observables)), dtype=bool)
    for o in c.observables:
        values[:, o.index] = np.bitwise_xor.reduce(
            interpreted[:, o.readout_measurement_indices], axis=1
        )
    expected = np.array([o.expected_value for o in c.observables], dtype=bool)
    failures = values ^ expected
    timings["final_evaluation"] = perf_counter() - started
    return KnillAnalysis(
        readonly(raw),
        readonly(events),
        readonly(truth),
        interpreted,
        readonly(values),
        readonly(failures),
        tuple(diagnostics),
        timings,
        state.final_x,
        state.final_z,
    )


@dataclass(frozen=True)
class KnillRun:
    experiment: KnillExperiment
    analysis: KnillAnalysis
    seed: int
    timings: dict

    def summary(self):
        e, a = self.experiment, self.analysis
        return {
            **e.parameters,
            "seed": self.seed,
            "shots": len(a.raw_measurements),
            "errors": a.errors,
            "logical_error_rate": a.logical_error_rate,
            "source_fingerprint": e.frame_plan.source_fingerprint,
            "raw_batch_sha256": hashlib.sha256(a.raw_measurements.tobytes()).hexdigest(),
            "decoder_identities": [BoundaryMatching.identity, ReadoutMatching.identity],
            "baseline_limitations": [
                "Temporal MWPM parallel edges can retain one representative's fault labels.",
                "Bell capacity MWPM uses unit-weight independent patches, "
                "not joint fault inference.",
                "Strict SE windows omit cross-boundary offsets; "
                "one round has no temporal evidence.",
                "Earlier residual decoder errors can violate the conditional "
                "incoming-sector hypothesis.",
            ],
            "timings_seconds": self.timings,
            "circuit": {
                "qubits": e.compiled.circuit.num_qubits,
                "measurements": len(e.compiled.measurements),
                "detectors": len(e.compiled.detectors),
                "global_dem_errors": e.global_dem.num_errors,
            },
            "boundary_requests": [
                {
                    "module_id": r.module_id,
                    "block_id": r.block_id,
                    "global_detector_ids": r.view.detector_map.global_ids,
                    "global_record_ids": r.view.measurement_map.global_ids,
                    "target_ids": r.target_ids,
                }
                for r in e.requests.boundaries
            ],
            "conditional_models": [
                {
                    "composite_id": m.composite_id,
                    "boundary_convention": m.boundary_convention,
                    "fault_atoms": len(m.faults),
                    "exclusive_groups": len({f.exclusive_group for f in m.faults}),
                }
                for m in e.conditional_models
            ],
        }


def run_knill(*, shots=1000, seed=7, **parameters):
    if type(shots) is not int or shots < 1 or type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("Use positive shots and an integer seed in [0, 2**64)")
    total = perf_counter()
    experiment = prepare_experiment(**parameters)
    timings = dict(experiment.setup_timings)
    started = perf_counter()
    sampler = experiment.compiled.circuit.compile_sampler(seed=seed)
    timings["sampler_compile"] = perf_counter() - started
    started = perf_counter()
    raw = sampler.sample(shots=shots)
    timings["sampling"] = perf_counter() - started
    analysis = analyze_knill(experiment, raw)
    timings.update(analysis.timings)
    timings["total_wall"] = perf_counter() - total
    timings["other"] = max(
        0.0, timings["total_wall"] - sum(v for k, v in timings.items() if k != "total_wall")
    )
    return KnillRun(experiment, analysis, seed, timings)


def save_report(runs, directory, *, process_wall_before_report=None):
    from matplotlib import __version__ as matplotlib_version
    from matplotlib.figure import Figure

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    summaries = [run.summary() for run in runs]
    fig = Figure(figsize=(12, 4.8), layout="constrained")
    ler, timing = fig.subplots(1, 2)
    for basis in ("X", "Z"):
        for t in (1, 2):
            group = [
                r
                for r in runs
                if r.experiment.parameters["basis"] == basis
                and r.experiment.parameters["teleportations"] == t
            ]
            group.sort(key=lambda r: r.experiment.parameters["distance"])
            if not group:
                continue
            rates = np.array([r.analysis.logical_error_rate for r in group])
            intervals = np.array(
                [
                    wilson_interval(r.analysis.errors, len(r.analysis.raw_measurements))
                    for r in group
                ]
            ).T
            ler.errorbar(
                [r.experiment.parameters["distance"] for r in group],
                rates,
                yerr=[rates - intervals[0], intervals[1] - rates],
                fmt="o-",
                capsize=3,
                label=f"{basis}, T={t}",
            )
    ler.set(
        xlabel="Code distance",
        ylabel="Failure probability per memory",
        title="Knill memory: conditional modular baseline",
        ylim=(0, None),
    )
    ler.set_xticks(sorted({r.experiment.parameters["distance"] for r in runs}))
    ler.legend()
    labels = [
        f"d={r.experiment.parameters['distance']} {r.experiment.parameters['basis']} "
        f"T={r.experiment.parameters['teleportations']}"
        for r in runs
    ]
    groups = {
        "compile": ("compile",),
        "model/map setup": (
            "global_dem",
            "frame_map_setup",
            "stage_view_models",
            "conditional_fault_models",
            "matching_setup",
        ),
        "physical sampling": ("sampler_compile", "sampling"),
        "m2d/events": ("m2d_compile", "m2d_convert", "event_inputs"),
        "stage decoding": ("temporal_decode", "capacity_decode"),
        "frame/evaluation/other": ("frame_updates", "final_evaluation", "other"),
    }
    bottom = np.zeros(len(runs))
    for label, names in groups.items():
        values = np.array([sum(r.timings[n] for n in names) for r in runs])
        timing.barh(np.arange(len(runs)), values, left=bottom, label=label)
        bottom += values
    timing.set_yticks(np.arange(len(runs)), labels, fontsize=8)
    timing.set(
        xlabel="Wall seconds (exclusive phases)", title="One-time setup versus batch execution"
    )
    timing.legend(fontsize=7, loc="upper right")
    timing.invert_yaxis()
    probabilities = sorted(
        {r.experiment.parameters["p"] for r in runs if r.experiment.parameters.get("p") is not None}
    )
    fig.suptitle(
        f"Static Knill memory | p={probabilities} | shots/case="
        f"{sorted({len(r.analysis.raw_measurements) for r in runs})}\n"
        "95% Wilson intervals; conditional per-patch capacity approximation",
        fontsize=11,
    )
    fig.savefig(directory / "knill_ler_and_timing.png", dpi=180)
    svg = directory / "knill_ler_and_timing.svg"
    fig.savefig(svg, metadata={"Date": None})
    svg.write_text(
        "\n".join(s.rstrip() for s in svg.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    with (directory / "knill_timing.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        phases = list(runs[0].timings)
        writer.writerow(["distance", "basis", "teleportations", "shots", *phases])
        for r in runs:
            writer.writerow(
                [r.experiment.parameters[k] for k in ("distance", "basis", "teleportations")]
                + [len(r.analysis.raw_measurements), *[r.timings[k] for k in phases]]
            )
    payload = {
        "versions": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib_version,
            "platform": platform.platform(),
        },
        "timing_convention": (
            "perf_counter wall seconds; exclusive phases; no performance thresholds"
        ),
        "process_wall_before_report": process_wall_before_report,
        "report_generation_wall": perf_counter() - started,
        "experiments": summaries,
    }
    (directory / "knill_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance", type=int, default=3)
    parser.add_argument("--basis", choices=("X", "Z"), default="Z")
    parser.add_argument("--bit", type=int, choices=(0, 1), default=0)
    parser.add_argument("--teleportations", type=int, default=1)
    parser.add_argument("--resource-rounds", type=int)
    parser.add_argument("--post-rounds", type=int, default=1)
    parser.add_argument("--p", type=float, default=0.001)
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--suite", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    started = perf_counter()
    cases = (
        [
            dict(distance=d, basis=b, teleportations=t)
            for d in (3, 5)
            for b in ("X", "Z")
            for t in (1, 2)
        ]
        if args.suite
        else [
            dict(
                distance=args.distance,
                basis=args.basis,
                teleportations=args.teleportations,
                bit=args.bit,
                resource_rounds=args.resource_rounds,
                post_rounds=args.post_rounds,
            )
        ]
    )
    runs = [
        run_knill(**case, p=args.p, shots=args.shots, seed=args.seed + i)
        for i, case in enumerate(cases)
    ]
    for r in runs:
        print(json.dumps(r.summary()))
    if args.output_dir:
        save_report(runs, args.output_dir, process_wall_before_report=perf_counter() - started)


if __name__ == "__main__":
    main()
