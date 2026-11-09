"""Research-only M9 Knill location census and independent physical Pauli oracle."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

import numpy as np
import stim

from examples.knill_memory_offline_decoding import prepare_experiment
from examples.knill_memory_three_patch_reuse import prepare_three_patch
from logical_to_stim_converter import NoiseModel, ResourcePreparationNoise
from validation.ordinary_faults import annotation_masks

AXES = "XYZ"


@dataclass(frozen=True)
class Case:
    cycles: int
    reference_probability: float = 0.01

    def __post_init__(self):
        if (
            type(self.cycles) is not int
            or self.cycles not in (1, 3)
            or isinstance(self.reference_probability, bool)
            or not 0 < self.reference_probability <= 0.75
        ):
            raise ValueError("Phase 3 supports one or three d=3 cycles and a positive M9 prior")

    @property
    def name(self) -> str:
        return f"d3_Z_r{self.cycles}_m9_only"


@dataclass(frozen=True)
class Location:
    location_id: int
    boundary_id: int
    block_id: str
    epoch: int
    site: str
    wire: int
    ideal_cut: int
    noisy_instruction: int | None
    channel_tag: str


@dataclass(frozen=True)
class Assignment:
    rank: int
    atoms: tuple[tuple[int, str], ...]

    @property
    def weight(self) -> int:
        return len(self.atoms)


def make_experiment(case: Case, probability: float):
    if isinstance(probability, bool) or not 0 <= probability <= 0.75:
        raise ValueError("M9 probability must be in [0,.75]")
    noise = NoiseModel(resource_preparation=ResourcePreparationNoise(True, probability))
    if case.cycles == 1:
        return prepare_experiment(
            distance=3,
            basis="Z",
            bit=0,
            teleportations=1,
            resource_rounds=3,
            input_rounds=3,
            post_rounds=1,
            noise_model=noise,
        )
    return prepare_three_patch(
        distance=3,
        basis="Z",
        bit=0,
        teleportations=3,
        resource_rounds=3,
        input_rounds=3,
        post_rounds=1,
        noise_model=noise,
    )


def scan_locations(experiment, probability: float) -> tuple[Location, ...]:
    """Cross-check metadata, actual Stim channels, use epochs and exact site targets."""
    compiled = experiment.compiled
    boundaries = compiled.resource_preparation_boundaries
    if len(boundaries) != 2 * len(compiled.bell_measurements):
        raise AssertionError("wrong number of resource halves")
    if len({b.block_use_id for b in boundaries}) != len(boundaries):
        raise AssertionError("M9 resource use was reused without a new epoch")
    if compiled.circuit.without_noise() != compiled.ideal_circuit:
        raise AssertionError("M9 changed the ideal circuit")
    stochastic = [
        (i, instruction)
        for i, instruction in enumerate(compiled.circuit)
        if instruction.name in {"X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"}
        or instruction.name in {"M", "MX", "MY"}
        and instruction.gate_args_copy()
    ]
    expected_tags = {b.channel_tag for b in boundaries} if probability else set()
    if {instruction.tag for _, instruction in stochastic} != expected_tags:
        raise AssertionError("M9-only circuit has a missing or unexpected stochastic channel")
    if len(stochastic) != len(expected_tags):
        raise AssertionError("M9 channel was duplicated or batched across boundaries")
    if len(compiled.block_uses) != 1 + 2 * len(compiled.bell_measurements):
        raise AssertionError("unexpected physical-use history")
    if len(compiled.relocation_history) != len(compiled.bell_measurements):
        raise AssertionError("unexpected logical relocation count")
    if any(inst.name == "MPP" for inst in compiled.circuit):
        raise AssertionError("model-only preparation probes entered the physical circuit")
    result = []
    for boundary_id, boundary in enumerate(boundaries):
        block = next(
            b for b in compiled._compiler.blocks if b.block_id == boundary.block_use_id.block_id
        )
        expected_sites = tuple((block.block_id, site) for site in block.layout.data_ids)
        if boundary.data_sites != expected_sites:
            raise AssertionError("M9 target sites differ from the physical layout")
        cut = boundary.ideal_boundary_instruction
        if (
            not 0 < cut < len(compiled.ideal_circuit)
            or compiled.ideal_circuit[cut - 1].name != "TICK"
        ):
            raise AssertionError("M9 channel is not after the final preparation TICK")
        if probability:
            index = boundary.channel_instruction
            if index is None:
                raise AssertionError("positive M9 channel is missing")
            instruction = compiled.circuit[index]
            expected_wires = [compiled.physical_qubit_map[site] for site in expected_sites]
            if (
                instruction.name != "DEPOLARIZE1"
                or instruction.tag != boundary.channel_tag
                or instruction.gate_args_copy() != [probability]
                or [target.value for target in instruction.targets_copy()] != expected_wires
            ):
                raise AssertionError("actual M9 Stim channel disagrees with boundary metadata")
        elif boundary.channel_instruction is not None:
            raise AssertionError("zero-probability M9 emitted a stochastic channel")
        for site in expected_sites:
            result.append(
                Location(
                    len(result),
                    boundary_id,
                    boundary.block_use_id.block_id,
                    boundary.block_use_id.epoch,
                    site[1],
                    compiled.physical_qubit_map[site],
                    cut,
                    boundary.channel_instruction,
                    boundary.channel_tag,
                )
            )
    if len(result) != 2 * len(compiled.bell_measurements) * 3**2:
        raise AssertionError("wrong M9 physical location count")
    return tuple(result)


def pattern_counts(location_count: int) -> tuple[int, int, int]:
    if type(location_count) is not int or location_count < 1:
        raise ValueError("location count must be positive")
    return 1, 3 * location_count, 9 * location_count * (location_count - 1) // 2


def assignments(location_count: int):
    """Yield a stable rank for every exclusive weight-zero/one/two assignment."""
    pattern_counts(location_count)
    yield Assignment(0, ())
    rank = 1
    for location in range(location_count):
        for axis in AXES:
            yield Assignment(rank, ((location, axis),))
            rank += 1
    for left, right in combinations(range(location_count), 2):
        for a, b in product(AXES, repeat=2):
            yield Assignment(rank, ((left, a), (right, b)))
            rank += 1


def ideal_cut_for_noisy_index(compiled, noisy_index: int) -> int:
    """Map an exclusive noisy-instruction boundary to the ideal instruction cut."""
    return sum(
        instruction.name not in {"X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"}
        for instruction in compiled.circuit[:noisy_index]
    )


def _parity(raw: np.ndarray, masks: tuple[int, ...]) -> np.ndarray:
    result = np.zeros((len(raw), len(masks)), dtype=bool)
    for column, mask in enumerate(masks):
        indices = [i for i in range(mask.bit_length()) if mask & (1 << i)]
        if indices:
            result[:, column] = np.bitwise_xor.reduce(raw[:, indices], axis=1)
    return result


def simulate_assignments(
    experiment, locations, patterns, *, check_parity: bool = True, seed: int = 1901
):
    """Propagate all selected Pauli assignments through the ideal Stim circuit.

    Paired seeded simulators cancel identical stabilizer randomization. Turning
    that randomization off would leave harmless post-reset stabilizer markers
    that can masquerade as later record flips on recycled patches.
    """
    if not patterns:
        raise ValueError("physical simulation needs at least one assignment")
    compiled = experiment.compiled
    ideal = compiled.ideal_circuit
    count = len(patterns)
    by_cut = {}
    for shot, pattern in enumerate(patterns):
        for location_id, axis in pattern.atoms:
            location = locations[location_id]
            by_cut.setdefault(location.ideal_cut, []).append((shot, location.wire, axis))
    output_wires = [
        [compiled.physical_qubit_map[b.output_block_id, site] for site in model.output_data_ids]
        for b, model in zip(compiled.bell_measurements, experiment.conditional_models, strict=True)
    ]
    ends = {
        ideal_cut_for_noisy_index(compiled, model.end_instruction): cycle
        for cycle, model in enumerate(experiment.conditional_models)
    }
    if len(ends) != len(output_wires):
        raise AssertionError("Bell readout intervals overlap at an ideal cut")
    support = np.zeros((count, len(ends), 2, len(output_wires[0])), dtype=bool)
    sim = stim.FlipSimulator(batch_size=count, num_qubits=ideal.num_qubits, seed=seed)
    reference = stim.FlipSimulator(batch_size=count, num_qubits=ideal.num_qubits, seed=seed)
    for cut in range(len(ideal) + 1):
        for axis in AXES:
            mask = np.zeros((ideal.num_qubits, count), dtype=bool)
            for shot, wire, fault_axis in by_cut.get(cut, ()):
                if fault_axis == axis:
                    mask[wire, shot] ^= True
            if mask.any():
                sim.broadcast_pauli_errors(pauli=axis, mask=mask)
        if cut < len(ideal):
            sim.do(ideal[cut])
            reference.do(ideal[cut])
        if cut + 1 in ends:
            cycle = ends[cut + 1]
            wires = output_wires[cycle]
            for shot, (pauli, baseline) in enumerate(
                zip(sim.peek_pauli_flips(), reference.peek_pauli_flips(), strict=True)
            ):
                x, z = pauli.to_numpy()
                baseline_x, baseline_z = baseline.to_numpy()
                support[shot, cycle, 0] = x[wires] ^ baseline_x[wires]
                support[shot, cycle, 1] = z[wires] ^ baseline_z[wires]
    raw = (sim.get_measurement_flips() ^ reference.get_measurement_flips()).T
    detectors = (sim.get_detector_flips() ^ reference.get_detector_flips()).T
    observables = (sim.get_observable_flips() ^ reference.get_observable_flips()).T
    if check_parity:
        detector_masks, observable_masks = annotation_masks(ideal)
        if not np.array_equal(detectors, _parity(raw, detector_masks)) or not np.array_equal(
            observables, _parity(raw, observable_masks)
        ):
            raise AssertionError("Stim physical flips disagree with independent raw-record parity")
    return raw, detectors, observables, support


def audit_conditional_singles(experiment, locations, patterns, raw, support):
    """Compare physical single-fault Bell actions with every conditional map."""
    compiled = experiment.compiled
    if any(pattern.weight != 1 for pattern in patterns):
        raise ValueError("conditional single audit accepts only weight-one patterns")
    by_rank = {pattern.rank: i for i, pattern in enumerate(patterns)}
    checked = 0
    for cycle, (bell, model) in enumerate(
        zip(compiled.bell_measurements, experiment.conditional_models, strict=True)
    ):
        own = [
            location for location in locations if location.boundary_id in (2 * cycle, 2 * cycle + 1)
        ]
        rows = {
            (fault.instruction_index, fault.paulis): i
            for i, fault in enumerate(model.faults)
            if fault.channel == "DEPOLARIZE1"
        }
        matrices = {
            name: getattr(model, name).incidence_matrix.toarray().astype(bool)
            for name in (
                "raw_flip_map",
                "x_syndrome_map",
                "z_syndrome_map",
                "logical_flip_map",
                "output_x_map",
                "output_z_map",
            )
        }
        for location in own:
            for axis in AXES:
                rank = 1 + 3 * location.location_id + AXES.index(axis)
                shot = by_rank[rank]
                row = rows.get((location.noisy_instruction, ((location.wire, axis),)))
                if row is None:
                    raise AssertionError("conditional Bell model omitted a physical M9 atom")
                selected = raw[shot, model.readout_record_ids]
                x_count = len(bell.x_readout.records)
                x_raw, z_raw = selected[:x_count], selected[x_count:]
                x_syndrome = x_raw.astype(np.uint8) @ bell.x_readout.check_matrix("X").T % 2
                z_syndrome = z_raw.astype(np.uint8) @ bell.z_readout.check_matrix("Z").T % 2
                logical = np.array(
                    [
                        np.bitwise_xor.reduce(
                            raw[
                                shot,
                                [
                                    compiled.measurement_index_by_key[key]
                                    for key in readout.logical_parity.terms
                                ],
                            ]
                        )
                        for readout in (bell.x_readout, bell.z_readout)
                    ],
                    dtype=bool,
                )
                checks = (
                    ("raw_flip_map", selected),
                    ("x_syndrome_map", x_syndrome),
                    ("z_syndrome_map", z_syndrome),
                    ("logical_flip_map", logical),
                    ("output_x_map", support[shot, cycle, 0]),
                    ("output_z_map", support[shot, cycle, 1]),
                )
                for name, observed in checks:
                    if not np.array_equal(matrices[name][row], observed):
                        raise AssertionError(f"physical M9 atom disagrees with {name}: {rank}")
                checked += 1
    if checked != len(patterns):
        raise AssertionError("some M9 atoms were not compared with conditional maps")
    return {"checked_atoms": checked, "maps": tuple(matrices)}


def audit_pair_action(patterns, raw, detectors, observables, support, single_actions):
    """Check every physically simulated pair against independent GF(2) composition."""
    single_raw, single_detectors, single_observables, single_support = single_actions
    checked = 0
    for row, pattern in enumerate(patterns):
        if pattern.weight != 2 or pattern.atoms[0][0] == pattern.atoms[1][0]:
            raise AssertionError("pair contains a duplicate or missing physical location")
        first, second = (3 * location + AXES.index(axis) for location, axis in pattern.atoms)
        for actual, singles in (
            (raw, single_raw),
            (detectors, single_detectors),
            (observables, single_observables),
            (support, single_support),
        ):
            if not np.array_equal(actual[row], singles[first] ^ singles[second]):
                raise AssertionError(f"physical GF(2) pair action disagrees at rank {pattern.rank}")
        checked += 1
    return checked


def audit_boundary_ownership(experiment, locations):
    """Own M9 faults in conditional Bell windows, after their preparation probes."""
    compiled = experiment.compiled
    requests = {request.module_id: request for request in experiment.requests.boundaries}
    for boundary in compiled.resource_preparation_boundaries:
        request = requests[boundary.preparation_module_id]
        if any(inst.tag == boundary.channel_tag for inst in request.model_circuit):
            raise AssertionError("preparation prefix includes its own post-SE M9 channel")
        model = next(
            model
            for model in experiment.conditional_models
            if model.resource_entangling_module_id == boundary.resource_entangling_module_id
        )
        if not model.start_instruction <= boundary.channel_instruction < model.end_instruction:
            raise AssertionError("M9 channel is outside its conditional Bell interval")
        atoms = [
            fault
            for fault in model.faults
            if fault.instruction_index == boundary.channel_instruction
            and fault.channel == "DEPOLARIZE1"
        ]
        if len(atoms) != 3 * len(boundary.data_sites):
            raise AssertionError("conditional M9 atom count disagrees with physical sites")
        if len({fault.exclusive_group for fault in atoms}) != len(boundary.data_sites):
            raise AssertionError("conditional model lost exclusive M9 groups")
    if len(locations) != sum(len(b.data_sites) for b in compiled.resource_preparation_boundaries):
        raise AssertionError("resource channel and location counts disagree")
    return {
        "preparation_prefixes": len(compiled.resource_preparation_boundaries),
        "conditional_windows": len(experiment.conditional_models),
    }


def audit_epoch_clearing(experiment, locations, singles):
    """Old physical Pauli support vanishes before a recycled patch's new M9 cut."""
    compiled = experiment.compiled
    by_cut = {}
    for shot, pattern in enumerate(singles):
        location_id, axis = pattern.atoms[0]
        location = locations[location_id]
        by_cut.setdefault(location.ideal_cut, []).append((shot, location.wire, axis))
    boundary_at_cut = {}
    for boundary in compiled.resource_preparation_boundaries:
        boundary_at_cut.setdefault(boundary.ideal_boundary_instruction, []).append(boundary)
    sim = stim.FlipSimulator(
        batch_size=len(singles), num_qubits=compiled.ideal_circuit.num_qubits, seed=281
    )
    reference = stim.FlipSimulator(
        batch_size=len(singles), num_qubits=compiled.ideal_circuit.num_qubits, seed=281
    )
    checked = 0
    for cut, instruction in enumerate(compiled.ideal_circuit):
        if cut in boundary_at_cut:
            current = sim.peek_pauli_flips()
            baseline = reference.peek_pauli_flips()
            for boundary in boundary_at_cut[cut]:
                old_shots = [
                    shot
                    for shot, pattern in enumerate(singles)
                    if locations[pattern.atoms[0][0]].block_id == boundary.block_use_id.block_id
                    and locations[pattern.atoms[0][0]].epoch < boundary.block_use_id.epoch
                ]
                wires = [
                    wire
                    for (block, _), wire in compiled.physical_qubit_map.items()
                    if block == boundary.block_use_id.block_id
                ]
                for shot in old_shots:
                    x, z = current[shot].to_numpy()
                    bx, bz = baseline[shot].to_numpy()
                    if np.any(x[wires] ^ bx[wires]) or np.any(z[wires] ^ bz[wires]):
                        raise AssertionError(
                            f"retired physical Pauli survived new reset epoch: "
                            f"cut={cut} use={boundary.block_use_id} rank={singles[shot].rank} "
                            f"x={np.flatnonzero(x[wires])} z={np.flatnonzero(z[wires])}"
                        )
                    checked += 1
        for axis in AXES:
            mask = np.zeros((compiled.ideal_circuit.num_qubits, len(singles)), dtype=bool)
            for shot, wire, selected in by_cut.get(cut, ()):
                if selected == axis:
                    mask[wire, shot] = True
            if mask.any():
                sim.broadcast_pauli_errors(pauli=axis, mask=mask)
        sim.do(instruction)
        reference.do(instruction)
    if compiled.relocation_history and checked == 0 and len(compiled.relocation_history) > 1:
        raise AssertionError("no recycled physical uses were checked")
    return {"retired_atom_use_checks": checked}


