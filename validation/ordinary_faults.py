"""Research-only ordinary-memory physical fault table and independent oracle."""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
import stim

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    NoiseParameters,
    SyndromeExtraction,
    TransversalH,
)
from logical_to_stim_converter.decoding import source_fingerprint

NOISE_GATES = {"X_ERROR", "Y_ERROR", "Z_ERROR", "DEPOLARIZE1", "DEPOLARIZE2"}
ONE_QUBIT_CLIFFORDS = {"H", "X", "Y", "Z", "S", "S_DAG", "H_XY", "H_YZ"}
MEASUREMENTS = {"M", "MX", "MY"}
RESETS = {"R", "RX", "RY"}
TWO_PAULIS = tuple(a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II")


@dataclass(frozen=True)
class Case:
    distance: int
    basis: str
    rounds: int
    probabilities: tuple[float, float, float, float, float]
    variant: str = "ordinary"  # ordinary, h, signed, spectator

    def __post_init__(self):
        if (
            self.distance not in (3, 5)
            or self.basis not in ("X", "Z")
            or type(self.rounds) is not int
            or self.rounds < 1
            or self.variant not in {"ordinary", "h", "signed", "spectator"}
            or len(self.probabilities) != 5
            or any(
                isinstance(p, bool) or not math.isfinite(p) or not 0 <= p <= 0.1
                for p in self.probabilities
            )
        ):
            raise ValueError("unsupported ordinary-memory validation case")
        if self.variant == "h" and self.basis != "X":
            raise ValueError("H control must end in X basis")
        if self.variant == "signed" and self.basis != "Z":
            raise ValueError("signed control must end in Z basis")
        if self.variant == "spectator" and self.rounds < 2:
            raise ValueError("spectator control needs a primary extraction interval")

    @property
    def name(self) -> str:
        return f"d{self.distance}_{self.basis}_r{self.rounds}_{self.variant}"


def build_case(case: Case):
    code = CodeSpec.rotated_surface(case.distance)
    blocks = [LogicalBlock.placed("P0", code)]
    if case.variant == "spectator":
        blocks.append(LogicalBlock.placed("P1", code, patch_index=1))
    compiler = CircuitCompiler(
        blocks, logical_to_block={"q": "P0", **({"s": "P1"} if case.variant == "spectator" else {})}
    )
    if case.variant == "spectator":
        program = [
            LogicalInit("q", case.basis, 1),
            [SyndromeExtraction("q", case.rounds - 1), LogicalInit("s", "X", 1)],
            LogicalMeasure("q", case.basis),
            SyndromeExtraction("s", 1),
            LogicalMeasure("s", "X"),
        ]
    else:
        initial = "Z" if case.variant == "h" else case.basis
        program = [LogicalInit("q", initial, 1)]
        if case.rounds > 1:
            program.append(SyndromeExtraction("q", case.rounds - 1))
        if case.variant == "h":
            program.append(TransversalH("q"))
        if case.variant == "signed":
            program.append(LogicalPauli("q", "X", mode="frame"))
        program.append(LogicalMeasure("q", case.basis))
    model = NoiseModel(default=NoiseParameters(*case.probabilities))
    return compiler.compile(program, noise_model=model), model


@dataclass(frozen=True)
class Location:
    location_id: int
    instruction_index: int
    ideal_cut: int
    layer: int
    kind: str
    channel: str
    targets: tuple[int, ...]
    target_position: int
    probability: float
    record_index: int | None
    operation: str
    instruction_tag: str
    source_module: str
    sites: tuple[tuple[str, str], ...]
    epochs: tuple[int | None, ...]

    @property
    def identity_probability(self) -> float:
        return 1 - self.probability

    @property
    def key(self) -> tuple:
        return (
            self.ideal_cut,
            self.layer,
            self.kind,
            self.channel,
            self.targets,
            self.probability,
            self.record_index,
        )


@dataclass(frozen=True)
class Atom:
    atom_id: int
    location_id: int
    alternative: str
    probability: float
    paulis: tuple[tuple[int, str], ...]
    record_index: int | None
    ideal_cut: int


def _site_context(compiled, targets, layer):
    by_wire = {wire: site for site, wire in compiled.physical_qubit_map.items()}
    active = {use.block_id: use.epoch for use in compiled.time_layers[layer].active_use_ids}
    sites = tuple(by_wire[t] for t in targets)
    return sites, tuple(active.get(block) for block, _ in sites)


def scan_noisy(compiled) -> tuple[Location, ...]:
    """Read actual stochastic instructions, aligning them to the ideal circuit."""
    if compiled.noisy_circuit is None or compiled.circuit.without_noise() != compiled.ideal_circuit:
        raise AssertionError("noisy circuit does not preserve the ideal physical instructions")
    ideal = list(compiled.ideal_circuit)
    cursor = layer = raw_cursor = 0
    locations = []

    def add(
        index, cut, kind, channel, targets, position, probability, record, operation, tag, module
    ):
        if not math.isfinite(probability) or not 0 < probability <= 1:
            raise AssertionError("unsupported physical channel probability")
        sites, epochs = _site_context(compiled, targets, layer)
        if kind == "idle":
            module = compiled.time_layers[layer].operation_by_block.get(sites[0][0]) or "WAITING"
        locations.append(
            Location(
                len(locations),
                index,
                cut,
                layer,
                kind,
                channel,
                tuple(targets),
                position,
                probability,
                record,
                operation,
                tag,
                module,
                sites,
                epochs,
            )
        )

    for noisy_index, instruction in enumerate(compiled.circuit):
        name = instruction.name
        targets = tuple(t.value for t in instruction.targets_copy())
        if name in NOISE_GATES:
            (p,) = instruction.gate_args_copy()
            previous = ideal[cursor - 1] if cursor else None
            width = 2 if name == "DEPOLARIZE2" else 1
            if len(targets) % width:
                raise AssertionError("malformed batched physical noise")
            for offset in range(0, len(targets), width):
                site_targets = targets[offset : offset + width]
                if name in {"X_ERROR", "Y_ERROR", "Z_ERROR"}:
                    kind = "reset"
                elif name == "DEPOLARIZE2":
                    kind = "after_2q"
                elif (
                    previous is not None
                    and previous.name in ONE_QUBIT_CLIFFORDS
                    and set(site_targets).issubset({t.value for t in previous.targets_copy()})
                ):
                    # Stim can merge adjacent gate and idle DEPOLARIZE1 with
                    # equal p into one batched instruction. Classify each target.
                    kind = "after_1q"
                else:
                    kind = "idle"
                operation = (
                    previous.name if kind != "idle" and previous is not None else "TICK_IDLE"
                )
                module = previous.tag if kind != "idle" and previous is not None else ""
                add(
                    noisy_index,
                    cursor,
                    kind,
                    name,
                    site_targets,
                    offset // width,
                    p,
                    None,
                    operation,
                    instruction.tag,
                    module,
                )
            continue
        if cursor >= len(ideal):
            raise AssertionError("extra physical instruction")
        expected = ideal[cursor]
        if (
            name != expected.name
            or targets != tuple(t.value for t in expected.targets_copy())
            or instruction.tag != expected.tag
        ):
            raise AssertionError(f"physical instruction mismatch at ideal index {cursor}")
        if name in MEASUREMENTS:
            args = instruction.gate_args_copy()
            if args:
                (p,) = args
                for offset, target in enumerate(targets):
                    add(
                        noisy_index,
                        cursor,
                        "measurement",
                        "RESULT_FLIP",
                        (target,),
                        offset,
                        p,
                        raw_cursor + offset,
                        name,
                        instruction.tag,
                        instruction.tag,
                    )
        raw_cursor += expected.num_measurements
        cursor += 1
        if name == "TICK":
            layer += 1
    if cursor != len(ideal) or raw_cursor != compiled.ideal_circuit.num_measurements:
        raise AssertionError("incomplete physical instruction/record alignment")
    return tuple(locations)


def expected_schedule(compiled, model) -> tuple[tuple, ...]:
    """Derive location keys from ideal gates and use occupancy, not noisy output."""
    ideal = list(compiled.ideal_circuit)
    by_module = {fragment.module_id: fragment for fragment in compiled.fragments}
    by_block = defaultdict(set)
    for (block, _), wire in compiled.physical_qubit_map.items():
        by_block[block].add(wire)
    expected = []
    used = set()
    layer = raw_cursor = 0

    def add(cut, kind, channel, targets, p, record=None):
        if p:
            expected.append((cut, layer, kind, channel, tuple(targets), p, record))

    def idle(cut):
        current = compiled.time_layers[layer]
        for use in current.active_use_ids:
            module = current.operation_by_block.get(use.block_id)
            if module is None:
                p = model.default.idle
            else:
                fragment = by_module[module]
                p = model.resolve(fragment.operation_type, fragment.noise).idle
            for wire in sorted(by_block[use.block_id] - used):
                add(cut, "idle", "DEPOLARIZE1", (wire,), p)

    for index, instruction in enumerate(ideal):
        name = instruction.name
        if name == "TICK":
            idle(index)
            layer += 1
            used.clear()
            continue
        if instruction.tag not in by_module:
            raw_cursor += instruction.num_measurements
            continue
        fragment = by_module[instruction.tag]
        params = model.resolve(fragment.operation_type, fragment.noise)
        targets = tuple(t.value for t in instruction.targets_copy())
        used.update(targets)
        if name in RESETS:
            channel = "Z_ERROR" if name == "RX" else "X_ERROR"
            for wire in targets:
                add(index + 1, "reset", channel, (wire,), params.reset)
        elif name in ONE_QUBIT_CLIFFORDS:
            for wire in targets:
                add(index + 1, "after_1q", "DEPOLARIZE1", (wire,), params.one_qubit)
        elif name == "CX":
            for offset in range(0, len(targets), 2):
                add(
                    index + 1,
                    "after_2q",
                    "DEPOLARIZE2",
                    targets[offset : offset + 2],
                    params.two_qubit,
                )
        elif name in MEASUREMENTS:
            for offset, wire in enumerate(targets):
                add(
                    index,
                    "measurement",
                    "RESULT_FLIP",
                    (wire,),
                    params.measurement,
                    raw_cursor + offset,
                )
        else:
            raise AssertionError(f"unsupported physical operation {name}")
        raw_cursor += instruction.num_measurements
    idle(len(ideal))
    return tuple(expected)


def audit_schedule(compiled, model, locations=None) -> dict:
    """Check physical map geometry and exact per-layer location multiset."""
    locations = scan_noisy(compiled) if locations is None else locations
    coordinates = compiled.ideal_circuit.get_final_qubit_coordinates()
    for block in compiled._compiler.blocks:
        for site in block.layout.data_ids + block.layout.ancilla_ids:
            wire = compiled.physical_qubit_map[block.block_id, site]
            if complex(*coordinates[wire]) != block.position(site):
                raise AssertionError(f"physical qubit map mismatch: {block.block_id}:{site}")
    expected = Counter(expected_schedule(compiled, model))
    observed = Counter(location.key for location in locations)
    if expected != observed:
        missing = list((expected - observed).items())[:8]
        extra = list((observed - expected).items())[:8]
        raise AssertionError(f"fault location mismatch; missing={missing}; extra={extra}")
    if len({loc.location_id for loc in locations}) != len(locations):
        raise AssertionError("duplicate location ID")
    return {
        "locations": len(locations),
        "channels": dict(Counter(loc.channel for loc in locations)),
        "kinds": dict(Counter(loc.kind for loc in locations)),
    }


def atoms_from_locations(locations: tuple[Location, ...]) -> tuple[Atom, ...]:
    atoms = []
    for location in locations:
        if location.channel == "RESULT_FLIP":
            alternatives = ("RESULT",)
        elif location.channel == "DEPOLARIZE2":
            alternatives = TWO_PAULIS
        elif location.channel == "DEPOLARIZE1":
            alternatives = ("X", "Y", "Z")
        else:
            alternatives = (location.channel[0],)
        for alternative in alternatives:
            if alternative == "RESULT":
                # A pre-measurement anticommuting Pauli is physically equivalent
                # on this measured ancilla/retired data, but the table retains
                # RESULT as the actual channel and raw record index.
                pauli = "Z" if location.operation == "MX" else "X"
                paulis = ((location.targets[0], pauli),)
            else:
                paulis = tuple(
                    (wire, pauli)
                    for wire, pauli in zip(location.targets, alternative, strict=True)
                    if pauli != "I"
                )
            atoms.append(
                Atom(
                    len(atoms),
                    location.location_id,
                    alternative,
                    location.probability / len(alternatives),
                    paulis,
                    location.record_index,
                    location.ideal_cut,
                )
            )
    return tuple(atoms)


def annotation_masks(circuit: stim.Circuit) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Parse absolute record parity directly from Stim rec annotations."""
    cursor = 0
    detector_masks = []
    observable_masks = [0] * circuit.num_observables
    for instruction in circuit:
        cursor += instruction.num_measurements
        if instruction.name not in {"DETECTOR", "OBSERVABLE_INCLUDE"}:
            continue
        mask = 0
        for target in instruction.targets_copy():
            if not target.is_measurement_record_target:
                raise AssertionError("unsupported non-record annotation target")
            index = cursor + target.value
            if not 0 <= index < circuit.num_measurements:
                raise AssertionError("bad absolute record index")
            mask ^= 1 << index
        if instruction.name == "DETECTOR":
            detector_masks.append(mask)
        else:
            observable_masks[int(instruction.gate_args_copy()[0])] ^= mask
    return tuple(detector_masks), tuple(observable_masks)


def signature_from_records(raw_mask: int, detector_masks, observable_masks) -> tuple[int, int]:
    return (
        sum(((raw_mask & mask).bit_count() & 1) << i for i, mask in enumerate(detector_masks)),
        sum(((raw_mask & mask).bit_count() & 1) << i for i, mask in enumerate(observable_masks)),
    )


def simulate_atoms(
    compiled, atoms: tuple[Atom, ...], batch_size: int = 512
) -> dict[int, tuple[int, int]]:
    """Batch independent physical Pauli insertions at exact ideal cuts."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    ideal = list(compiled.ideal_circuit)
    detector_masks, observable_masks = annotation_masks(compiled.ideal_circuit)
    by_cut = defaultdict(list)
    for atom in atoms:
        by_cut[atom.ideal_cut].append(atom)
    result = {}
    for cut, group in by_cut.items():
        prefix, suffix = stim.Circuit(), stim.Circuit()
        for instruction in ideal[:cut]:
            prefix.append(instruction)
        for instruction in ideal[cut:]:
            suffix.append(instruction)
        measurement_atoms = [atom for atom in group if atom.record_index is not None]
        for atom in measurement_atoms:
            # A measurement flip edits the reported result, not the physical
            # state after measurement. Split its batched ideal measurement and
            # ask Stim to apply M(1)/MX(1) to exactly that target.
            original = ideal[cut]
            if original.name not in MEASUREMENTS:
                raise AssertionError("measurement atom is not before a measurement")
            sim = stim.FlipSimulator(batch_size=1, num_qubits=compiled.ideal_circuit.num_qubits)
            sim.do(prefix)
            fault_wire = atom.paulis[0][0]
            for target in original.targets_copy():
                one = stim.Circuit()
                one.append(original.name, [target], 1 if target.value == fault_wire else 0)
                sim.do(one)
            for instruction in ideal[cut + 1 :]:
                sim.do(instruction)
            raw_mask = 1 << atom.record_index
            expected = signature_from_records(raw_mask, detector_masks, observable_masks)
            observed = (
                sum(int(bit) << i for i, bit in enumerate(sim.get_detector_flips()[:, 0])),
                sum(int(bit) << i for i, bit in enumerate(sim.get_observable_flips()[:, 0])),
            )
            if expected != observed:
                raise AssertionError(f"Stim reported-bit flip disagrees at {atom.atom_id}")
            result[atom.atom_id] = expected
        group = [atom for atom in group if atom.record_index is None]
        for start in range(0, len(group), batch_size):
            batch = group[start : start + batch_size]
            sim = stim.FlipSimulator(
                batch_size=len(batch), num_qubits=compiled.ideal_circuit.num_qubits
            )
            sim.do(prefix)
            for pauli in "XYZ":
                mask = np.zeros((compiled.ideal_circuit.num_qubits, len(batch)), dtype=bool)
                for shot, atom in enumerate(batch):
                    for wire, error in atom.paulis:
                        if error == pauli:
                            mask[wire, shot] = True
                if mask.any():
                    sim.broadcast_pauli_errors(pauli=pauli, mask=mask)
            sim.do(suffix)
            raw = sim.get_measurement_flips()
            detectors = sim.get_detector_flips()
            observables = sim.get_observable_flips()
            for shot, atom in enumerate(batch):
                raw_mask = sum(int(bit) << i for i, bit in enumerate(raw[:, shot]))
                signature = signature_from_records(raw_mask, detector_masks, observable_masks)
                observed = (
                    sum(int(bit) << i for i, bit in enumerate(detectors[:, shot])),
                    sum(int(bit) << i for i, bit in enumerate(observables[:, shot])),
                )
                if signature != observed:
                    raise AssertionError(
                        f"raw parity and physical detector/observable disagree at {atom.atom_id}"
                    )
                result[atom.atom_id] = signature
    if len(result) != len(atoms):
        raise AssertionError("missing or duplicate physical atom")
    return result


def audit_pair_subset(compiled, atoms, signatures, *, count: int = 128, seed: int = 1729) -> dict:
    """Check a reproducible, explicitly incomplete subset of physical Pauli pairs."""
    if count < 1 or seed < 0:
        raise ValueError("invalid pair audit settings")
    eligible = [atom for atom in atoms if atom.record_index is None]
    by_location = Counter(atom.location_id for atom in eligible)
    possible = len(eligible) * (len(eligible) - 1) // 2 - sum(
        size * (size - 1) // 2 for size in by_location.values()
    )
    if count > possible:
        raise ValueError("pair sample exceeds eligible pairs")
    rng = np.random.default_rng(seed)
    chosen = set()
    while len(chosen) < count:
        i, j = sorted(int(x) for x in rng.choice(len(eligible), 2, replace=False))
        if eligible[i].location_id != eligible[j].location_id:
            chosen.add((i, j))
    pairs = tuple((eligible[i], eligible[j]) for i, j in sorted(chosen))
    cuts = defaultdict(list)
    for shot, pair in enumerate(pairs):
        for atom in pair:
            cuts[atom.ideal_cut].append((shot, atom))
    sim = stim.FlipSimulator(batch_size=count, num_qubits=compiled.ideal_circuit.num_qubits)
    ideal = list(compiled.ideal_circuit)
    for cut in range(len(ideal) + 1):
        for pauli in "XYZ":
            mask = np.zeros((compiled.ideal_circuit.num_qubits, count), dtype=bool)
            for shot, atom in cuts[cut]:
                for wire, error in atom.paulis:
                    if error == pauli:
                        mask[wire, shot] ^= True
            if mask.any():
                sim.broadcast_pauli_errors(pauli=pauli, mask=mask)
        if cut < len(ideal):
            sim.do(ideal[cut])
    detector_masks, observable_masks = annotation_masks(compiled.ideal_circuit)
    raw = sim.get_measurement_flips()
    detectors = sim.get_detector_flips()
    observables = sim.get_observable_flips()
    for shot, (left, right) in enumerate(pairs):
        raw_mask = sum(int(bit) << i for i, bit in enumerate(raw[:, shot]))
        actual = signature_from_records(raw_mask, detector_masks, observable_masks)
        observed = (
            sum(int(bit) << i for i, bit in enumerate(detectors[:, shot])),
            sum(int(bit) << i for i, bit in enumerate(observables[:, shot])),
        )
        expected = tuple(
            a ^ b for a, b in zip(signatures[left.atom_id], signatures[right.atom_id], strict=True)
        )
        if actual != observed or actual != expected:
            raise AssertionError(f"physical fault pair disagrees: {left.atom_id}, {right.atom_id}")
    return {
        "eligible_atom_count": len(eligible),
        "possible_cross_location_pairs": possible,
        "sampled_cross_location_pairs": count,
        "seed": seed,
        "measurement_atoms_excluded": True,
        "complete": False,
    }


