"""Independent signed logical physics, exact physical noise and public consumer checks."""

import json
from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
import stim

from examples.deep_clifford import (
    deep_clifford_source,
    experiment_noise,
    recorded_sector_frames,
    run,
)
from logical_to_stim_converter import (
    BindPatch,
    BlockUseId,
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    LogicalPauliProduct,
    LSTIMCompileError,
    LSTIMSemanticError,
    NoiseModel,
    NoiseOverride,
    NoiseParameters,
    PostInitializationNoise,
    ResourcePreparationNoise,
    RotatedSurfaceCodeBackend,
    TransversalCNOT,
    TransversalH,
    format_logical_circuit,
    parse_logical_circuit,
)
from logical_to_stim_converter.decoding import (
    SourceMismatchError,
    make_conditional_readout_model,
    make_stage_requests,
    source_fingerprint,
)


def compiler(n=1, d=3):
    return CircuitCompiler(
        [
            LogicalBlock.placed(f"P{i}", CodeSpec.rotated_surface(d), patch_index=i)
            for i in range(n)
        ],
        logical_to_block={f"Q{i}": f"P{i}" for i in range(n)},
    )


def checked_samples(compiled, products, shots=24):
    plan = compiled.make_frame_plan()
    probe = compiled.make_terminal_observable_probe(products)
    samples = probe.circuit.compile_sampler(seed=131).sample(shots)
    raw, _ = probe.split_measurements(samples)
    frames = recorded_sector_frames(compiled, plan, make_stage_requests(compiled), raw)
    assert not probe.corrected_flips(samples, frames).any()
    return probe, samples, frames


def parallel_source(n, cycles=1, serial=False, rounds=1):
    lines = ["FORMAT(1)", "CODE sc ROTATED_SURFACE(3)"]
    for q in range(n):
        lines.extend(f"PATCH P{q}_{p} sc index={3 * q + p}" for p in range(3))
    for q in range(n):
        lines.extend((f"BIND Q{q} P{q}_0", f"INIT_X(1) Q{q}"))
    for cycle in range(cycles):
        _, a, b = ((0, 1, 2), (2, 0, 1), (1, 2, 0))[cycle % 3]
        for q in range(n):
            lines.extend((f"BIND A{cycle}_{q} P{q}_{a}", f"BIND B{cycle}_{q} P{q}_{b}"))
        members = [
            f"KNILL_EC[ec{cycle}_q{q}]({rounds}) Q{q} A{cycle}_{q} B{cycle}_{q}" for q in range(n)
        ]
        lines.extend(members if serial or n == 1 else ["PARALLEL {", *members, "}"])
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("n", [1, 2, 4])
def test_parallel_knill_physical_overlap_semantics_and_stages(n):
    source = parallel_source(n)
    program = parse_logical_circuit(source)
    assert format_logical_circuit(parse_logical_circuit(format_logical_circuit(program)))
    c = program.compile(allow_open_outputs=True)
    c.validate_metadata()
    assert len(c.bell_measurements) == n
    assert len(c.preparations) == 3 * n
    assert len(c.relocation_history) == n
    by_module = {f.module_id: f for f in c.fragments}
    if n > 1:
        for kind in ("LogicalInit", "TransversalCNOT", "LogicalMeasure"):
            assert any(
                sum(
                    by_module[m].operation_type == kind
                    for m in set(layer.operation_by_block.values())
                )
                >= n
                for layer in c.time_layers
            )
    products = [LogicalPauliProduct({f"Q{q}": "X"}) for q in range(n)]
    checked_samples(c, products)
    serial = parse_logical_circuit(parallel_source(n, serial=True)).compile(allow_open_outputs=True)
    checked_samples(serial, products)
    if n > 1:
        assert len(c.time_layers) < len(serial.time_layers)
    requests = make_stage_requests(c)
    plan = c.make_frame_plan()
    order = {module: i for i, (_, module) in enumerate(requests.order)}
    for request in requests.boundaries:
        assert request.block_use_id == plan.boundary_by_id[request.module_id].block_use_id
        assert set(request.last_record_ids) <= set(request.view.measurement_map.global_ids)
    for bell in c.bell_measurements:
        for prep in c.preparations:
            if prep.block_use_id in (bell.first_resource_use_id, bell.output_use_id):
                assert order[prep.module_id] < order[bell.x_readout.module_id]


