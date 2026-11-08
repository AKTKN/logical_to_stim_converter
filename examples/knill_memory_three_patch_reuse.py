"""Static Knill memory on three caller-assigned physical surface-code patches.

P0/P1/P2 retain their d² data and d²-1 check-ancilla wires. A BlockUseId epoch
counts reset-to-destructive-readout occupancies, not syndrome-extraction (SE)
rounds. Persistent D teleports; fresh A_t/B_t resource names retire each cycle.
A Knill cycle prepares a Bell pair and destructively reads its encoded Bell
interaction. Resource preparations use d SE rounds by default; ordinary SE
after teleportation has an independently chosen round count. Stages label these
semantic regions, TICKs delimit physical noise layers, and decoder boundaries
are cuts for offline hypotheses. None of these are interchangeable time units.

The declared schedule below authors BindPatch directives outside the compiler.
All physical gates are compiled once; the M6-D restricted temporal/capacity MWPM
consumer replays each raw batch in software. Physical-state width stays fixed;
circuit, metadata and record widths grow with duration. No decoder sees sampled
boundary probes or quantum truth. PyMatching remains an example dependency.
"""

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from logical_to_stim_converter import (
    BindPatch,
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

try:
    from .knill_memory_offline_decoding import analyze_knill, prepare_compiled
    from .memory_offline_decoding import wilson_interval
except ImportError:  # The source distribution also supports direct script execution.
    from knill_memory_offline_decoding import analyze_knill, prepare_compiled
    from memory_offline_decoding import wilson_interval


# Caller-authored (input D, resource A, output B) assignments, repeated as written.
THREE_PATCH_SCHEDULE = (("P0", "P1", "P2"), ("P2", "P0", "P1"), ("P1", "P2", "P0"))


def explicit_three_patch_program(
    *,
    distance=3,
    basis="Z",
    bit=0,
    teleportations=3,
    resource_rounds=None,
    input_rounds=None,
    post_rounds=1,
    allow_open_outputs=False,
    schedule=None,
):
    """Author primitives and explicit reservations for a declared physical schedule.

    ``schedule`` optionally supplies exactly one (D, A, B) physical-block triple
    per cycle, starting with P0/P1/P2. The default repeats THREE_PATCH_SCHEDULE.
    Return a logical program consumable by an ordinary three-block compiler;
    only the compiler checks actual occupancy and executes reset/readout flows.
    """
    if basis not in ("X", "Z") or bit not in (0, 1):
        raise ValueError("Use X/Z basis and binary input bit")
    if type(teleportations) is not int or teleportations < 1:
        raise ValueError("teleportations must be positive")
    if type(post_rounds) is not int or post_rounds < 0:
        raise ValueError("post_rounds must be nonnegative")
    slots = (
        tuple(THREE_PATCH_SCHEDULE[t % 3] for t in range(teleportations))
        if schedule is None
        else tuple(tuple(row) for row in schedule)
    )
    if len(slots) != teleportations or slots[0] != THREE_PATCH_SCHEDULE[0]:
        raise ValueError("Supply one triple per cycle, starting with (P0, P1, P2)")
    previous_output = "P0"
    for row in slots:
        if len(row) != 3 or set(row) != {"P0", "P1", "P2"} or row[0] != previous_output:
            raise ValueError("Each explicit triple must continue D on three distinct P0/P1/P2")
        previous_output = row[2]
    program = [LogicalInit("D", basis, distance if input_rounds is None else input_rounds)]
    if bit:
        program.append(LogicalPauli("D", "Z" if basis == "X" else "X", mode="physical"))
    for t, (_, a, b) in enumerate(slots):
        if t:
            program.extend((BindPatch(f"A{t}", a), BindPatch(f"B{t}", b)))
        program.append(
            KnillEC(
                "D",
                f"A{t}",
                f"B{t}",
                rounds=(distance if resource_rounds is None else resource_rounds),
            )
        )
        if post_rounds:
            program.append(SyndromeExtraction("D", post_rounds))
    if not allow_open_outputs:
        program.append(LogicalMeasure("D", basis))
    return program


def build_explicit_three_patch_knill(*, distance=3, noise_model=None, **parameters):
    """Compile caller-authored reservations on exactly three fixed placed patches.

    Parameters pass to explicit_three_patch_program, including open-output mode.
    Return the canonical artifact with all global detectors, use and raw-record
    history. Bindings add no physical instructions, time layers or noise.
    """
    code = CodeSpec.rotated_surface(distance)
    compiler = CircuitCompiler(
        [LogicalBlock.placed(f"P{i}", code, patch_index=i) for i in range(3)],
        logical_to_block={"D": "P0", "A0": "P1", "B0": "P2"},
    )
    return compiler.compile(
        explicit_three_patch_program(distance=distance, **parameters),
        noise_model=NoiseModel() if noise_model is None else noise_model,
        allow_open_outputs=parameters.get("allow_open_outputs", False),
    )


def prepare_three_patch(
    *,
    distance=3,
    basis="Z",
    bit=0,
    teleportations=3,
    resource_rounds=None,
    input_rounds=None,
    post_rounds=1,
    p=None,
    noise_model=None,
    allow_open_outputs=False,
    schedule=None,
):
    """Build once, then prepare public frame/views/models and M6-D decoder adapters.

    Choose either uniform ``p`` or an explicit NoiseModel. Returned experiment
    accepts unchanged raw batches and independently replaceable stage adapters.
    Ideal MPP boundary probes stay in model circuits, outside physical sampling.
    """
    if p is not None and noise_model is not None:
        raise ValueError("Supply p or noise_model, not both")
    if noise_model is None:
        p = 0.001 if p is None else p
        noise_model = NoiseModel.uniform_depolarizing(p)
    parameters = dict(
        distance=distance,
        basis=basis,
        bit=bit,
        teleportations=teleportations,
        resource_rounds=distance if resource_rounds is None else resource_rounds,
        input_rounds=distance if input_rounds is None else input_rounds,
        post_rounds=post_rounds,
        allow_open_outputs=allow_open_outputs,
        schedule=schedule,
    )
    started = perf_counter()
    compiled = build_explicit_three_patch_knill(noise_model=noise_model, **parameters)
    seconds = perf_counter() - started
    parameters.update(
        p=p,
        noise={
            "default": asdict(noise_model.default),
            "operation_overrides": {
                k: asdict(v) for k, v in noise_model.operation_overrides.items()
            },
        },
    )
    return prepare_compiled(compiled, parameters=parameters, compile_seconds=seconds)


def describe_experiment(experiment):
    """Export compact physical-use, stage/view and canonical-source provenance.

    Every cycle names its actual input/resource/output uses. Epoch histories
    contain reset/readout/owner events; module rows retain global detector/record
    IDs, source fingerprints and model targets. No dense correction maps or shot
    matrices enter the report. The exact DEM remains on the experiment object.
    """
    e, c = experiment, experiment.compiled
    requests = {r.module_id: r for r in e.requests.boundaries}
    requests.update({r.readout.module_id: r for r in e.requests.readouts})
    stages = []
    for kind, module in e.requests.order:
        r = requests[module]
        readout = getattr(r, "readout", None)
        stages.append(
            dict(
                kind=kind,
                module_id=module,
                stage_id=(
                    r.source_preparation.stage_id
                    if kind == "boundary" and r.preparation is not None
                    else next(f.stage for f in c.fragments if f.module_id == module)
                ),
                use=asdict(r.block_use_id),
                global_detector_ids=r.view.detector_map.global_ids,
                global_record_ids=r.view.measurement_map.global_ids,
                target_ids=r.target_ids if kind == "boundary" else (),
                source_preparation=r.source_preparation.module_id,
                record_count=len(r.view.measurements),
                detector_count=len(r.view.detectors),
                source_fingerprint=r.view.source_fingerprint,
                view_id=hashlib.sha256(
                    repr(
                        (
                            r.view.source_fingerprint,
                            r.view.detector_map.global_ids,
                            r.view.measurement_map.global_ids,
                            r.view.observable_map.global_ids,
                        )
                    ).encode()
                ).hexdigest(),
                basis=readout.basis if readout is not None else r.source_preparation.basis,
            )
        )
    return dict(
        physical_patch_count=len({b for b, _ in c.physical_qubit_map}),
        qubits=c.circuit.num_qubits,
        measurements=len(c.measurements),
        detectors=len(c.detectors),
        source_fingerprint=e.frame_plan.source_fingerprint,
        canonical_dem_sha256=hashlib.sha256(
            repr(
                tuple(
                    (i.type, tuple(i.args_copy()), tuple(str(t) for t in i.targets_copy()))
                    for i in e.global_dem.flattened()
                )
            ).encode()
        ).hexdigest(),
        global_dem_errors=e.global_dem.num_errors,
        cycles=[
            dict(
                cycle=t,
                input_use=asdict(b.data_use_id),
                a_use=asdict(b.first_resource_use_id),
                b_use=asdict(b.output_use_id),
                output_use=asdict(b.output_use_id),
                composite_id=b.composite_id,
            )
            for t, b in enumerate(c.bell_measurements)
        ],
        epoch_history={
            bid: [asdict(u) for u in c.block_uses if u.use_id.block_id == bid]
            for bid in ("P0", "P1", "P2")
        },
        bindings=[asdict(b) for b in c.binding_history],
        relocations=[asdict(r) for r in c.relocation_history],
        stages=stages,
        conditional_models=[
            dict(
                composite_id=m.composite_id,
                fault_atoms=len(m.faults),
                exclusive_groups=len({f.exclusive_group for f in m.faults}),
                boundary_convention=m.boundary_convention,
            )
            for m in e.conditional_models
        ],
        decoder_identities=sorted(
            {d.identity for d in (*e.boundary_decoders.values(), *e.readout_decoders.values())}
        ),
        limitations=[
            "Temporal correlated MWPM can retain ambiguous parallel-edge target labels.",
            "Bell matching uses independent unit-weight patch capacity models.",
            "Strict SE windows omit cross-boundary offsets; one round has no temporal evidence.",
            "Residual earlier decoder errors may violate incoming-sector hypotheses.",
            "Only physical-state width is constant; circuit and record widths grow.",
        ],
    )


@dataclass(frozen=True)
class ThreePatchRun:
    """Bounded-batch aggregate with one experiment and no retained raw shot matrix."""

    experiment: object
    seed: int
    shots: int
    errors: int
    batches: int
    batch_size: int
    raw_sha256: str
    timings: dict

    def summary(self):
        """Return JSON-compatible provenance, honest readout failure counts and wall phases."""
        return dict(
            **self.experiment.parameters,
            **describe_experiment(self.experiment),
            seed=self.seed,
            shots=self.shots,
            errors=self.errors,
            logical_error_rate=self.errors / self.shots,
            wilson_95=wilson_interval(self.errors, self.shots),
            batches=self.batches,
            batch_size=self.batch_size,
            raw_batch_sha256=self.raw_sha256,
            timings_seconds=self.timings,
        )


def run_three_patch(*, shots=1000, batch_size=256, seed=7, **parameters):
    """Compile/sample one static circuit, decoding successive bounded raw batches.

    Compile one sampler and call sample once per batch, including the shorter
    last batch. Accumulate final corrected-readout XOR intended-bit failures and
    exclusive wall phases; release each analysis before requesting the next batch.
    Open outputs are available through prepare_three_patch, without a LER label.
    """
    if any(type(n) is not int or n < 1 for n in (shots, batch_size)):
        raise ValueError("Use positive shots and batch_size")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("Use an integer seed in [0, 2**64)")
    if parameters.get("allow_open_outputs", False):
        raise ValueError("LER requires a final destructive readout")
    total = perf_counter()
    e = prepare_three_patch(**parameters)
    timings = dict(e.setup_timings)
    started = perf_counter()
    sampler = e.compiled.circuit.compile_sampler(seed=seed)
    timings["sampler_compile"] = perf_counter() - started
    timings["sampling"] = 0.0
    errors, batches, digest = 0, 0, hashlib.sha256()
    for first in range(0, shots, batch_size):
        started = perf_counter()
        raw = sampler.sample(shots=min(batch_size, shots - first))
        timings["sampling"] += perf_counter() - started
        analysis = analyze_knill(e, raw)
        errors += analysis.errors
        batches += 1
        digest.update(raw.tobytes())
        for label, seconds in analysis.timings.items():
            timings[label] = timings.get(label, 0.0) + seconds
        del analysis, raw
    timings["total_wall"] = perf_counter() - total
    timings["other"] = max(
        0.0, timings["total_wall"] - sum(v for k, v in timings.items() if k != "total_wall")
    )
    return ThreePatchRun(e, seed, shots, errors, batches, batch_size, digest.hexdigest(), timings)


def save_report(runs, directory):
    """Write aggregate JSON, phase CSV and LER/timing figures; omit physical samples."""
    from matplotlib.figure import Figure

    started = perf_counter()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    summaries = [r.summary() for r in runs]
    fig = Figure(figsize=(11, 4), layout="constrained")
    ler, timing = fig.subplots(1, 2)
    labels = [
        f"d={r.experiment.parameters['distance']} {r.experiment.parameters['basis']} "
        f"T={r.experiment.parameters['teleportations']}"
        for r in runs
    ]
    for i, r in enumerate(runs):
        rate = r.errors / r.shots
        lo, hi = wilson_interval(r.errors, r.shots)
        ler.errorbar(
            i, rate, yerr=[[max(0.0, rate - lo)], [max(0.0, hi - rate)]], fmt="o", capsize=3
        )
    ler.set_xticks(range(len(runs)), labels, rotation=30)
    ler.set(ylabel="Failure probability per memory", title="Restricted baseline, 95% Wilson")
    phases = {
        "setup": (
            "compile",
            "global_dem",
            "frame_map_setup",
            "stage_view_models",
            "conditional_fault_models",
            "matching_setup",
        ),
        "sampling": ("sampler_compile", "sampling"),
        "events": ("m2d_compile", "m2d_convert", "event_inputs"),
        "decode": ("temporal_decode", "capacity_decode"),
        "frames/other": ("frame_updates", "final_evaluation", "other"),
    }
    left = [0.0] * len(runs)
    for phase, names in phases.items():
        values = [sum(r.timings[k] for k in names) for r in runs]
        timing.barh(range(len(runs)), values, left=left, label=phase)
        left = [a + b for a, b in zip(left, values, strict=True)]
    timing.set_yticks(range(len(runs)), labels)
    timing.set(xlabel="Exclusive wall seconds", title="Three patches; bounded raw batches")
    timing.legend(fontsize=7)
    for suffix in ("png", "svg"):
        fig.savefig(directory / f"three_patch_ler_and_timing.{suffix}")
    with (directory / "three_patch_timing.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("case", "phase", "seconds"))
        for label, run in zip(labels, runs, strict=True):
            writer.writerows((label, k, v) for k, v in run.timings.items())
    payload = dict(experiments=summaries, report_generation_wall=perf_counter() - started)
    (directory / "three_patch_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def main():
    """Run caller-authored three-patch cases and optionally save an aggregate report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance", type=int, default=3)
    parser.add_argument("--basis", choices=("X", "Z"), default="Z")
    parser.add_argument("--bit", type=int, choices=(0, 1), default=0)
    parser.add_argument("--teleportations", type=int, default=3)
    parser.add_argument("--resource-rounds", type=int)
    parser.add_argument("--input-rounds", type=int)
    parser.add_argument("--post-rounds", type=int, default=1)
    parser.add_argument("--p", type=float, default=0.001)
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--suite", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    cases = (
        [dict(distance=d, basis=b, teleportations=3) for d in (3, 5) for b in "XZ"]
        if args.suite
        else [
            dict(
                distance=args.distance,
                basis=args.basis,
                bit=args.bit,
                teleportations=args.teleportations,
                resource_rounds=args.resource_rounds,
                input_rounds=args.input_rounds,
                post_rounds=args.post_rounds,
            )
        ]
    )
    runs = [
        run_three_patch(
            **case, p=args.p, shots=args.shots, batch_size=args.batch_size, seed=args.seed + i
        )
        for i, case in enumerate(cases)
    ]
    for run in runs:
        print(json.dumps(run.summary()))
    if args.output_dir:
        save_report(runs, args.output_dir)


if __name__ == "__main__":
    main()