def circuit_identity(compiled) -> dict:
    return {
        "source_fingerprint": source_fingerprint(compiled),
        "ideal_sha256": hashlib.sha256(str(compiled.ideal_circuit).encode()).hexdigest(),
        "noisy_sha256": hashlib.sha256(str(compiled.circuit).encode()).hexdigest(),
        "num_detectors": compiled.circuit.num_detectors,
        "num_observables": compiled.circuit.num_observables,
        "num_measurements": compiled.circuit.num_measurements,
        "num_ticks": compiled.circuit.num_ticks,
    }


def audit_signed_reference(compiled, shots: int = 64) -> dict:
    """Check ideal random-gauge samples against signed intended logical labels."""
    if shots < 1:
        raise ValueError("shots must be positive")
    raw = compiled.ideal_circuit.compile_sampler(seed=4471).sample(shots)
    interpreted = compiled.interpreted_measurements(raw)
    intended = np.array([o.expected_value for o in compiled.observables], dtype=bool)
    if interpreted.shape != (shots, len(intended)) or not np.all(interpreted == intended):
        raise AssertionError("signed noiseless logical labels disagree with physical readout")
    detectors, observables = compiled.ideal_circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True
    )
    if detectors.any() or observables.any():
        raise AssertionError("ideal random-gauge sample has deterministic event")
    return {
        "shots": shots,
        "expected_values": intended.tolist(),
        "random_raw_columns": int(np.count_nonzero(np.any(raw != raw[0], axis=0))),
    }


