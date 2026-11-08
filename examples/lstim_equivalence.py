"""Pair frozen LSTIM samples with independent Python programs and external decoding.

Run with .[dev]. This is a bounded demonstration, not a new language CLI or
decoder. The ordinary-memory and restricted Knill adapters are unchanged.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from logical_to_stim_converter import (
    BindPatch,
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    parse_logical_file,
)

try:
    from .knill_memory_offline_decoding import analyze_knill, prepare_compiled
    from .memory_offline_decoding import analyze_memory
except ImportError:
    from knill_memory_offline_decoding import analyze_knill, prepare_compiled
    from memory_offline_decoding import analyze_memory


def python_memory_reference(noise):
    """Direct reference for memory_d3.lstim, including two distinct SE barriers."""
    block = LogicalBlock.placed("P0", CodeSpec.rotated_surface(3), patch_index=0)
    return CircuitCompiler((block,), logical_to_block={}).compile((
        BindPatch("D", "P0"), LogicalInit("D", "Z", 3),
        SyndromeExtraction("D", 1), SyndromeExtraction("D", 1), LogicalMeasure("D", "Z"),
    ), noise_model=noise)


def python_knill_reference(noise):
    """Direct three-cycle reference; initial reservations are explicit directives."""
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed(f"P{i}", code, patch_index=i) for i in range(3)]
    return CircuitCompiler(blocks, logical_to_block={}).compile((
        BindPatch("D", "P0"), BindPatch("A0", "P1"), BindPatch("B0", "P2"),
        LogicalInit("D", "Z", 3),
        KnillEC("D", "A0", "B0", rounds=3, operation_id="cycle0"), SyndromeExtraction("D", 1),
        BindPatch("A1", "P0"), BindPatch("B1", "P1"),
        KnillEC("D", "A1", "B1", rounds=3, operation_id="cycle1"), SyndromeExtraction("D", 1),
        BindPatch("A2", "P2"), BindPatch("B2", "P0"),
        KnillEC("D", "A2", "B2", rounds=3, operation_id="cycle2"), SyndromeExtraction("D", 1),
        LogicalMeasure("D", "Z"),
    ), noise_model=noise)


def compare_sample(path, reference, *, noise, shots, seed):
    """Use one shared batch for offline comparisons; check a separate seeded sampler."""
    program = parse_logical_file(path)
    compiled = program.compile(noise_model=noise)
    assert compiled.ideal_circuit == reference.ideal_circuit
    assert compiled.noisy_circuit == reference.noisy_circuit
    dem = compiled.circuit.detector_error_model()
    assert dem == reference.circuit.detector_error_model()
    compiled.validate_metadata()
    reference.validate_metadata()
    view, reference_view = compiled.make_decoder_view(), reference.make_decoder_view()
    assert view.source_fingerprint == reference_view.source_fingerprint
    experiments = (prepare_compiled(compiled), prepare_compiled(reference)) if (
        compiled.bell_measurements
    ) else None
    raw = compiled.circuit.compile_sampler(seed=seed).sample(shots)
    np.testing.assert_array_equal(raw, reference.circuit.compile_sampler(seed=seed).sample(shots))
    before = raw.copy()
    if experiments is not None:
        a = analyze_knill(experiments[0], raw)
        b = analyze_knill(experiments[1], raw)
        for name in ("physical_events", "physical_observable_flips", "interpreted_measurements",
                     "final_x", "final_z", "logical_values", "failures"):
            np.testing.assert_array_equal(getattr(a, name), getattr(b, name))
        for x, y in zip(a.diagnostics, b.diagnostics, strict=True):
            assert x[0] == y[0]
            np.testing.assert_array_equal(x[1], y[1])
            np.testing.assert_array_equal(x[2].correction.bits, y[2].correction.bits)
        errors = {"restricted_knill": a.errors}
    else:
        a, b = analyze_memory(compiled, raw), analyze_memory(reference, raw)
        np.testing.assert_array_equal(a.detection_events, b.detection_events)
        np.testing.assert_array_equal(a.observable_flips, b.observable_flips)
        for x, y in zip(a.strategies, b.strategies, strict=True):
            assert x.strategy == y.strategy
            np.testing.assert_array_equal(x.predicted_flips, y.predicted_flips)
            np.testing.assert_array_equal(x.failures, y.failures)
        errors = {r.strategy: r.logical_errors for r in a.strategies}
    np.testing.assert_array_equal(raw, before)
    assert compiled.circuit.detector_error_model() == dem
    first_error = next((inst for inst in dem if inst.type == "error"), None)
    return dict(
        source=path.name, seed=seed, shots=shots, qubits=compiled.circuit.num_qubits,
        measurements=compiled.circuit.num_measurements, detectors=compiled.circuit.num_detectors,
        observables=compiled.circuit.num_observables, dem_errors=dem.num_errors,
        first_dem_error=None if first_error is None else dict(
            probabilities=first_error.args_copy(),
            targets=[str(t) for t in first_error.targets_copy()],
        ),
        uses=[dict(patch=u.use_id.block_id, epoch=u.use_id.epoch) for u in compiled.block_uses],
        source_fingerprint=view.source_fingerprint, exact_physical_and_decode_equality=True,
        errors=errors, ler={name: count / shots for name, count in errors.items()},
    )


def main():
    """Print bounded paired-source/DEM/decode evidence for both shipped source files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=int, default=32)
    parser.add_argument("--p", type=float, default=.001)
    parser.add_argument("--seed", type=int, default=826)
    args = parser.parse_args()
    if args.shots < 1 or not 0 <= args.seed < 2**64:
        parser.error("Use positive shots and a seed in [0, 2**64)")
    noise = NoiseModel.uniform_depolarizing(args.p)
    examples = Path(__file__).resolve().parent / "lstim"
    for name, factory in (("memory_d3.lstim", python_memory_reference),
                          ("three_patch_knill_d3.lstim", python_knill_reference)):
        report = compare_sample(examples / name, factory(noise), noise=noise,
                                shots=args.shots, seed=args.seed)
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