@pytest.mark.parametrize("cycles", [2, 4])
def test_parallel_recycling_epochs_ancestry_and_corrections(cycles):
    c = parse_logical_circuit(parallel_source(2, cycles)).compile(
        allow_open_outputs=True,
        noise_model=NoiseModel(
            NoiseParameters(idle=0.001), resource_preparation=ResourcePreparationNoise(True, 0.002)
        ),
    )
    c.validate_metadata()
    assert len(c.block_uses) == 2 * (1 + 2 * cycles)
    assert len(c.resource_preparation_boundaries) == 4 * cycles
    assert len(c.physical_qubit_map) == 6 * 17
    for q in range(2):
        for b in [
            b
            for b in c.resource_preparation_boundaries
            if b.block_use_id.block_id.startswith(f"P{q}_")
        ]:
            assert len(b.data_sites) == 9
            assert b.channel_instruction is not None
    ideal = parse_logical_circuit(parallel_source(2, cycles)).compile(allow_open_outputs=True)
    probe, samples, frames = checked_samples(
        ideal, [LogicalPauliProduct({"Q0": "X"}), LogicalPauliProduct({"Q1": "X"})]
    )
    assert probe.original_measurement_count == len(ideal.measurements)
    assert np.array_equal(frames.raw_measurements, samples[:, : len(ideal.measurements)])
    for q in range(2):
        deps = ideal.preparation_dependencies[f"Q{q}"]
        assert all(
            next(p for p in ideal.preparations if p.module_id == d).block_id.startswith(f"P{q}_")
            for d in deps
        )


@pytest.mark.parametrize("replacement", ["KNILL_EC Q0 A0_0 B0_0", "H Q0", "BELL_PREP A0_0 B0_0"])
def test_parallel_logical_conflicts_rejected(replacement):
    source = parallel_source(2).replace("KNILL_EC[ec0_q1](1) Q1 A0_1 B0_1", replacement)
    with pytest.raises(LSTIMCompileError, match="same physical block twice"):
        parse_logical_circuit(source).compile(allow_open_outputs=True)


def test_parallel_physical_reservation_conflict_rejected():
    with pytest.raises(ValueError):
        compiler(2).compile(
            [BindPatch("fresh", "P0"), (KnillEC("Q0", "Q1", "fresh"),)], allow_open_outputs=True
        )


def test_parallel_bell_prep_matches_existing_python_compiler():
    source = parallel_source(2).replace(
        "KNILL_EC[ec0_q0](1) Q0 A0_0 B0_0", "BELL_PREP[bell0](1) A0_0 B0_0"
    )
    source = source.replace("KNILL_EC[ec0_q1](1) Q1 A0_1 B0_1", "BELL_PREP[bell1](1) A0_1 B0_1")
    c = parse_logical_circuit(source).compile(allow_open_outputs=True)
    checked_samples(
        c,
        [
            LogicalPauliProduct({"A0_0": "Y", "B0_0": "Y"}, -1),
            LogicalPauliProduct({"A0_1": "X", "B0_1": "X"}),
        ],
    )


@pytest.mark.parametrize("d", [3, 5, 7])
@pytest.mark.parametrize("axis", ["X", "Y", "Z"])
@pytest.mark.parametrize("orientation", [0, 1])
def test_transversal_pauli_signed_flows_and_all_data_sites(d, axis, orientation):
    block = LogicalBlock.placed("P", CodeSpec.rotated_surface(d))
    backend = RotatedSurfaceCodeBackend()
    chunk = backend.transversal_pauli(block, "Q", axis, orientation)
    chunk.verify()
    (gate,) = chunk.circuit
    assert gate.name == axis
    assert len(gate.targets_copy()) == d * d
    assert {q for q, i in chunk.q2i.items() if i in {t.value for t in gate.targets_copy()}} == {
        block.position(q) for q in block.layout.data_ids
    }
    for flow in chunk.flows:
        assert flow.start == flow.end
        expected = flow.obs_name is not None and flow.obs_name[1] != axis
        assert flow.sign == expected
    # Corrupt a physical site: a missing Pauli must fail the signed declared flows.
    bad = stim.Circuit()
    bad.append(axis, gate.targets_copy()[1:])
    with pytest.raises(ValueError):
        chunk.with_edits(circuit=bad).verify()