def deterministic_physical_circuit(compiled, locations, pattern):
    """Spell a test fault as explicit ideal Stim Pauli gates at its actual cuts."""
    by_cut = {}
    for location_id, axis in pattern.atoms:
        loc = locations[location_id]
        by_cut.setdefault(loc.ideal_cut, []).append((loc.wire, axis))
    result = stim.Circuit()
    for cut, instruction in enumerate(compiled.ideal_circuit):
        for wire, axis in by_cut.get(cut, ()):
            result.append(axis, [wire])
        result.append(instruction)
    return result


def audit_direct_physical_samples(experiment, locations, patterns, actions, *, seed=1937):
    """Check selected explicit fault circuits against original-source events/labels."""
    compiled = experiment.compiled
    _, detectors, observables, _ = actions
    converter = compiled.circuit.compile_m2d_converter()
    for row, pattern in enumerate(patterns):
        circuit = deterministic_physical_circuit(compiled, locations, pattern)
        raw = circuit.compile_sampler(seed=seed + pattern.rank).sample(8)
        physical_detectors, physical_observables = converter.convert(
            measurements=raw, separate_observables=True
        )
        if not np.all(physical_detectors == detectors[row]) or not np.all(
            physical_observables == observables[row]
        ):
            raise AssertionError(f"explicit Stim fault circuit disagrees at rank {pattern.rank}")
    return {"explicit_circuits": len(patterns), "shots_per_circuit": 8}
