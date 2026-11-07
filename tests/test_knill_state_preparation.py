"""Preparation-sector physics, actual records, and test-only MWPM corrections."""

from dataclasses import replace

import numpy as np
import pymatching
import pytest
import stim

from logical_to_stim_converter import LogicalInit
from tests.helpers.knill_physics import apply_frame, make_compiler, pauli, simulate
from tests.helpers.preparation_matching import preparation_corrections


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("seed", [10, 100])
def test_noiseless_preparation_sectors(d, basis, seed):
    compiler = make_compiler(d, "D")
    result = compiler.compile([LogicalInit("D", basis, d)], allow_open_outputs=True)
    prep, = result.preparations
    code = compiler.blocks[0].code
    assert np.array_equal(prep.check_matrix("X"), code.H_X)
    assert np.array_equal(prep.check_matrix("Z"), code.H_Z)
    assert prep.rounds == d
    assert len(result.measurements) == d * (d*d - 1)
    assert len(prep.gauge_measurements) == (d*d - 1)//2
    assert not prep.unresolved_frame.resolved
    assert len(result.detectors) == (d*d - 1)//2 + (d-1)*(d*d - 1)
    for detector in result.detectors:
        keys = detector.measurement_keys
        if len(keys) == 1:
            m = result.measurements[detector.measurement_indices[0]]
            assert m.basis == basis and keys[0].round_index == 0
        else:
            assert len(keys) == 2
            assert keys[0].local_id == keys[1].local_id
            assert keys[1].round_index == keys[0].round_index + 1
    assert not any(i.name in ("X", "Y", "Z", "MPP", "M" if basis == "X" else "MX")
                   and any(t.value in {result.physical_qubit_map[(prep.block_id, q)]
                                       for q in prep.data_ids} for t in i.targets_copy())
                   for i in result.ideal_circuit)
    raw, simulators = simulate(result, range(seed, seed+12))
    records = {m.key: m.index for m in result.measurements}
    assert raw[:, [records[k] for k in prep.gauge_measurements]].any()
    corrections = preparation_corrections(result, raw)
    for check in prep.checks:
        history = raw[:, [records[k] for k in check.measurements]]
        assert (history == history[:, :1]).all()
    for shot, sim in enumerate(simulators):
        frame = corrections[prep.module_id][shot]
        corrected = sim.copy()
        apply_frame(corrected, result, frame)
        for check in prep.checks:
            p = stim.PauliString(result.ideal_circuit.num_qubits)
            for q in check.support:
                p[result.physical_qubit_map[(prep.block_id, q)]] = check.basis
            assert corrected.peek_observable_expectation(p) == 1
        assert corrected.peek_observable_expectation(pauli(result, "D", basis)) == 1
    evaluated = result.evaluate_frames(raw, corrections)
    assert "D" in evaluated.final_frames


@pytest.mark.parametrize("corruption", ["missing", "zero", "vector", "mapping", "orientation",
                                         "check_order", "swapped_matrices"])
def test_incorrect_preparation_corrections_fail(corruption):
    result = make_compiler(3, "D").compile([LogicalInit("D", "Z", 3)],
                                         allow_open_outputs=True)
    raw = result.ideal_circuit.compile_sampler(seed=21).sample(64)
    corrections = preparation_corrections(result, raw)
    prep, = result.preparations
    frames = corrections[prep.module_id]
    if corruption == "missing":
        corrections = {}
    elif corruption == "zero":
        corrections[prep.module_id] = tuple(prep.resolve(np.zeros(9), np.zeros(9)) for _ in raw)
    elif corruption == "vector":
        corrections[prep.module_id] = tuple(replace(f, z_support=tuple(
            sorted(set(f.z_support) ^ {"D1"}))) for f in frames)
    elif corruption == "mapping":
        corrections[prep.module_id] = tuple(replace(f, z_support=tuple(
            f"D{10-int(q[1:])}" for q in f.z_support)) for f in frames)
    elif corruption == "orientation":
        corrections[prep.module_id] = tuple(replace(f, orientation=1) for f in frames)
    else:
        keys = {m.key: m.index for m in result.measurements}
        sx = raw[:, [keys[c.measurements[-1]] for c in prep.checks if c.basis == "X"]]
        matrix = prep.check_matrix("Z" if corruption == "swapped_matrices" else "X")
        bad = pymatching.Matching.from_check_matrix(matrix).decode_batch(
            sx[:, ::-1] if corruption == "check_order" else sx)
        corrections[prep.module_id] = tuple(prep.resolve(np.zeros(9), z) for z in bad)
    with pytest.raises(ValueError):
        result.evaluate_frames(raw, corrections)