@pytest.mark.parametrize("mode,count", [("transversal", 9), ("physical", 5), ("frame", 0)])
def test_pauli_gate_noise_locations_and_old_modes(mode, count):
    c = compiler().compile(
        [LogicalInit("Q0", "X", 1), LogicalPauli("Q0", "Y", mode=mode)],
        allow_open_outputs=True,
        noise_model=NoiseModel(NoiseParameters(one_qubit=0.02)),
    )
    f = c.fragments[-1]
    physical = [i for i in c.circuit if i.tag == f.module_id]
    assert sum(len(i.targets_copy()) for i in physical if i.name in ("X", "Y", "Z")) == count
    assert sum(len(i.targets_copy()) for i in c.circuit if i.name == "DEPOLARIZE1") == count
    assert all(i.gate_args_copy() == [0.02] for i in c.circuit if i.name == "DEPOLARIZE1")
    assert bool(f.steps()) == (mode != "frame")
    checked_samples(
        c if mode == "frame" else replace(c, noisy_circuit=None),
        [LogicalPauliProduct({"Q0": "X"}, -1)],
    )


@pytest.mark.parametrize("gate", ["H", "X", "Y", "Z", "CX"])
def test_terminal_logical_conjugation_with_cliffords_and_y_products(gate):
    operations = [
        LogicalInit(("Q0", "Q1", "Q2", "Q3"), "X", 1),
        TransversalH(("Q1", "Q3")),
        TransversalCNOT("Q0", "Q1"),
        TransversalCNOT("Q2", "Q3"),
    ]
    logical = stim.Circuit("H 1 3\nCX 0 1 2 3")
    if gate == "CX":
        operations.append(TransversalCNOT("Q1", "Q2"))
        logical.append("CX", [1, 2])
    elif gate == "H":
        operations.append(TransversalH("Q0"))
        logical.append("H", [0])
    else:
        operations.append(LogicalPauli("Q0", gate, mode="transversal"))
        logical.append(gate, [0])
    c = compiler(4).compile(operations, allow_open_outputs=True)
    products = []
    for initial in ("X___", "_X__", "__X_", "___X", "XX__", "__XX"):
        p = stim.PauliString(initial).after(logical)
        products.append(
            LogicalPauliProduct({f"Q{i}": "_XYZ"[p[i]] for i in range(4) if p[i]}, int(p.sign.real))
        )
    probe, samples, frames = checked_samples(c, products)
    assert any(len(p.factors) > 1 for p in products)
    # Actually execute a logical error before the terminal MPP, independently of frames.
    error = stim.PauliString(c.circuit.num_qubits)
    # Canonical logical Z after H uses the bottom rotated boundary.
    block = c._compiler.blocks[0]
    d = block.code.d
    positions = [
        complex(1, 2 * y + 1) if not c.orientations["Q0"] else complex(2 * y + 1, 2 * d - 1)
        for y in range(d)
    ]
    for pos in positions:
        local = next(k for k in block.layout.data_ids if block.position(k) == pos)
        error[c.physical_qubit_map["P0", local]] = "Z"
    circuit = c.circuit.copy()
    circuit.append("Z", [i for i in range(len(error)) if error[i]])
    for inst in probe.circuit[len(c.circuit) :]:
        circuit.append(inst)
    faults = circuit.compile_sampler(seed=131).sample(24)
    # Prefixes share exactly the same random measurement branches.
    assert np.array_equal(faults[:, : len(c.measurements)], frames.raw_measurements)
    expected = [sum(error[i] != 0 for i in o.physical_x) % 2 for o in probe.observables]
    assert np.array_equal(probe.corrected_flips(faults, frames), np.tile(expected, (24, 1)))
    assert not probe.corrected_flips(samples, frames).any()


