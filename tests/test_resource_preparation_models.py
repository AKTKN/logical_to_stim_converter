"""Independent Stim fault actions, temporal cuts and source-bound M9 views."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    BellStatePrep,
    DetectorSelector,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseParameters,
    SyndromeExtraction,
    TransversalCNOT,
)
from logical_to_stim_converter.decoding import (
    DecoderViewError,
    SourceMismatchError,
    UnsupportedProjectionError,
    make_conditional_readout_model,
    make_stage_requests,
)
from logical_to_stim_converter.decoding.stages import module_end
from logical_to_stim_converter.decoding.views import source_fingerprint
from tests.helpers.decoder_view_physics import assert_marginal_equivalent, physical_instructions
from tests.helpers.knill_physics import make_compiler
from tests.test_bell_state_preparation import physical_circuit
from tests.test_resource_preparation_noise import special


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_every_post_se_xyz_atom_against_independent_ideal_primitives(distance, basis):
    compiler = make_compiler(distance)
    c = compiler.compile([LogicalInit("D", basis, 1), KnillEC("D", "A", "B", rounds=1),
                          LogicalMeasure("D", basis)], noise_model=special(.12345678912345678))
    # This reference authors only physical primitives; it has no resource policy,
    # composite expansion or conditional mapping and measures B explicitly.
    reference = compiler.compile([
        LogicalInit("D", basis, 1),
        [LogicalInit("A", "X", 1), LogicalInit("B", "Z", 1)],
        TransversalCNOT("A", "B"), TransversalCNOT("D", "A"),
        [LogicalMeasure("D", "X", mode="random"), LogicalMeasure("A", "Z", mode="random")],
        LogicalMeasure("B", basis, mode="random"),
    ])
    assert physical_circuit(reference.ideal_circuit) == physical_circuit(c.ideal_circuit)
    bell = c.bell_measurements[0]
    model = make_conditional_readout_model(c, bell)
    assert "before post-SE depolarizing channels" in model.boundary_convention
    bs = c.resource_preparation_boundaries
    assert model.start_instruction == min(b.channel_instruction for b in bs)
    assert len(model.faults) == 6 * distance**2
    assert model.end_instruction == module_end(c.circuit, bell.z_readout.module_id)
    atoms = [(compiler_block.block_id, q, axis)
             for compiler_block in compiler.blocks[1:]
             for q in compiler_block.layout.data_ids for axis in "XYZ"]
    locations = [(c.physical_qubit_map[block, q], axis) for block, q, axis in atoms]
    rows = []
    for q, axis in locations:
        matches = [i for i, f in enumerate(model.faults) if f.paulis == ((q, axis),)]
        assert len(matches) == 1
        rows.append(matches[0])
    groups = {}
    for f in model.faults:
        groups.setdefault(f.exclusive_group, []).append(f)
    assert len(groups) == 2 * distance**2
    for group in groups.values():
        assert {f.paulis[0][1] for f in group} == set("XYZ")
        assert len(group) == 3
        assert sum(f.probability for f in group) == pytest.approx(.12345678912345678)
    oracle = stim.FlipSimulator(batch_size=len(atoms), num_qubits=c.circuit.num_qubits,
                                disable_stabilizer_randomization=True)
    rc = reference.ideal_circuit
    start = next(i for i, inst in enumerate(rc) if inst.tag == "module0003")
    end = module_end(rc, "module0006")
    oracle.do(rc[:start])
    for axis in "XYZ":
        mask = np.zeros((c.circuit.num_qubits, len(atoms)), dtype=bool)
        for row, (q, a) in enumerate(locations):
            mask[q, row] = a == axis
        oracle.broadcast_pauli_errors(pauli=axis, mask=mask)
    oracle.do(rc[start:end])
    xs, zs, flips, _, _ = oracle.to_numpy(
        transpose=True, output_xs=True, output_zs=True, output_measure_flips=True)
    output = [c.physical_qubit_map[bell.output_block_id, q] for q in model.output_data_ids]
    raw = flips[:, model.readout_record_ids]
    np.testing.assert_array_equal(model.raw_flip_map.incidence_matrix.toarray()[rows], raw)
    np.testing.assert_array_equal(model.output_x_map.incidence_matrix.toarray()[rows],
                                  xs[:, output])
    np.testing.assert_array_equal(model.output_z_map.incidence_matrix.toarray()[rows],
                                  zs[:, output])
    split = len(bell.x_readout.records)
    for readout, measured, incidence in (
        (bell.x_readout, raw[:, :split], model.x_syndrome_map),
        (bell.z_readout, raw[:, split:], model.z_syndrome_map),
    ):
        np.testing.assert_array_equal(incidence.incidence_matrix.toarray()[rows],
                                      measured.astype(np.uint8) @
                                      readout.check_matrix(readout.basis).T % 2)
    logical = np.column_stack([
        np.bitwise_xor.reduce(flips[:, [c.measurement_index_by_key[k]
                                       for k in r.logical_parity.terms]], axis=1)
        for r in (bell.x_readout, bell.z_readout)
    ])
    np.testing.assert_array_equal(model.logical_flip_map.incidence_matrix.toarray()[rows], logical)
    assert np.any(raw.any(axis=1) & (xs[:, output].any(axis=1) | zs[:, output].any(axis=1)))
    oracle.do(rc[end:])
    flips = oracle.get_measurement_flips().T
    expected = np.column_stack([
        np.bitwise_xor.reduce(flips[:, d.measurement_indices], axis=1)
        for d in (*c.detectors, *c.observables)
    ])
    # Each deterministic fault is also executed in the canonical ideal circuit,
    # independently of both the conditional model and the batch propagation.
    cut = bs[0].ideal_boundary_instruction
    for row, (q, axis) in enumerate(locations):
        fault = c.ideal_circuit[:cut]
        fault.append(axis + "_ERROR", [q], 1)
        fault += c.ideal_circuit[cut:]
        actual = fault.compile_detector_sampler(seed=17).sample(1, append_observables=True)[0]
        np.testing.assert_array_equal(actual, expected[row])
    assert expected.any()  # Added errors produce observable physical effects.


@pytest.mark.parametrize("p", [0, .012345678912345678])
def test_preparation_probes_exclude_channels_and_views_preserve_exact_physics(p):
    c = make_compiler().compile([
        LogicalInit("D", "Z", 1), KnillEC("D", "A", "B", rounds=1), LogicalMeasure("D", "Z")
    ], noise_model=special(p))
    requests = make_stage_requests(c)
    for b in c.resource_preparation_boundaries:
        request = next(r for r in requests.boundaries if r.module_id == b.preparation_module_id)
        assert not any(i.tag.startswith("resource_post_se:") for i in request.model_circuit)
        assert not any(i.type == "error" for i in request.detector_error_model)
        assert request.model_circuit.num_measurements == (
            c.circuit[:module_end(c.circuit, b.preparation_module_id)].num_measurements
            + len(request.target_ids))
    model = make_conditional_readout_model(c, c.bell_measurements[0])
    assert len(model.faults) == (54 if p else 0)
    if not p:
        assert c.circuit[model.start_instruction].name == "CX"
    for b in c.resource_preparation_boundaries:
        view = c.make_decoder_view(detector_selector=DetectorSelector(use_ids=(b.block_use_id,)))
        assert physical_instructions(view.circuit) == physical_instructions(c.circuit)
        assert_marginal_equivalent(c.circuit.detector_error_model(), view)
        if p:
            channel = next(i for i in view.circuit if i.tag == b.channel_tag)
            assert channel.gate_args_copy() == [p]
    other = make_compiler().compile([
        LogicalInit("D", "Z", 1), KnillEC("D", "A", "B", rounds=1), LogicalMeasure("D", "Z")
    ], noise_model=special(p + .001))
    with pytest.raises(SourceMismatchError):
        other.make_decoder_view(expected_source_fingerprint=source_fingerprint(c))
    with pytest.raises(SourceMismatchError):
        c.make_decoder_view().assert_source(other)
    assert c.make_frame_plan().source_fingerprint == model.source_fingerprint


@pytest.mark.parametrize("reverse", [False, True])
def test_explicit_resources_delayed_consumption_includes_all_real_waiting_faults(reverse):
    resources = ("B", "A") if reverse else ("A", "B")
    c = make_compiler().compile([
        LogicalInit("D", "Z", 1), BellStatePrep(*resources, 1),
        LogicalPauli("D", "X", mode="physical"),  # Resources acquire waiting faults.
        KnillEC("D", "A", "B", prepare_resource=False), LogicalMeasure("D", "Z"),
    ], noise_model=special(.017, default=NoiseParameters(.001, .002, .003, .004, .005)))
    model = make_conditional_readout_model(c, c.bell_measurements[0])
    assert model.start_instruction == min(b.channel_instruction
                                          for b in c.resource_preparation_boundaries)
    from tests.test_patch_reuse_knill_e2e import assert_physical_conditional_atoms

    assert_physical_conditional_atoms(c, model)
    tags = {b.channel_tag for b in c.resource_preparation_boundaries}
    assert sum(c.circuit[f.instruction_index].tag in tags for f in model.faults) == 54
    waiting = next(i for i, inst in enumerate(c.circuit) if inst.name == "X")
    assert any(f.instruction_index == waiting + 1 for f in model.faults)


def test_delayed_operand_se_requires_an_intermediate_hypothesis_and_fails_explicitly():
    c = make_compiler().compile([
        LogicalInit("D", "Z", 1), BellStatePrep("A", "B", 1), SyndromeExtraction("D", 2),
        KnillEC("D", "A", "B", prepare_resource=False), LogicalMeasure("D", "Z"),
    ], noise_model=special(.017))
    c.validate_metadata()
    with pytest.raises(UnsupportedProjectionError, match="intermediate preparation/SE"):
        make_conditional_readout_model(c, c.bell_measurements[0])


@pytest.mark.parametrize("bad", ["missing", "epoch", "site", "duplicate", "after_cnot", "index"])
def test_invalid_stochastic_boundary_provenance_is_rejected(bad):
    c = make_compiler().compile([BellStatePrep("A", "B", 1)],
                               allow_open_outputs=True, noise_model=special(.01))
    bs = list(c.resource_preparation_boundaries)
    if bad == "missing":
        bs = []
    elif bad == "epoch":
        bs[0] = replace(bs[0], block_use_id=replace(bs[0].block_use_id, epoch=10))
    elif bad == "site":
        bs[0] = replace(bs[0], data_sites=(bs[0].data_sites[0],) * 9)
    elif bad == "duplicate":
        bs.append(bs[0])
    elif bad == "index":
        bs[0] = replace(bs[0], channel_instruction=bs[0].channel_instruction + 1)
    else:
        circuit = c.circuit.copy()
        channel = circuit[bs[0].channel_instruction]
        index = bs[0].channel_instruction
        circuit = circuit[:index] + circuit[index+1:]
        circuit.append(channel)
        bs[0] = replace(bs[0], channel_instruction=len(circuit)-1)
        bs[1] = replace(bs[1], channel_instruction=bs[1].channel_instruction-1)
        c = replace(c, noisy_circuit=circuit)
    corrupted = replace(c, resource_preparation_boundaries=tuple(bs))
    with pytest.raises(ValueError, match="Resource|resource"):
        corrupted.validate_metadata()
    with pytest.raises(DecoderViewError, match="Resource|resource"):
        corrupted.make_decoder_view()


@pytest.mark.parametrize("distance", [3, 5])
def test_recycled_epoch_post_se_atoms_retain_their_actual_physical_window(distance):
    from tests.helpers.lstim_equivalence import compile_pair
    from tests.helpers.lstim_programs import knill_operations, knill_source
    from tests.test_patch_reuse_knill_e2e import assert_physical_conditional_atoms

    c, _ = compile_pair(knill_source(distance=distance), knill_operations(distance=distance),
                         count=3, distance=distance, noise=special(.023))
    previous = -1
    for bell in c.bell_measurements:
        model = make_conditional_readout_model(c, bell)
        assert previous < model.start_instruction
        assert_physical_conditional_atoms(c, model)
        assert len(model.faults) == 6 * distance**2
        assert {b.block_use_id for b in c.resource_preparation_boundaries
                if b.channel_instruction in {f.instruction_index for f in model.faults}} == {
                    bell.first_resource_use_id, bell.output_use_id}
        previous = model.end_instruction