def dem_events(model: stim.DetectorErrorModel) -> tuple[tuple[float, int, int, tuple], ...]:
    """Parse each DEM mechanism, retaining its correlated ^ component structure."""
    events = []
    for instruction in model.flattened():
        if instruction.type != "error":
            continue
        (probability,) = instruction.args_copy()
        components = []
        detector = observable = 0
        for target in (*instruction.targets_copy(), stim.target_separator()):
            if target.is_separator():
                components.append((detector, observable))
                detector = observable = 0
            elif target.is_relative_detector_id():
                detector ^= 1 << target.val
            elif target.is_logical_observable_id():
                observable ^= 1 << target.val
            else:
                raise AssertionError("unsupported DEM target")
        total_detector = total_observable = 0
        for dmask, omask in components:
            total_detector ^= dmask
            total_observable ^= omask
        events.append((probability, total_detector, total_observable, tuple(components)))
    return tuple(events)


def project_signature(
    signature: tuple[int, int], detector_ids: tuple[int, ...], observable_ids: tuple[int, ...]
) -> int:
    detectors, observables = signature
    result = sum(
        ((detectors >> global_id) & 1) << local for local, global_id in enumerate(detector_ids)
    )
    result |= sum(
        ((observables >> global_id) & 1) << (len(detector_ids) + local)
        for local, global_id in enumerate(observable_ids)
    )
    return result


