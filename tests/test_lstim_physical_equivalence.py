"""Independent Python references certify the exact physical experiment, not Stim text."""

import numpy as np
import pytest

from logical_to_stim_converter import (
    BellStatePrep,
    BindPatch,
    BlockUseId,
    DEMOptions,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    NoiseParameters,
    SyndromeExtraction,
    TransversalCNOT,
    TransversalH,
    observable_local_views,
)
from tests.helpers.lstim_equivalence import (
    assert_experiment_equal,
    compile_pair,
    declarations,
)
from tests.helpers.lstim_programs import knill_operations, knill_source
from tests.test_epoch_views_noise import assert_exact_reuse_noise


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("long_init", [False, True])
@pytest.mark.parametrize("mode", [None, "physical", "frame"])
@pytest.mark.parametrize("noisy", [False, True])
def test_single_patch_memory(distance, basis, long_init, mode, noisy):
    rounds = distance if long_init else 1
    axis = "Z" if basis == "X" else "X"
    source = declarations(distance) + f"BIND D P0\nINIT_{basis}[prepare]({rounds}) D\n"
    operations = [BindPatch("D", "P0"), LogicalInit("D", basis, rounds, operation_id="prepare")]
    if mode is not None:
        source += f"{axis}[flip] D mode={mode}\n"
        operations.append(LogicalPauli("D", axis, mode=mode, operation_id="flip"))
    source += f"SE[extra]({distance}) D\nREPEAT 2 {{\n    SE(1) D\n}}\nM{basis}[output] D\n"
    operations.extend((
        SyndromeExtraction("D", distance, operation_id="extra"),
        SyndromeExtraction("D", 1), SyndromeExtraction("D", 1),
        LogicalMeasure("D", basis, operation_id="output"),
    ))
    noise = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005)) if noisy else None
    actual, reference = compile_pair(source, operations, distance=distance, noise=noise)
    raw = assert_experiment_equal(actual, reference)
    assert actual.observables[0].expected_value == (mode is not None)
    # Decompose only this exactly graphlike memory model; never discard hyperedges.
    options = DEMOptions(decompose_errors=True)
    a = actual.make_decoder_view(dem_options=options)
    b = reference.make_decoder_view(dem_options=options)
    assert a.detector_error_model == b.detector_error_model
    np.testing.assert_array_equal(a.events_from_raw(raw), b.events_from_raw(raw))
    assert len([f for f in actual.fragments if f.operation_type == "SyndromeExtraction"]) == 3


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("noisy", [False, True])
def test_parallel_unequal_rounds_ticks_and_exact_idle_channels(distance, noisy):
    source = declarations(distance, 2) + """BIND D P0
BIND S P1
PARALLEL {
    INIT_Z(1) D
    INIT_X(1) S
}
PARALLEL {
    SE(3) D
    SE(1) S
}
PARALLEL {
    H D
    H S
}
PARALLEL {
    MX D
    MZ S
}
"""
    operations = (
        BindPatch("D", "P0"), BindPatch("S", "P1"),
        (LogicalInit("D", "Z", 1), LogicalInit("S", "X", 1)),
        (SyndromeExtraction("D", 3), SyndromeExtraction("S", 1)),
        (TransversalH("D"), TransversalH("S")),
        (LogicalMeasure("D", "X"), LogicalMeasure("S", "Z")),
    )
    model = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005))
    actual, reference = compile_pair(
        source, operations, distance=distance, count=2, noise=model if noisy else None,
    )
    assert_experiment_equal(actual, reference)
    assert len(actual.observables) == 2
    # Derive every channel from actual physical gates/resets, including an idle spectator.
    if noisy:
        assert_exact_reuse_noise(actual, model)
        assert any(i.name == "DEPOLARIZE1" and i.gate_args_copy() == [.005]
                   for i in actual.circuit)
    assert any(len(layer.operation_by_block) == 1 and len(layer.active_use_ids) == 2
               for layer in actual.time_layers)


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("rotated", [False, True])
def test_ordered_cnot_h_orientation_and_signed_frame(distance, rotated):
    source = declarations(distance, 2) + """BIND D P0
BIND A P1
INIT_X(1) D
INIT_Z(1) A
"""
    operations = [
        BindPatch("D", "P0"), BindPatch("A", "P1"),
        LogicalInit("D", "X", 1), LogicalInit("A", "Z", 1),
    ]
    if rotated:
        source += "PARALLEL {\n    H D\n    H A\n}\n"
        operations.append((TransversalH("D"), TransversalH("A")))
    source += "CX[forward] D A\nZ[sign] D mode=frame\nCX[uncompute] D A\n"
    operations.extend((TransversalCNOT("D", "A", operation_id="forward"),
                       LogicalPauli("D", "Z", mode="frame", operation_id="sign"),
                       TransversalCNOT("D", "A", operation_id="uncompute")))
    a_basis, b_basis = ("Z", "X") if rotated else ("X", "Z")
    source += f"M{a_basis} D\nM{b_basis} A\n"
    operations.extend((LogicalMeasure("D", a_basis), LogicalMeasure("A", b_basis)))
    actual, reference = compile_pair(
        source, operations, distance=distance, count=2,
        noise=NoiseModel.uniform_depolarizing(.001),
    )
    assert_experiment_equal(actual, reference)
    assert actual.orientations == {"D": int(rotated), "A": int(rotated)}


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("explicit_rounds", [False, True])
def test_bell_resource_reverse_patch_order_and_no_double_noise(distance, explicit_rounds):
    rounds = f"({distance})" if explicit_rounds else ""
    source = declarations(distance, 2) + f"""BIND D P0
BIND A P1
BELL_PREP[resource]{rounds} A D
CX[uncompute] A D
H A
X D mode=frame
MZ D
MZ A
"""
    operations = (
        BindPatch("D", "P0"), BindPatch("A", "P1"),
        BellStatePrep("A", "D", distance if explicit_rounds else None, operation_id="resource"),
        TransversalCNOT("A", "D", operation_id="uncompute"), TransversalH("A"),
        LogicalPauli("D", "X", mode="frame"), LogicalMeasure("D", "Z"), LogicalMeasure("A", "Z"),
    )
    noise = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005))
    actual, reference = compile_pair(source, operations, distance=distance, count=2, noise=noise)
    assert_experiment_equal(actual, reference)
    assert_exact_reuse_noise(actual, noise)
    assert any(c.composite_id == "resource" for c in actual.composites)


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
@pytest.mark.parametrize("cycles", [1, 3])
@pytest.mark.parametrize("post_rounds", [0, 1])
def test_knill_fixed_width_epoch_schedule_and_exact_noise(
    distance, basis, bit, cycles, post_rounds,
):
    parameters = dict(
        distance=distance, basis=basis, bit=bit, cycles=cycles, post_rounds=post_rounds,
    )
    noise = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005))
    actual, reference = compile_pair(
        knill_source(**parameters), knill_operations(**parameters),
        distance=distance, count=3, noise=noise,
    )
    assert_experiment_equal(actual, reference)
    assert_exact_reuse_noise(actual, noise)
    assert actual.circuit.num_qubits == 3 * (2 * distance * distance - 1)
    assert len(actual.block_uses) == 1 + 2 * cycles
    assert len(actual.binding_history) == 3 + 2 * (cycles - 1)
    assert len(set(m.key for m in actual.measurements)) == actual.circuit.num_measurements
    expected = [BlockUseId("P2", 0)] if cycles == 1 else [
        BlockUseId("P2", 0), BlockUseId("P1", 1), BlockUseId("P0", 2),
    ]
    assert [r.output_use_id for r in actual.relocation_history] == expected
    assert actual.observables[0].block_use_id == expected[-1]
    assert actual.observables[0].expected_value == bit


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("spectator", [False, True])
def test_reuse_independent_epochs_with_active_spectator(distance, spectator):
    source = declarations(distance, 2 if spectator else 1)
    operations = []
    if spectator:
        source += f"BIND S P1\nINIT_Z({distance}) S\n"
        operations.extend((BindPatch("S", "P1"), LogicalInit("S", "Z", distance)))
    source += f"""BIND first P0
INIT_Z({distance}) first
X first mode=frame
MZ first
BIND second P0
INIT_X({distance}) second
MX second
"""
    operations.extend((
        BindPatch("first", "P0"), LogicalInit("first", "Z", distance),
        LogicalPauli("first", "X", mode="frame"), LogicalMeasure("first", "Z"),
        BindPatch("second", "P0"), LogicalInit("second", "X", distance),
        LogicalMeasure("second", "X"),
    ))
    if spectator:
        source += "MZ S\n"
        operations.append(LogicalMeasure("S", "Z"))
    model = NoiseModel(NoiseParameters(.001, .002, .003, .004, .005))
    actual, reference = compile_pair(
        source, operations, distance=distance, count=2 if spectator else 1, noise=model,
    )
    assert_experiment_equal(actual, reference)
    assert_exact_reuse_noise(actual, model)
    assert {m.key.block_use_id for m in actual.measurements if m.key.block_id == "P0"} == {
        BlockUseId("P0", 0), BlockUseId("P0", 1),
    }
    for observable, view in zip(actual.observables, observable_local_views(actual), strict=True):
        assert all(d.source_use_ids == (observable.block_use_id,) for d in view.detectors)
    # A correction at the retired preparation changes old readout bits only.
    from logical_to_stim_converter.decoding import CorrectionBatch

    plan = actual.make_frame_plan()
    raw = actual.ideal_circuit.compile_sampler(seed=811).sample(7)
    state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
    baseline = state.interpreted_measurements.copy()
    old = next(p for p in actual.preparations if p.logical_id == "first")
    boundary = plan.boundary_by_id[old.module_id]
    bits = np.zeros((len(raw), len(boundary.input_ids)), dtype=bool)
    bits[:, 0] = True
    state.apply(CorrectionBatch(plan.source_fingerprint, old.module_id, bits, old.block_use_id))
    new_ids = [m.index for m in actual.measurements if m.key.block_use_id == BlockUseId("P0", 1)]
    np.testing.assert_array_equal(state.interpreted_measurements[:, new_ids], baseline[:, new_ids])
    assert not state.final_x[:, [i for (b, _), i in actual.physical_qubit_map.items()
                                if b == "P0"]].any()
    assert not np.array_equal(state.interpreted_measurements, baseline)


@pytest.mark.parametrize("distance", [3, 5])
def test_open_knill_outputs_have_no_fake_terminal_measurements(distance):
    params = dict(distance=distance, open_outputs=True)
    actual, reference = compile_pair(
        knill_source(**params), knill_operations(**params), distance=distance, count=3,
        noise=NoiseModel.uniform_depolarizing(.001), open_outputs=True,
    )
    assert_experiment_equal(actual, reference)
    assert actual.open_logical_outputs == {"D": "P0"}
    assert len(actual.readouts) == 6 and not actual.observables
    assert actual.block_uses[-1].use_id == BlockUseId("P0", 2)
    assert actual.block_uses[-1].terminal_module_id is None
    closed = actual.append((LogicalMeasure("D", "Z"),))
    assert closed.circuit.num_measurements - actual.circuit.num_measurements == distance**2
