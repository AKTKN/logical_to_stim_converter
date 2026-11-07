"""Immutable selections of one physical experiment, with exact Stim re-extraction."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from types import MappingProxyType

import numpy as np
import stim

from .errors import (
    DecoderViewError,
    DEMConstructionError,
    SourceMismatchError,
    UndefinedObservableError,
    UnsupportedProjectionError,
)
from .records import GF2Map, RecordFlipMap, apply_record_flips, binary_batch, ordered_ids
from .selectors import DetectorSelector


@dataclass(frozen=True)
class IndexMap:
    global_size: int
    global_ids: tuple[int, ...]

    def __post_init__(self):
        if type(self.global_size) is not int or self.global_size < 0:
            raise DecoderViewError("IndexMap global_size must be a nonnegative integer")
        object.__setattr__(
            self, "global_ids", ordered_ids(self.global_ids, self.global_size, "index")
        )

    @property
    def local_to_global(self):
        return self.global_ids

    @property
    def global_to_local(self):
        return MappingProxyType({g: i for i, g in enumerate(self.global_ids)})

    @property
    def local_ids(self):
        return tuple(range(len(self.global_ids)))

    def project(self, values):
        return binary_batch(values, self.global_size)[:, self.global_ids].copy()


@dataclass(frozen=True)
class DEMOptions:
    """Exact Stim options only. Decomposition retains correlated ^ components."""

    decompose_errors: bool = False
    flatten_loops: bool = False

    def __post_init__(self):
        if type(self.decompose_errors) is not bool or type(self.flatten_loops) is not bool:
            raise DecoderViewError("DEM options must be booleans")


@dataclass(frozen=True)
class SelectionAudit:
    selector: str
    cross_region_policy: str
    requested_detector_ids: tuple[int, ...]
    omitted_detector_ids: tuple[int, ...]
    crossing_detector_ids: tuple[int, ...]
    region_block_ids: tuple[str, ...]
    region_stage_ids: tuple[str | None, ...]


@dataclass(frozen=True)
class DecoderInputs:
    source_fingerprint: str
    detection_events: np.ndarray
    observable_flips: np.ndarray
    records: np.ndarray


def _freeze_circuit(circuit):
    """Snapshot exact arguments/targets; Stim text is not a lossless float format."""
    return tuple(
        ("REPEAT", inst.repeat_count, _freeze_circuit(inst.body_copy()), inst.tag)
        if isinstance(inst, stim.CircuitRepeatBlock)
        else (inst.name, tuple(inst.gate_args_copy()), tuple(inst.targets_copy()), inst.tag)
        for inst in circuit
    )


def _thaw_circuit(snapshot):
    circuit = stim.Circuit()
    for name, args, targets, tag in snapshot:
        if name == "REPEAT":
            circuit.append(stim.CircuitRepeatBlock(args, _thaw_circuit(targets), tag=tag))
        else:
            circuit.append(name, targets, args, tag=tag)
    return circuit


def _freeze_dem(model):
    """Keep exact double probabilities on Windows as well as Linux."""
    return tuple(
        ("repeat", inst.repeat_count, _freeze_dem(inst.body_copy()))
        if isinstance(inst, stim.DemRepeatBlock)
        else (inst.type, tuple(inst.args_copy()), tuple(inst.targets_copy()), inst.tag)
        for inst in model
    )


def _thaw_dem(snapshot):
    model = stim.DetectorErrorModel()
    for instruction in snapshot:
        if instruction[0] == "repeat":
            _, count, body = instruction
            model.append(stim.DemRepeatBlock(count, _thaw_dem(body)))
        else:
            name, args, targets, tag = instruction
            model.append(name, args, targets, tag=tag)
    return model


def source_fingerprint(compiled):
    """Content identity (schema v2) covering both physical circuits and public metadata."""
    metadata = {
        name: [asdict(v) for v in getattr(compiled, name)]
        for name in (
            "measurements",
            "detectors",
            "observables",
            "preparations",
            "readouts",
            "relocation_history",
            "ancestry_events",
        )
    }
    metadata["sites"] = sorted(compiled.physical_qubit_map.items())
    metadata["locations"] = sorted(compiled.logical_to_block.items())
    metadata["dependencies"] = sorted(compiled.preparation_dependencies.items())
    metadata["operations"] = [
        (f.module_id, f.operation_type, f.block_ids, f.orientations_before, f.stage)
        for f in compiled.fragments
    ]
    text = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(
        (
            "decoder-view-v2\n"
            + stim.__version__
            + "\n"
            + repr(_freeze_circuit(compiled.ideal_circuit))
            + "\n"
            + repr(_freeze_circuit(compiled.circuit))
            + "\n"
            + text
        ).encode()
    ).hexdigest()


def _instructions(circuit):
    """Expand repeat occurrences without dropping SHIFT_COORDS or changing gates."""
    for inst in circuit:
        if isinstance(inst, stim.CircuitRepeatBlock):
            body = inst.body_copy()
            for _ in range(inst.repeat_count):
                yield from _instructions(body)
        else:
            yield inst


def _parities(circuit):
    cursor = 0
    detectors, observables = [], [set() for _ in range(circuit.num_observables)]
    for inst in _instructions(circuit):
        cursor += inst.num_measurements
        if inst.name not in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            continue
        parity = set()
        for t in inst.targets_copy():
            i = cursor + t.value
            if not t.is_measurement_record_target or not 0 <= i < cursor:
                raise DecoderViewError("Invalid source annotation record")
            parity.symmetric_difference_update((i,))
        if inst.name == "DETECTOR":
            detectors.append(tuple(sorted(parity)))
        else:
            observables[int(inst.gate_args_copy()[0])] ^= parity
    return tuple(detectors), tuple(tuple(sorted(p)) for p in observables)


def _validate_source(compiled):
    circuit = compiled.circuit
    for name, size in (
        ("measurements", circuit.num_measurements),
        ("detectors", circuit.num_detectors),
        ("observables", circuit.num_observables),
    ):
        values = getattr(compiled, name)
        if len(values) != size or tuple(v.index for v in values) != tuple(range(size)):
            raise DecoderViewError(f"Missing or inconsistent global {name} metadata")
    if len({m.key for m in compiled.measurements}) != circuit.num_measurements:
        raise DecoderViewError("Duplicate measurement keys")
    dets, obs = _parities(circuit)
    if _parities(compiled.ideal_circuit) != (dets, obs):
        raise DecoderViewError("Ideal/physical source annotations disagree")
    coordinates = circuit.get_detector_coordinates()
    sites = set(compiled.physical_qubit_map)
    for d, parity in zip(compiled.detectors, dets, strict=True):
        if (
            d.measurement_indices != parity
            or d.measurement_keys != tuple(compiled.measurements[i].key for i in parity)
            or d.coordinates != tuple(coordinates[d.index])
            or d.supporting_block_ids != tuple(sorted({k.block_id for k in d.measurement_keys}))
            or set(d.source_stage_ids) != {compiled.measurements[i].stage_id for i in parity}
            or d.basis not in ("X", "Z")
            or not d.anchor_module_id
            or not d.physical_support
            or not set(d.physical_support) <= sites
        ):
            raise DecoderViewError("Missing or inconsistent detector provenance")
    if any(o.measurement_indices != parity for o, parity in zip(compiled.observables, obs)):
        raise DecoderViewError("Observable parity metadata disagrees with circuit")


def _select(selector, values, name):
    if selector is None:
        return tuple(range(len(values)))
    if callable(selector):
        return tuple(v.index for v in values if selector(v))
    return ordered_ids(selector, len(values), name)


def _observable_ids(compiled, selector):
    if selector is not None and not callable(selector):
        resolved = []
        for value in selector:
            if isinstance(value, str):
                matches = [o.index for o in compiled.observables if o.logical_id == value]
                if not matches:
                    raise UndefinedObservableError(
                        f"{value!r} has no reliable observable; "
                        "random Bell readouts are raw records"
                    )
                (value,) = matches
            resolved.append(value)
        selector = resolved
    result = _select(selector, compiled.observables, "observable")
    if any(compiled.observables[i].expected_value not in (0, 1) for i in result):
        raise UndefinedObservableError("Requested observable is not deterministically defined")
    return result


def _annotation_circuit(source, detectors, observable_ids):
    """Place selected detectors at the end to honor arbitrary requested order.

    All record offsets are derived from global indices. Absolute coordinates are
    translated back through the retained SHIFT_COORDS offset. Observable updates
    stay at their original positions, with IDs remapped contiguously.
    """
    result = stim.Circuit()
    observable_map = {g: i for i, g in enumerate(observable_ids)}
    shift = []
    detector_tags = []
    for inst in _instructions(source):
        if inst.name == "DETECTOR":
            detector_tags.append(inst.tag)
            continue
        if inst.name == "SHIFT_COORDS":
            args = inst.gate_args_copy()
            shift.extend([0] * max(0, len(args) - len(shift)))
            for i, value in enumerate(args):
                shift[i] += value
        if inst.name == "OBSERVABLE_INCLUDE":
            global_id = int(inst.gate_args_copy()[0])
            if global_id in observable_map:
                result.append(
                    inst.name, inst.targets_copy(), observable_map[global_id], tag=inst.tag
                )
        else:
            result.append(inst)
    for d in detectors:
        coords = [v - (shift[i] if i < len(shift) else 0) for i, v in enumerate(d.coordinates)]
        result.append(
            "DETECTOR",
            [stim.target_rec(i - source.num_measurements) for i in d.measurement_indices],
            coords,
            tag=detector_tags[d.index],
        )
    for local_id in range(len(observable_ids)):
        result.append("OBSERVABLE_INCLUDE", [], local_id)
    return result


@dataclass(frozen=True)
class DecoderView:
    """A content-addressed snapshot. Public Stim objects are returned as copies.

    Construct with make_decoder_view or CompiledCircuit.make_decoder_view.
    Full raw records are always required for parity reconstruction; record
    selection only controls the records projected for a consumer.
    """

    source_fingerprint: str
    detector_map: IndexMap
    observable_map: IndexMap
    measurement_map: IndexMap
    detectors: tuple
    observables: tuple
    measurements: tuple
    audit: SelectionAudit
    dem_options: DEMOptions
    detector_record_map: GF2Map
    observable_record_map: GF2Map
    _source_instructions: tuple = field(repr=False)
    _circuit_instructions: tuple = field(repr=False)
    _dem_instructions: tuple = field(repr=False)
    _reference_bytes: bytes = field(repr=False)

    @property
    def schema_version(self):
        return "decoder-view-v2"

    @property
    def source_circuit(self):
        return _thaw_circuit(self._source_instructions)

    @property
    def circuit(self):
        return _thaw_circuit(self._circuit_instructions)

    @property
    def detector_error_model(self):
        return _thaw_dem(self._dem_instructions)

    @property
    def reference_sample(self):
        return np.frombuffer(self._reference_bytes, dtype=np.bool_)

    def assert_source(self, compiled):
        self._check_fingerprint(source_fingerprint(compiled))

    def _check_fingerprint(self, fingerprint):
        if fingerprint is not None and fingerprint != self.source_fingerprint:
            raise SourceMismatchError(
                "Decoder view belongs to a different circuit/metadata snapshot"
            )

    def project_detection_events(self, global_events, *, source_fingerprint=None):
        self._check_fingerprint(source_fingerprint)
        return self.detector_map.project(global_events)

    def project_observable_flips(self, global_flips, *, source_fingerprint=None):
        self._check_fingerprint(source_fingerprint)
        return self.observable_map.project(global_flips)

    def project_raw_measurements(self, global_raw, *, source_fingerprint=None):
        self._check_fingerprint(source_fingerprint)
        return self.measurement_map.project(global_raw)

    def _reference(self, reference_sample):
        ref = self.reference_sample if reference_sample is None else np.asarray(reference_sample)
        if ref.ndim != 1:
            raise DecoderViewError("Reference sample must be a global raw-record vector")
        ref = binary_batch(ref[None, :], self.measurement_map.global_size, "reference sample")
        if reference_sample is not None:
            baseline = self.reference_sample[None, :]
            for transform in (self.detector_record_map, self.observable_record_map):
                if not np.array_equal(transform.apply(ref), transform.apply(baseline)):
                    raise DecoderViewError("Reference sample disagrees with noiseless parity signs")
        return ref

    def events_from_raw(self, global_raw, *, reference_sample=None, source_fingerprint=None):
        self._check_fingerprint(source_fingerprint)
        return self.detector_record_map.apply(global_raw) ^ self.detector_record_map.apply(
            self._reference(reference_sample)
        )

    def observable_flips_from_raw(
        self, global_raw, *, reference_sample=None, source_fingerprint=None
    ):
        self._check_fingerprint(source_fingerprint)
        return self.observable_record_map.apply(global_raw) ^ self.observable_record_map.apply(
            self._reference(reference_sample)
        )

    def update_detection_events(self, global_events, record_flips):
        """Project original global events, then apply selected incidence-map flips."""
        events = self.project_detection_events(global_events)
        flips = self.detector_record_map.apply(record_flips)
        if len(events) != len(flips):
            raise DecoderViewError("Events and record flips have different shot counts")
        return events ^ flips

    def inputs_from_raw(self, global_raw, *, record_flips=None, source_fingerprint=None):
        self._check_fingerprint(source_fingerprint)
        raw = binary_batch(global_raw, self.measurement_map.global_size)
        if record_flips is not None:
            raw = apply_record_flips(raw, record_flips)
        arrays = (
            self.events_from_raw(raw),
            self.observable_flips_from_raw(raw),
            self.project_raw_measurements(raw),
        )
        arrays = tuple(np.frombuffer(a.tobytes(), dtype=np.bool_).reshape(a.shape) for a in arrays)
        return DecoderInputs(self.source_fingerprint, *arrays)

    def record_flip_map(self, input_ids, matrix):
        """Bind an external (correction_bits, global_records) binary map to this source."""
        transform = GF2Map.from_matrix(matrix)
        if len(transform.supports) != self.measurement_map.global_size:
            raise DecoderViewError("Correction map output must cover all global raw records")
        return RecordFlipMap(self.source_fingerprint, tuple(input_ids), transform)


def make_decoder_view(
    compiled,
    *,
    detector_selector=None,
    observable_selector=None,
    measurement_selector=None,
    cross_region_policy="retain",
    model_source="physical_circuit",
    dem_options=DEMOptions(),
    expected_source_fingerprint=None,
):
    """Re-extract a detector/observable marginal without changing physical noise.

    Sequences specify exact local order; callbacks receive public metadata.
    Cross-region means multiple supporting blocks or contributing stage IDs.
    retain keeps selected crossings, omit removes them, joint keeps them and
    records the combined scope. No policy changes a gate, raw record, or fault.
    """
    if model_source != "physical_circuit":
        raise UnsupportedProjectionError("Only physical-circuit re-extraction is supported")
    if cross_region_policy not in ("retain", "omit", "joint"):
        raise DecoderViewError("Cross-region policy must be retain, omit, or joint")
    if not isinstance(dem_options, DEMOptions):
        raise UnsupportedProjectionError(
            "Use exact DEMOptions; approximation modes are unsupported"
        )
    _validate_source(compiled)
    fingerprint = source_fingerprint(compiled)
    if expected_source_fingerprint is not None and expected_source_fingerprint != fingerprint:
        raise SourceMismatchError("Requested source fingerprint disagrees")
    requested = _select(detector_selector, compiled.detectors, "detector")
    crossing = tuple(
        i
        for i in requested
        if len(compiled.detectors[i].supporting_block_ids) > 1
        or compiled.detectors[i].crosses_decoder_boundary
    )
    omitted = crossing if cross_region_policy == "omit" else ()
    omitted_set = set(omitted)
    ids = tuple(i for i in requested if i not in omitted_set)
    obs_ids = _observable_ids(compiled, observable_selector)
    if measurement_selector is not None and not callable(measurement_selector):
        keys = compiled.measurement_index_by_key
        measurement_selector = tuple(keys[v] if v in keys else v for v in measurement_selector)
    record_ids = _select(measurement_selector, compiled.measurements, "measurement")
    detectors = tuple(compiled.detectors[i] for i in ids)
    observables = tuple(compiled.observables[i] for i in obs_ids)
    source = compiled.circuit.copy()
    selected = _annotation_circuit(source, detectors, obs_ids)
    try:
        dem = selected.detector_error_model(**asdict(dem_options))
    except ValueError as ex:
        raise DEMConstructionError(f"Exact Stim DEM extraction failed: {ex}") from ex
    if isinstance(detector_selector, DetectorSelector):
        description = repr(detector_selector)
    elif callable(detector_selector):
        name = getattr(detector_selector, "__qualname__", type(detector_selector).__name__)
        description = f"callback:{name}"
    else:
        description = repr(requested)
    audit = SelectionAudit(
        description,
        cross_region_policy,
        requested,
        omitted,
        crossing,
        tuple(sorted({b for d in detectors for b in d.supporting_block_ids})),
        tuple(
            sorted(
                {s for d in detectors for s in d.source_stage_ids},
                key=lambda s: (s is not None, s or ""),
            )
        ),
    )
    return DecoderView(
        fingerprint,
        IndexMap(source.num_detectors, ids),
        IndexMap(source.num_observables, obs_ids),
        IndexMap(source.num_measurements, record_ids),
        detectors,
        observables,
        tuple(compiled.measurements[i] for i in record_ids),
        audit,
        dem_options,
        GF2Map(source.num_measurements, tuple(d.measurement_indices for d in detectors)),
        GF2Map(source.num_measurements, tuple(o.measurement_indices for o in observables)),
        _freeze_circuit(source),
        _freeze_circuit(selected),
        _freeze_dem(dem),
        source.reference_sample().tobytes(),
    )


def observable_local_views(compiled, *, observable_selector=None, region_selector=None, **options):
    """One view per reliable observable, using conservative physical interaction components.

    Seeds include every block in the observable's raw parity and its output block.
    Actual CNOTs and relocations join components (also through retired blocks).
    A region_selector(observable_info) callback may override detector membership.
    This selection example supplies no decoder or guarantee of optimal locality.
    """
    graph = {b: {b} for b, _ in compiled.physical_qubit_map}
    edges = [f.block_ids for f in compiled.fragments if f.operation_type == "TransversalCNOT"]
    edges += [(r.source_block_id, r.output_block_id) for r in compiled.relocation_history]
    for edge in edges:
        connected = set().union(*(graph[b] for b in edge))
        for b in connected:
            graph[b] = set(connected)
    result = []
    for i in _observable_ids(compiled, observable_selector):
        o = compiled.observables[i]
        seeds = {o.block_id} | {
            compiled.measurements[j].key.block_id for j in o.measurement_indices
        }
        blocks = set().union(*(graph[b] for b in seeds))
        selector = (
            DetectorSelector(block_ids=tuple(sorted(blocks)), block_membership="strict")
            if region_selector is None
            else region_selector(o)
        )
        result.append(
            make_decoder_view(
                compiled, detector_selector=selector, observable_selector=(i,), **options
            )
        )
    return tuple(result)