def fourier_table(
    locations: tuple[Location, ...],
    atoms: tuple[Atom, ...],
    signatures: dict[int, tuple[int, int]],
    detector_ids: tuple[int, ...],
    observable_ids: tuple[int, ...],
) -> tuple[float, ...]:
    """Exact categorical-location parity transform on a small selected subset."""
    by_location = defaultdict(list)
    for atom in atoms:
        by_location[atom.location_id].append(
            (
                atom.probability,
                project_signature(signatures[atom.atom_id][:2], detector_ids, observable_ids),
            )
        )
    n = len(detector_ids) + len(observable_ids)
    moments = []
    for probe in range(1 << n):
        value = 1.0
        for location in locations:
            factor = location.identity_probability + sum(
                p * (-1 if (probe & signature).bit_count() & 1 else 1)
                for p, signature in by_location[location.location_id]
            )
            value *= factor
        moments.append(value)
    return tuple(moments)


def fourier_dem(
    events: tuple[tuple[float, int, int, tuple], ...],
    detector_ids: tuple[int, ...],
    observable_ids: tuple[int, ...],
    *,
    local: bool = False,
) -> tuple[float, ...]:
    n = len(detector_ids) + len(observable_ids)
    if local:
        detector_ids = tuple(range(len(detector_ids)))
        observable_ids = tuple(range(len(observable_ids)))
    projected = [
        (p, project_signature((d, o), detector_ids, observable_ids)) for p, d, o, _ in events
    ]
    return tuple(
        math.prod(
            1 - 2 * p if (probe & signature).bit_count() & 1 else 1 for p, signature in projected
        )
        for probe in range(1 << n)
    )


