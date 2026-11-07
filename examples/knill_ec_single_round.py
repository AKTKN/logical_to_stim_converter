"""Generate ideal/noisy Knill circuits without importing a decoder."""

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    TransversalH,
)


def main():
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed("physical_" + q, code, patch_index=i)
              for i, q in enumerate("DAB")]
    compiler = CircuitCompiler(blocks, logical_to_block={q: b.block_id
        for q, b in zip("DAB", blocks, strict=True)})
    noise = NoiseModel.uniform_depolarizing(.001)
    opened = compiler.compile([LogicalInit("D", "X", 1), KnillEC("D", "A", "B")],
                              allow_open_outputs=True, noise_model=noise)
    print("Active logical locations:", dict(opened.open_logical_outputs))
    print("Physical block states:", {b: s.value for b, s in opened.block_status.items()})
    print("Physical site -> Stim index:", dict(opened.physical_qubit_map))
    print("Preparation stages:", [(p.block_id, p.stage_id, p.rounds)
                                   for p in opened.preparations])
    print("Detector regions:", sorted({str(d.stage_id) for d in opened.detectors}))
    print("Verified cross-stage relations retained as metadata:", len(opened.suppressed_detectors))
    bell, = opened.bell_measurements
    records = {m.key: m.index for m in opened.measurements}
    print("Bell X raw records:", [records[k] for k in bell.raw_x_records])
    print("Bell Z raw records:", [records[k] for k in bell.raw_z_records])
    print("Symbolic teleportation byproduct:", bell.raw_byproduct)
    print("Output physical correction resolved:", bell.physical_output_frame.resolved)
    print("Relocation history:", opened.relocation_history)
    assert not any(i.name == "MPP" for i in opened.ideal_circuit)
    closed = opened.append([SyndromeExtraction("D", 2), TransversalH("D"),
                            LogicalMeasure("D", "Z")])
    for name, circuit in (("ideal", closed.ideal_circuit), ("noisy", closed.noisy_circuit)):
        dem = circuit.detector_error_model()
        print(name, "qubits", circuit.num_qubits, "measurements", circuit.num_measurements,
              "detectors", circuit.num_detectors, "observables", circuit.num_observables,
              "DEM errors", dem.num_errors)
    assert not closed.ideal_circuit.compile_detector_sampler(seed=9).sample(100).any()
    print("Noiseless physical-frame recovery is verified by tests/helpers/preparation_matching.py.")
    print("Preparation corrections remain unresolved here; no decoded recovery or LER is claimed.")


if __name__ == "__main__":
    main()
