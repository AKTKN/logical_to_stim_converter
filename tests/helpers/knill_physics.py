"""Independent physical tableau probes and explicit-correction reference runs."""

import numpy as np
import stim

from logical_to_stim_converter import CircuitCompiler, CodeSpec, LogicalBlock


def make_compiler(d=3, names="DAB"):
    blocks = [LogicalBlock.placed("physical_" + q, CodeSpec.rotated_surface(d), patch_index=i)
              for i, q in enumerate(names)]
    return CircuitCompiler(blocks, logical_to_block={q: b.block_id
        for q, b in zip(names, blocks, strict=True)})


def pauli(compiled, logical, basis, *, block_id=None, orientation=None):
    bid = block_id or compiled.logical_to_block[logical]
    block = next(b for b in compiled._compiler.blocks if b.block_id == bid)
    p = compiled._compiler.backend.logical_pauli(
        block, logical, basis,
        compiled.orientations[logical] if orientation is None else orientation)
    at = {block.position(q): compiled.physical_qubit_map[(bid, q)] for q in block.layout.data_ids}
    result = stim.PauliString(compiled.ideal_circuit.num_qubits)
    for q, axis in p.items():
        result[at[q]] = axis
    return result


def simulate(compiled, seeds):
    simulators, raw = [], []
    for seed in seeds:
        sim = stim.TableauSimulator(seed=seed)
        sim.set_num_qubits(compiled.ideal_circuit.num_qubits)
        sim.do(compiled.ideal_circuit)
        simulators.append(sim)
        raw.append(sim.current_measurement_record())
    return np.asarray(raw, dtype=bool), simulators


def apply_frame(sim, compiled, frame):
    sim.x(*(compiled.physical_qubit_map[(frame.block_id, q)] for q in frame.x_support))
    sim.z(*(compiled.physical_qubit_map[(frame.block_id, q)] for q in frame.z_support))


def corrected_expectation(sim, compiled, operator, frames):
    parity = 0
    for frame in frames:
        for support, anti_axes in ((frame.x_support, (2, 3)), (frame.z_support, (1, 2))):
            parity ^= sum(operator[compiled.physical_qubit_map[(frame.block_id, q)]]
                          in anti_axes for q in support) % 2
    return sim.peek_observable_expectation(operator) * (-1 if parity else 1)


def explicit_reference(compiled, interpreted, corrections):
    """Actually execute corrections on a separate physical simulator.

    Force the evaluator's classical branch. An incorrect propagation makes this
    branch physically impossible or produces an incorrect final expectation.
    The reference uses Pauli execution and projective quantum measurement; it
    does not propagate binary frame vectors.
    """
    sim = stim.TableauSimulator()
    sim.set_num_qubits(compiled.ideal_circuit.num_qubits)
    blocks = compiled._compiler.blocks
    at = {b.position(q): compiled.physical_qubit_map[(b.block_id, q)]
          for b in blocks for q in b.layout.qubit_ids}
    cursor = 0
    bells = {b.composite_id: b for b in compiled.bell_measurements}
    records = {m.key: m.index for m in compiled.measurements}
    for kind, value in compiled._evaluation_steps:
        if kind == "physical":
            local = {i: at[q] for q, i in value.q2i.items()}
            for inst in value.circuit:
                if inst.name == "TICK":
                    continue
                targets = [local[t.value] for t in inst.targets_copy()]
                if inst.name in ("M", "MX"):
                    for t in targets:
                        getattr(sim, "postselect_x" if inst.name == "MX" else "postselect_z")(
                            t, desired_value=bool(interpreted[cursor]))
                        measurement = stim.Circuit()
                        measurement.append(inst.name, [t])
                        sim.do(measurement)
                        cursor += 1
                else:
                    gate = stim.Circuit()
                    gate.append(inst.name, targets)
                    sim.do(gate)
        elif kind == "preparation":
            apply_frame(sim, compiled, corrections[value][0])
        elif kind == "virtual":
            for q, axis in value.items():
                getattr(sim, axis.lower())(at[q])
        elif kind == "teleport":
            bell = bells[value["composite_id"]]
            measured = np.asarray(sim.current_measurement_record())
            mx = bell.x_readout.logical_parity.evaluate(measured, records)
            mz = bell.z_readout.logical_parity.evaluate(measured, records)
            if mz:
                sim.do_pauli_string(pauli(compiled, bell.logical_id, "X",
                    block_id=bell.output_block_id, orientation=bell.output_orientation))
            if mx:
                sim.do_pauli_string(pauli(compiled, bell.logical_id, "Z",
                    block_id=bell.output_block_id, orientation=bell.output_orientation))
    return sim