def audit_dem_marginal(
    compiled,
    locations,
    atoms,
    signatures,
    detector_ids: tuple[int, ...] = (0, 1, 2),
    observable_ids: tuple[int, ...] = (0,),
) -> dict:
    """Compare full and exact-view physical distributions, not DEM text rows."""
    from logical_to_stim_converter import DEMOptions

    full = dem_events(compiled.circuit.detector_error_model())
    decomposed = dem_events(
        compiled.make_decoder_view(
            dem_options=DEMOptions(decompose_errors=True)
        ).detector_error_model
    )
    view = compiled.make_decoder_view(
        detector_selector=detector_ids,
        observable_selector=observable_ids,
        dem_options=DEMOptions(),
    )
    local = dem_events(view.detector_error_model)
    a = fourier_table(locations, atoms, signatures, detector_ids, observable_ids)
    b = fourier_dem(full, detector_ids, observable_ids)
    c = fourier_dem(local, detector_ids, observable_ids, local=True)
    d = fourier_dem(decomposed, detector_ids, observable_ids)
    full_difference = max(abs(x - y) for x, y in zip(a, b, strict=True))
    view_difference = max(abs(x - y) for x, y in zip(a, c, strict=True))
    decomposed_difference = max(abs(x - y) for x, y in zip(a, d, strict=True))
    if max(full_difference, view_difference, decomposed_difference) > 2e-9:
        raise AssertionError(
            f"physical table/DEM marginal differs: {full_difference}, {view_difference}"
        )
    return {
        "global_detector_ids": detector_ids,
        "global_observable_ids": observable_ids,
        "full_dem_errors": len(full),
        "view_dem_errors": len(local),
        "full_max_fourier_difference": full_difference,
        "view_max_fourier_difference": view_difference,
        "decomposed_max_fourier_difference": decomposed_difference,
        "full_correlated_components": sum(len(parts) > 1 for _, _, _, parts in full),
        "decomposed_correlated_components": sum(len(parts) > 1 for _, _, _, parts in decomposed),
        "full_hyperedge_components": sum(
            any(d.bit_count() > 2 for d, _ in parts) for _, _, _, parts in full
        ),
    }