def test_terminal_rejects_wrong_sign_random_noncommuting_or_dead_targets():
    c = compiler(2).compile([LogicalInit(("Q0", "Q1"), "X", 1)], allow_open_outputs=True)
    for products, reason in [
        ([LogicalPauliProduct({"Q0": "Z"})], "nondeterministic"),
        ([LogicalPauliProduct({"Q0": "X"}, -1)], "does not stabilize"),
        ([LogicalPauliProduct({"absent": "X"})], "not an active"),
        ([LogicalPauliProduct({"Q0": "X"}), LogicalPauliProduct({"Q0": "Y"})], "commute"),
    ]:
        with pytest.raises(ValueError, match=reason):
            c.make_terminal_observable_probe(products)
    p = c.make_terminal_observable_probe(
        [LogicalPauliProduct({"Q0": "X"}, -1)], require_stabilizers=False
    )
    assert p.observables[0].expected_value == 1
    closed = c.append([LogicalMeasure("Q0", "X")])
    with pytest.raises(ValueError, match="not an active"):
        closed.make_terminal_observable_probe([LogicalPauliProduct({"Q0": "X"})])


def test_terminal_preserves_original_metadata_models_records_and_frame_identity():
    c = parse_logical_circuit(parallel_source(2, cycles=2)).compile(allow_open_outputs=True)
    before, fingerprint, plan = c.circuit.copy(), source_fingerprint(c), c.make_frame_plan()
    detectors, measurements = c.detectors, c.measurements
    probe, samples, frames = checked_samples(c, [LogicalPauliProduct({"Q0": "X"})])
    assert c.circuit == before and source_fingerprint(c) == fingerprint
    assert c.detectors == detectors and c.measurements == measurements
    assert c.make_frame_plan() == plan
    assert probe.measurement_indices == (len(measurements),)
    copy = probe.circuit
    copy.append("X", [0])
    assert copy != probe.circuit
    wrong = samples.copy()
    wrong[:, 0] ^= True
    with pytest.raises(SourceMismatchError, match="raw prefix"):
        probe.corrected_flips(wrong, frames)
    other = compiler().compile([LogicalInit("Q0", "X", 1)], allow_open_outputs=True)
    otherplan = other.make_frame_plan()
    otherframes = otherplan.start(
        np.zeros((24, len(other.measurements)), dtype=bool),
        source_fingerprint=otherplan.source_fingerprint,
    )
    with pytest.raises(SourceMismatchError, match="different sources"):
        probe.corrected_flips(samples, otherframes)


@pytest.mark.parametrize("bad", [-1, 0.75001, 1, True, float("nan"), float("inf"), "0.1"])
def test_post_init_probability_rejected(bad):
    with pytest.raises(ValueError):
        PostInitializationNoise("init", BlockUseId("P0"), bad)


