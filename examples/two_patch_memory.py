"""Two synchronous memory patches; no parser, postselection, or external decoder.

Run after installing the package: python examples/two_patch_memory.py
"""

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
)


def main() -> None:
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed(f"patch{i}", code, patch_index=i) for i in range(2)]
    compiler = CircuitCompiler(blocks, logical_to_block={"data0": "patch0", "data1": "patch1"})
    compiled = compiler.compile(
        [
            [LogicalInit("data0", basis="Z", rounds=1), LogicalInit("data1", basis="X", rounds=1)],
            SyndromeExtraction(("data0", "data1"), rounds=3),
            [LogicalMeasure("data0", basis="Z"), LogicalMeasure("data1", basis="X")],
        ],
        noise_model=NoiseModel.uniform_depolarizing(0.001),
    )

    ideal_dets, ideal_obs = compiled.ideal_circuit.compile_detector_sampler(seed=7).sample(
        shots=100, separate_observables=True
    )
    assert not ideal_dets.any()
    assert not ideal_obs.any()  # Both prepared +1 logical eigenstates read back as zero bits.
    dem = compiled.circuit.detector_error_model()
    noisy_dets, noisy_obs = compiled.circuit.compile_detector_sampler(seed=8).sample(
        shots=100, separate_observables=True
    )
    print(f"Physical qubits: {len(compiled.physical_qubit_map)}")
    print(f"Detectors: {len(compiled.detectors)}; observables: {len(compiled.observables)}")
    print(f"Physical layers: {len(compiled.time_layers)}")
    print(f"DEM: {dem.num_detectors} detectors, {dem.num_observables} observables")
    print(f"Sample shapes: {noisy_dets.shape}, {noisy_obs.shape}")
    for observable in compiled.observables:
        print(
            f"{observable.logical_id}: observable {observable.index}, "
            f"raw measurement indices {observable.measurement_indices}"
        )
    # compiled.ideal_circuit / compiled.noisy_circuit are available for optional export.
    # Detector-event and observable samples alone are not decoded logical error rates.


if __name__ == "__main__":
    main()