def audit_first_order(case: Case, atoms: tuple[Atom, ...], signatures, scale: float = 1e-5) -> dict:
    """Compare each nonzero global signature's derivative at zero noise."""
    if not 0 < scale < 1e-2:
        raise ValueError("scale must be small and positive")
    tiny_case = Case(
        case.distance,
        case.basis,
        case.rounds,
        tuple(p * scale for p in case.probabilities),
        case.variant,
    )
    tiny, _ = build_case(tiny_case)
    dem = dem_events(tiny.circuit.detector_error_model())
    table_weight = defaultdict(float)
    dem_weight = defaultdict(float)
    for atom in atoms:
        signature = signatures[atom.atom_id][:2]
        if signature != (0, 0):
            table_weight[signature] += atom.probability
    for p, detectors, observables, _ in dem:
        signature = detectors, observables
        if signature != (0, 0):
            dem_weight[signature] += p / scale
    difference = {
        key: dem_weight[key] - table_weight[key] for key in set(table_weight) | set(dem_weight)
    }
    maximum = max((abs(v) for v in difference.values()), default=0.0)
    if maximum > 1e-5:
        biggest = sorted(difference.items(), key=lambda item: abs(item[1]), reverse=True)[:5]
        raise AssertionError(f"first-order DEM signature mismatch: {biggest}")
    return {
        "scale": scale,
        "nonzero_signatures": len(difference),
        "max_absolute_coefficient_difference": maximum,
    }