@pytest.mark.parametrize("at_end", [False, True])
def test_ideal_initialization_exact_post_init_noise_and_metadata(at_end):
    source = "FORMAT(1)\nCODE sc ROTATED_SURFACE(3)\nPATCH P0 sc index=0\nBIND Q0 P0\n"
    source += "INIT_X[initial](1) Q0 noise=ideal\n"
    if not at_end:
        source += "Y Q0 mode=transversal\nSE[final](1) Q0 noise=ideal\n"
    model = NoiseModel(
        NoiseParameters(0.01, 0.02, 0.03, 0.04, 0.05),
        post_initialization=(
            PostInitializationNoise("initial", BlockUseId("P0"), 0.0123456789012345),
        ),
    )
    c = parse_logical_circuit(source).compile(allow_open_outputs=True, noise_model=model)
    c.validate_metadata()
    (boundary,) = c.post_initialization_boundaries
    channel = c.circuit[boundary.channel_instruction]
    assert channel.name == "DEPOLARIZE1"
    assert channel.gate_args_copy() == [0.0123456789012345]
    assert [t.value for t in channel.targets_copy()] == [
        c.physical_qubit_map[s] for s in boundary.data_sites
    ]
    before = c.circuit[: boundary.channel_instruction]
    assert before == before.without_noise()
    if not at_end:
        after = c.circuit[boundary.channel_instruction + 1 :]
        assert any(i.name == "DEPOLARIZE1" and i.gate_args_copy() == [0.02] for i in after)
        # Terminal SE has neither gate/result/idle noise.
        last = c.fragments[-1].module_id
        assert all(
            (i.name in ("R", "RX", "CX", "M", "MX")) and i.gate_args_copy() in ([], [0.0])
            for i in c.circuit
            if i.tag == last
        )
    requests = make_stage_requests(c)
    init = next(r for r in requests.boundaries if r.module_id == boundary.preparation_module_id)
    assert not any(i.tag == boundary.channel_tag for i in init.model_circuit)
    exported = json.loads(json.dumps(c.export_metadata()))
    assert exported["post_initialization_boundaries"][0]["probability"] == boundary.probability
    assert exported["source_fingerprint"] == source_fingerprint(c)
    exact = stim.Circuit()
    for i in exported["selected_instructions"]:
        exact.append(
            i["name"], [stim.GateTarget(t) for t in i["targets"]], i["arguments"], tag=i["tag"]
        )
    assert exact == c.circuit


def test_post_init_epoch_identity_zero_duplicate_and_m9_separation():
    program = [
        LogicalInit("Q0", "X", 1, operation_id="first"),
        LogicalMeasure("Q0", "X"),
        BindPatch("new", "P0"),
        LogicalInit("new", "Z", 1, operation_id="second"),
    ]
    model = NoiseModel(
        post_initialization=(PostInitializationNoise("second", BlockUseId("P0", 1), 0.1),)
    )
    c = compiler().compile(program, allow_open_outputs=True, noise_model=model)
    assert c.post_initialization_boundaries[0].block_use_id == BlockUseId("P0", 1)
    wrong = replace(
        model, post_initialization=(PostInitializationNoise("second", BlockUseId("P0"), 0.1),)
    )
    with pytest.raises(ValueError, match="match one LogicalInit"):
        compiler().compile(program, allow_open_outputs=True, noise_model=wrong)
    with pytest.raises(ValueError, match="Duplicate"):
        replace(model, post_initialization=model.post_initialization * 2)
    zero = replace(
        model, post_initialization=(PostInitializationNoise("second", BlockUseId("P0", 1), 0),)
    )
    baseline = compiler().compile(program, allow_open_outputs=True, noise_model=NoiseModel())
    assert (
        compiler().compile(program, allow_open_outputs=True, noise_model=zero).circuit
        == baseline.circuit
    )
    source = parallel_source(2)
    c = parse_logical_circuit(source).compile(allow_open_outputs=True)
    resource = next(p for p in c.preparations if p.logical_id == "A0_0")
    f = next(f for f in c.fragments if f.module_id == resource.module_id)
    combined = NoiseModel(
        resource_preparation=ResourcePreparationNoise(True, 0.01),
        post_initialization=(PostInitializationNoise(f.operation_id, f.block_use_ids[0], 0.01),),
    )
    with pytest.raises(ValueError, match="same use"):
        parse_logical_circuit(source).compile(allow_open_outputs=True, noise_model=combined)


