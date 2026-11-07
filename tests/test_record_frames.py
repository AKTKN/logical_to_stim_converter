"""External linear corrections edit copies of records, never the physical experiment."""

from dataclasses import replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter import GF2Map, apply_record_flips
from logical_to_stim_converter.decoding import DecoderViewError, SourceMismatchError
from tests.helpers.decoder_view_physics import hand_artifact


def test_sparse_and_dense_gf2_maps_are_exact_and_immutable():
    matrix = np.random.default_rng(82).integers(0, 2, (300, 5), dtype=np.uint8)
    values = np.random.default_rng(83).integers(0, 2, (64, 300), dtype=np.uint8)
    expected = values.astype(np.int64) @ matrix.astype(np.int64) % 2
    transform = GF2Map.from_matrix(matrix)
    assert np.array_equal(transform.apply(values), expected)
    assert np.array_equal(transform.apply(values.astype(bool)), expected)
    assert np.array_equal(
        GF2Map(300, (tuple(range(300)),)).apply(np.ones((1, 300), bool)), [[False]]
    )
    matrix[:] = 0
    copy = transform.incidence_matrix
    copy.data[:] = 0
    assert np.array_equal(transform.apply(values), expected)
    assert GF2Map(0, ((), ())).apply(np.zeros((3, 0), bool)).shape == (3, 2)
    assert GF2Map(7, ()).apply(np.zeros((0, 7), bool)).shape == (0, 0)


def test_generic_map_agrees_with_explicit_physical_pauli_execution():
    source = hand_artifact(
        stim.Circuit("""
        R 0
        H 0
        H 0
        M 0
        DETECTOR(0, 0, 0) rec[-1]
        OBSERVABLE_INCLUDE(0) rec[-1]
    """)
    )
    view = source.make_decoder_view()
    # At the middle boundary H X H = Z (no record flip), H Z H = X (flip).
    record_map = view.record_flip_map(("physical_X", "physical_Z"), [[0], [1]])
    bits = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.uint8)
    raw = source.circuit.compile_sampler(seed=84).sample(4)
    before = raw.copy()
    corrected = record_map.apply(raw, bits, source_fingerprint=view.source_fingerprint)
    physical = []
    for x, z in bits:
        circuit = stim.Circuit("R 0\nH 0")
        if x:
            circuit.append("X", [0])
        if z:
            circuit.append("Z", [0])
        circuit += stim.Circuit("H 0\nM 0")
        physical.append(circuit.compile_sampler(seed=85).sample(1)[0])
    assert np.array_equal(corrected, physical)
    assert np.array_equal(view.events_from_raw(corrected), bits[:, 1:2])
    assert np.array_equal(view.observable_flips_from_raw(corrected), bits[:, 1:2])
    assert np.array_equal(raw, before)
    assert np.array_equal(
        record_map.apply(raw, bits, source_fingerprint=view.source_fingerprint), corrected
    )
    with pytest.raises(SourceMismatchError):
        record_map.apply(raw, bits, source_fingerprint="different-physical-source")
    with pytest.raises(DecoderViewError):
        record_map.apply(raw, bits[:1], source_fingerprint=view.source_fingerprint)
    with pytest.raises(DecoderViewError):
        view.record_flip_map(("X", "Z"), np.zeros((2, 3), bool))
    with pytest.raises(DecoderViewError):
        replace(record_map, input_ids=("X", "X"))


def test_record_xor_masks_copy_broadcast_and_validate():
    raw = np.array([[0, 1, 0], [1, 1, 1]], dtype=np.uint8)
    before = raw.copy()
    assert np.array_equal(apply_record_flips(raw, [1, 0, 1]), [[1, 1, 1], [0, 1, 0]])
    assert np.array_equal(apply_record_flips(raw, np.zeros_like(raw)), raw)
    assert np.array_equal(raw, before)
    for bad in ([2, 0, 0], [0, 0], np.zeros((3, 3), bool), np.zeros((2, 3, 1), bool)):
        with pytest.raises(DecoderViewError):
            apply_record_flips(raw, bad)


@pytest.mark.parametrize("bad", ["size", "index", "duplicate", "matrix", "float"])
def test_bad_gf2_maps_are_rejected(bad):
    with pytest.raises(DecoderViewError):
        if bad == "size":
            GF2Map(-1, ())
        elif bad == "index":
            GF2Map(2, ((2,),))
        elif bad == "duplicate":
            GF2Map(2, ((1, 1),))
        elif bad == "matrix":
            GF2Map.from_matrix([1, 0])
        else:
            GF2Map.from_matrix(np.zeros((2, 2)))
