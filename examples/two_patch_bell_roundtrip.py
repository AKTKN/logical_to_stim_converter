"""Encoded Bell preparation, synchronous SE, and inverse Bell transformation.

Run: python examples/two_patch_bell_roundtrip.py
No decoder, dedicated Bell class, logical parser, or error-rate benchmark is used.
"""

import numpy as np
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
)


def main():
    d, rounds = 3, 3
    code = CodeSpec.rotated_surface(d)
    blocks = [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate(("A", "B"))]
    result = CircuitCompiler(blocks).compile(
        [
            LogicalInit(("A", "B"), basis="Z", rounds=1),
            TransversalH("A"),
            TransversalCNOT(control="A", target="B"),
            SyndromeExtraction(("A", "B"), rounds=rounds),
            TransversalCNOT(control="A", target="B"),
            TransversalH("A"),
            LogicalMeasure(("A", "B"), basis="Z"),
        ],
        noise_model=NoiseModel.uniform_depolarizing(0.001),
    )

    # Independent tableau check of the actual physical intermediate state.
    simulator = stim.TableauSimulator(seed=17)
    first_cnot = next(f for f in result.fragments if f.operation_type == "TransversalCNOT")
    for instruction in result.ideal_circuit:
        simulator.do(instruction)
        if instruction.tag == first_cnot.module_id:
            break
    for axis in "XZ":
        # A is in code frame 1 (clockwise template), while B is in frame 0.
        columns_a = range(d) if axis == "X" else range(d - 1, d * d, d)
        columns_b = range(0, d * d, d) if axis == "X" else range(d)
        a = stim.PauliString(result.ideal_circuit.num_qubits)
        b = stim.PauliString(result.ideal_circuit.num_qubits)
        for column in columns_a:
            a[result.physical_qubit_map[("A", f"D{column + 1}")]] = axis
        for column in columns_b:
            b[result.physical_qubit_map[("B", f"D{column + 1}")]] = axis
        assert simulator.peek_observable_expectation(a * b) == 1
        assert simulator.peek_observable_expectation(a) == 0
        assert simulator.peek_observable_expectation(b) == 0
        print(f"Intermediate logical {axis}{axis}: +1; individual {axis}: nondeterministic")

    raw = result.ideal_circuit.compile_sampler(seed=7).sample(100)
    # Final frames return to orientation 0: Z is the original western data column.
    for block in ("A", "B"):
        indices = [
            m.index
            for m in result.measurements
            if m.key.block_id == block
            and m.key.kind == "readout"
            and m.key.local_id in {f"D{i + 1}" for i in range(d)}
        ]
        assert not np.bitwise_xor.reduce(raw[:, indices], axis=1).any()
    assert not result.interpreted_measurements(raw).any()
    dem = result.circuit.detector_error_model()
    sampler_a = result.circuit.compile_detector_sampler(seed=12)
    sampler_b = result.circuit.compile_detector_sampler(seed=12)
    assert np.array_equal(sampler_a.sample(100), sampler_b.sample(100))
    cross = sum(len(d.supporting_block_ids) > 1 for d in result.detectors)
    print(
        f"{len(result.physical_qubit_map)} qubits, {len(result.detectors)} detectors, "
        f"{len(result.observables)} observables, {len(result.time_layers)} physical layers"
    )
    print(f"{cross} detectors contain records from both blocks")
    print("Ideal raw logical Z outcomes: (0, 0)")
    print(f"Noisy DEM: {dem.num_errors} mechanisms; seeded samples reproducible")


if __name__ == "__main__":
    main()
