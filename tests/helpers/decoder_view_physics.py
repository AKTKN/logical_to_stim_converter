"""Independent hand-circuit metadata and DEM characteristic-function checks."""

import numpy as np
import stim

from logical_to_stim_converter import (
    CompiledCircuit,
    DetectorInfo,
    MeasurementInfo,
    MeasurementKey,
    ObservableInfo,
)


def expanded_instructions(circuit):
    for inst in circuit:
        if isinstance(inst, stim.CircuitRepeatBlock):
            for _ in range(inst.repeat_count):
                yield from expanded_instructions(inst.body_copy())
        else:
            yield inst


def physical_instructions(circuit):
    result = stim.Circuit()
    for inst in expanded_instructions(circuit):
        if inst.name not in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            result.append(inst)
    return result


def hand_artifact(circuit):
    """Public metadata only: deliberately has no private compiler/evaluation state."""
    measurements, detectors = [], []
    observables = [set() for _ in range(circuit.num_observables)]
    coordinates = circuit.get_detector_coordinates()
    for inst in expanded_instructions(circuit):
        if inst.name == "M":
            for t in inst.targets_copy():
                i = len(measurements)
                key = MeasurementKey("patch", f"q{t.value}", "readout", i)
                measurements.append(MeasurementInfo(key, i, "q", "Z", "manual", i))
        if inst.name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            parity = tuple(sorted(len(measurements) + t.value for t in inst.targets_copy()))
            if inst.name == "DETECTOR":
                keys = tuple(measurements[i].key for i in parity)
                detectors.append(
                    DetectorInfo(
                        len(detectors),
                        tuple(coordinates[len(detectors)]),
                        parity,
                        keys,
                        "patch",
                        "check",
                        ("patch",),
                        None,
                        (None,),
                        False,
                        "manual",
                        "Z",
                        tuple(sorted({(k.block_id, k.local_id) for k in keys})),
                    )
                )
            else:
                observables[int(inst.gate_args_copy()[0])] ^= set(parity)
    reference = circuit.reference_sample()
    obs = tuple(
        ObservableInfo(
            i,
            f"logical{i}",
            "patch",
            "Z",
            tuple(sorted(p)),
            expected_value=int(np.bitwise_xor.reduce(reference[list(p)])),
        )
        for i, p in enumerate(observables)
    )
    return CompiledCircuit(
        circuit.without_noise(),
        circuit.copy(),
        {("patch", f"q{i}"): i for i in range(circuit.num_qubits)},
        {"q": "patch"},
        tuple(measurements),
        tuple(detectors),
        obs,
        {},
        {},
        (),
        (),
        {},
    )


def mechanisms(dem, detector_ids=None, observable_ids=None):
    """Each ^-separated instruction is ONE correlated Bernoulli variable."""
    dids = tuple(range(dem.num_detectors)) if detector_ids is None else tuple(detector_ids)
    oids = tuple(range(dem.num_observables)) if observable_ids is None else tuple(observable_ids)
    dmap = {g: i for i, g in enumerate(dids)}
    omap = {g: i + len(dids) for i, g in enumerate(oids)}
    result = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        support = set()
        for t in inst.targets_copy():
            if t.is_separator():
                continue
            mapping = dmap if t.is_relative_detector_id() else omap
            if t.val in mapping:
                support.symmetric_difference_update((mapping[t.val],))
        if support:
            result.append((inst.args_copy()[0], tuple(sorted(support))))
    return result


def assert_marginal_equivalent(global_dem, view):
    """Compare exact parity expectations, not counts or independent RNG streams."""
    global_terms = mechanisms(
        global_dem, view.detector_map.global_ids, view.observable_map.global_ids
    )
    local_terms = mechanisms(view.detector_error_model)
    width = len(view.detector_map.global_ids) + len(view.observable_map.global_ids)
    if width <= 10:
        masks = np.array(
            [[bool(i & (1 << j)) for j in range(width)] for i in range(1 << width)], dtype=bool
        )
    else:
        masks = np.random.default_rng(700).integers(0, 2, (96, width), dtype=np.uint8).astype(bool)

    def expectations(terms):
        values = np.ones(len(masks))
        for probability, support in terms:
            odd = np.bitwise_xor.reduce(masks[:, support], axis=1)
            values[odd] *= 1 - 2 * probability
        return values

    np.testing.assert_allclose(
        expectations(global_terms), expectations(local_terms), rtol=1e-12, atol=1e-12
    )