@pytest.mark.parametrize("m9", [False, True])
def test_parallel_idle_noise_exact_per_layer_and_resource_policy(m9):
    model = NoiseModel(
        NoiseParameters(idle=0.001), resource_preparation=ResourcePreparationNoise(m9, 0.003)
    )
    c = parse_logical_circuit(parallel_source(2)).compile(
        allow_open_outputs=True, noise_model=model
    )
    sites = {
        b: {i for (bid, _), i in c.physical_qubit_map.items() if bid == b}
        for b, _ in c.physical_qubit_map
    }
    expected = Counter()
    intervals = {
        b.block_use_id: (b.first_layer, b.final_se_layer) for b in c.resource_preparation_boundaries
    }
    for layer in c.time_layers:
        for use in layer.active_use_ids:
            if use in intervals and intervals[use][0] <= layer.index <= intervals[use][1]:
                continue
            expected.update(
                (layer.index, i, 0.001) for i in sites[use.block_id] - layer.used_qubits
            )
    actual, layer = Counter(), 0
    for i in c.circuit:
        if i.name == "TICK":
            layer += 1
        elif i.name == "DEPOLARIZE1" and not i.tag:
            actual.update((layer, t.value, i.gate_args_copy()[0]) for t in i.targets_copy())
    assert actual == expected
    for bell in c.bell_measurements:
        model = make_conditional_readout_model(c, bell)
        assert model.source_fingerprint == source_fingerprint(c)


@pytest.mark.parametrize("option", ["noise=true", "noise=1", "noise=noisy"])
def test_noise_override_invalid_values(option):
    with pytest.raises(LSTIMSemanticError, match="noise must be ideal"):
        parse_logical_circuit(parallel_source(1).replace("INIT_X(1) Q0", f"INIT_X(1) Q0 {option}"))


@pytest.mark.parametrize("depth,cycles", [(2, 1), (3, 1), (2, 2)])
def test_deep_clifford_recycling_end_to_end(depth, cycles):
    source, products = deep_clifford_source(depth=depth, cycles=cycles)
    c = parse_logical_circuit(source).compile(allow_open_outputs=True)
    c.validate_metadata()
    assert len(c.relocation_history) == 4 * depth * cycles
    assert len(c.physical_qubit_map) == 12 * 17
    checked_samples(c, products, shots=12)


@pytest.mark.parametrize("ideal_resource", [False, True])
def test_public_consumer_noisy_sampling_export_and_both_resource_policies(tmp_path, ideal_resource):
    summary = run(shots=4, output=tmp_path, ideal_resource=ideal_resource)
    assert summary["ideal_failures"] == 0
    assert summary["teleportations"] == 8
    exported = json.loads((tmp_path / "metadata.json").read_text())
    assert len(exported["resource_preparation_boundaries"]) == (16 if ideal_resource else 0)
    assert experiment_noise(input_error=0.02).post_initialization[0].block_use_id == BlockUseId(
        "P0_0"
    )


@pytest.mark.parametrize("d", [3, 5, 7])
@pytest.mark.parametrize("axis", ["X", "Y", "Z"])
def test_transversal_before_and_after_h_cx_signed_action_and_noise_width(d, axis):
    ops = [
        LogicalInit("Q0", "X", 1),
        LogicalInit("Q1", "Z", 1),
        LogicalPauli("Q0", axis, mode="transversal"),
        TransversalH("Q0"),
        TransversalCNOT("Q0", "Q1"),
        LogicalPauli("Q1", axis, mode="transversal"),
        TransversalH("Q1"),
        TransversalCNOT("Q1", "Q0"),
    ]
    c = compiler(2, d).compile(ops, allow_open_outputs=True)
    reference = stim.Circuit()
    reference.append(axis, [0])
    reference.append("H", [0])
    reference.append("CX", [0, 1])
    reference.append(axis, [1])
    reference.append("H", [1])
    reference.append("CX", [1, 0])
    products = []
    for initial in ("X_", "_Z"):
        p = stim.PauliString(initial).after(reference)
        products.append(
            LogicalPauliProduct({f"Q{i}": "_XYZ"[p[i]] for i in range(2) if p[i]}, int(p.sign.real))
        )
    checked_samples(c, products, shots=8)
    noisy = compiler(2, d).compile(
        ops,
        allow_open_outputs=True,
        noise_model=NoiseModel(operation_overrides={"LogicalPauli": NoiseOverride(one_qubit=0.01)}),
    )
    channels = [i for i in noisy.circuit if i.name == "DEPOLARIZE1"]
    assert sum(len(i.targets_copy()) for i in channels) == 2 * d * d
    assert all(i.gate_args_copy() == [0.01] for i in channels)
