"""Public-only four-logical-qubit Clifford/parallel-Knill consumer.

Run from any directory with the package installed. The recorded-sector recovery
below is a noiseless preparation check, not a noisy MWPM decoder or LER estimate.
Consumers can replace it with their own source-bound CorrectionBatch hypotheses.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import stim

from logical_to_stim_converter import (
    BlockUseId,
    LogicalPauliProduct,
    NoiseModel,
    NoiseParameters,
    PostInitializationNoise,
    ResourcePreparationNoise,
    parse_logical_circuit,
)
from logical_to_stim_converter.decoding import CorrectionBatch, make_stage_requests


def deep_clifford_source(*, distance=3, depth=2, cycles=1):
    """Author the explicit three-patch rotation for each persistent Q0..Q3."""
    if depth not in (2, 3) or cycles not in (1, 2):
        raise ValueError("Use depth 2/3 and 1/2 Knill cycles per Clifford layer")
    lines = ["FORMAT(1)", f"CODE sc ROTATED_SURFACE({distance})"]
    for q in range(4):
        for p in range(3):
            lines.append(f"PATCH P{q}_{p} sc index={3 * q + p}")
    for q in range(4):
        lines.extend((f"BIND Q{q} P{q}_0", f"INIT_X[initial_q{q}](1) Q{q} noise=ideal"))
    logical = stim.Circuit()
    schedule = ((0, 1, 2), (2, 0, 1), (1, 2, 0))
    cycle = 0
    for layer in range(depth):
        targets = (1, 3) if layer % 2 == 0 else (0, 2)
        lines.extend(("PARALLEL {", *(f"H Q{q}" for q in targets), "}"))
        logical.append("H", targets)
        pairs = ((0, 1), (2, 3)) if layer % 2 == 0 else ((1, 2), (3, 0))
        lines.extend(("PARALLEL {", *(f"CX Q{c} Q{t}" for c, t in pairs), "}"))
        logical.append("CX", [i for pair in pairs for i in pair])
        for q, axis in enumerate(("X", "Y", "Z", "Y")):
            lines.append(f"{axis} Q{q} mode=transversal")
            logical.append(axis, [q])
        for _ in range(cycles):
            _, a, b = schedule[cycle % 3]
            for q in range(4):
                lines.extend((f"BIND A{cycle}_{q} P{q}_{a}", f"BIND B{cycle}_{q} P{q}_{b}"))
            lines.extend(
                (
                    "PARALLEL {",
                    *(
                        f"KNILL_EC[ec{cycle}_q{q}]({distance}) Q{q} A{cycle}_{q} B{cycle}_{q}"
                        for q in range(4)
                    ),
                    "}",
                )
            )
            cycle += 1
    lines.extend(("PARALLEL {", *(f"SE[final_se_q{q}](1) Q{q} noise=ideal" for q in range(4)), "}"))
    generators = []
    for q in range(4):
        p = stim.PauliString(4)
        p[q] = "X"
        p = p.after(logical)
        generators.append(
            LogicalPauliProduct(
                {f"Q{i}": "_XYZ"[p[i]] for i in range(4) if p[i]},
                sign=int(p.sign.real),
                label=f"G{q}",
            )
        )
    return "\n".join(lines) + "\n", tuple(generators)


def experiment_noise(*, probability=0.001, p_st=0.003, ideal_resource=True, input_error=0):
    """Case A uses M9; Case B inherits ordinary d-round initialization noise."""
    return NoiseModel(
        NoiseParameters(*(probability for _ in range(5))),
        resource_preparation=ResourcePreparationNoise(ideal_resource, p_st),
        post_initialization=tuple(
            PostInitializationNoise(f"initial_q{q}", BlockUseId(f"P{q}_0", 0), input_error)
            for q in range(4)
        )
        if input_error
        else (),
    )


def solve_sector(matrix, syndrome):
    """Consumer-owned free-zero GF(2) representative for exact noiseless checks."""
    matrix = np.asarray(matrix, dtype=bool).copy()
    rhs = np.asarray(syndrome, dtype=bool).T.copy()
    pivot, columns = 0, []
    for column in range(matrix.shape[1]):
        rows = np.flatnonzero(matrix[pivot:, column])
        if not len(rows):
            continue
        selected = pivot + rows[0]
        matrix[[pivot, selected]] = matrix[[selected, pivot]]
        rhs[[pivot, selected]] = rhs[[selected, pivot]]
        for row in range(len(matrix)):
            if row != pivot and matrix[row, column]:
                matrix[row] ^= matrix[pivot]
                rhs[row] ^= rhs[pivot]
        columns.append(column)
        pivot += 1
    if rhs[pivot:].any():
        raise ValueError("Inconsistent recorded sector")
    out = np.zeros((rhs.shape[1], matrix.shape[1]), dtype=bool)
    out[:, columns] = rhs[:pivot].T
    return out


def recorded_sector_frames(compiled, plan, requests, raw):
    """Replay one raw batch; no terminal outcome enters correction selection.

    Assumes perfect final SE/result bits. This intentionally limited consumer
    verifies ideal physics; noisy experiments need an external decoder adapter.
    """
    frames = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    boundaries = {b.module_id: b for b in requests.boundaries}
    for kind, module in requests.order:
        if kind != "boundary":
            continue  # Identity readout-error hypothesis.
        request = boundaries[module]
        current = frames.interpreted_measurements[:, request.last_record_ids]
        parts = []
        for basis in ("Z", "X"):
            matrix = request.check_matrix(basis)
            rhs = current[:, [i for i, check in enumerate(request.checks) if check.basis == basis]]
            prep = request.preparation
            if prep is not None and prep.basis == basis:
                support = prep.logical_x if basis == "X" else prep.logical_z
                matrix = np.vstack((matrix, [q in support for q in request.data_ids]))
                rhs = np.column_stack((rhs, np.zeros(len(rhs), dtype=bool)))
            parts.append(solve_sector(matrix, rhs))
        boundary = plan.boundary_by_id[module]
        frames.apply(
            CorrectionBatch(
                plan.source_fingerprint,
                module,
                np.concatenate(parts, axis=1),
                request.block_use_id,
                boundary.input_ids,
            )
        )
    return frames


def run(*, shots=16, probability=0.001, output=None, ideal_resource=True, depth=2, cycles=1):
    source, stabilizers = deep_clifford_source(depth=depth, cycles=cycles)
    program = parse_logical_circuit(source)
    ideal = program.compile(allow_open_outputs=True)
    ideal.validate_metadata()
    requests, plan = make_stage_requests(ideal), ideal.make_frame_plan()
    probe = ideal.make_terminal_observable_probe(stabilizers)
    samples = probe.circuit.compile_sampler(seed=113).sample(shots)
    raw, _ = probe.split_measurements(samples)
    frames = recorded_sector_frames(ideal, plan, requests, raw)
    assert not probe.corrected_flips(samples, frames).any()
    compiled = program.compile(
        allow_open_outputs=True,
        noise_model=experiment_noise(probability=probability, ideal_resource=ideal_resource),
    )
    compiled.validate_metadata()
    noisy_requests = make_stage_requests(compiled)
    compiled.make_frame_plan()
    noisy_probe = compiled.make_terminal_observable_probe(stabilizers)
    noisy_samples = noisy_probe.circuit.compile_sampler(seed=114).sample(shots)
    view = compiled.make_decoder_view()
    assert noisy_samples.shape == (shots, len(compiled.measurements) + 4)
    for request in noisy_requests.boundaries:
        assert max(request.last_record_ids) < len(compiled.measurements)
        request.detector_error_model
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        (output / "program.lstim").write_text(source, encoding="utf-8")
        compiled.circuit.to_file(output / "circuit.stim")
        (output / "metadata.json").write_text(
            json.dumps(compiled.export_metadata(), indent=2), encoding="utf-8"
        )
        (output / "terminal.json").write_text(
            json.dumps(
                {
                    "original_measurement_count": noisy_probe.original_measurement_count,
                    "measurement_indices": noisy_probe.measurement_indices,
                }
            ),
            encoding="utf-8",
        )
    return dict(
        shots=shots,
        patches=12,
        uses=len(compiled.block_uses),
        teleportations=len(compiled.relocation_history),
        raw_shape=list(raw.shape),
        noisy_sample_shape=list(noisy_samples.shape),
        detectors=len(view.detectors),
        terminal_stabilizers=4,
        ideal_failures=0,
        noisy_decoder="not evaluated; external decoder required",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=int, default=16)
    parser.add_argument("--p", type=float, default=0.001)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--noisy-resource", action="store_true")
    parser.add_argument("--depth", type=int, choices=(2, 3), default=2)
    parser.add_argument("--cycles", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                shots=args.shots,
                probability=args.p,
                output=args.output,
                ideal_resource=not args.noisy_resource,
                depth=args.depth,
                cycles=args.cycles,
            ),
            indent=2,
        )
    )
