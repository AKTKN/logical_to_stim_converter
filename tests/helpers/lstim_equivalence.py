"""Test-only exact experiment comparison; independent of frontend implementation."""

from collections.abc import Mapping
from dataclasses import fields, is_dataclass

import numpy as np
import stimflow as sf
from scipy.sparse import issparse

from logical_to_stim_converter import CircuitCompiler, CodeSpec, LogicalBlock, parse_logical_circuit


def assert_exact(actual, expected):
    """Compare every field, retaining typed scalars, signed flows and exact doubles."""
    assert type(actual) is type(expected), (type(actual), type(expected))
    if isinstance(actual, np.ndarray):
        assert actual.dtype == expected.dtype
        np.testing.assert_array_equal(actual, expected)
    elif issparse(actual):
        assert actual.shape == expected.shape and actual.dtype == expected.dtype
        assert (actual != expected).nnz == 0
    elif is_dataclass(actual):
        for field in fields(actual):
            assert_exact(getattr(actual, field.name), getattr(expected, field.name))
    elif isinstance(actual, Mapping):
        assert tuple(actual) == tuple(expected)
        for key in actual:
            assert_exact(actual[key], expected[key])
    elif isinstance(actual, (tuple, list)):
        assert len(actual) == len(expected)
        for a, b in zip(actual, expected, strict=True):
            assert_exact(a, b)
    elif isinstance(actual, sf.ChunkLoop):
        assert actual.repetitions == expected.repetitions
        assert_exact(actual.chunks, expected.chunks)
    else:
        assert actual == expected


def placed_blocks(distance, count):
    """Direct public constructors, never AST/lowering-derived block objects."""
    code = CodeSpec.rotated_surface(distance)
    return tuple(LogicalBlock.placed(f"P{i}", code, patch_index=i) for i in range(count))


def declarations(distance=3, count=1):
    """Source declarations only; reference operations are authored separately."""
    return f"FORMAT(1)\nCODE sc ROTATED_SURFACE({distance})\n" + "".join(
        f"PATCH P{i} sc index={i}\n" for i in range(count)
    )


def compile_pair(source, operations, *, distance=3, count=1, noise=None, open_outputs=False):
    """Compile independently authored Python first, then the text under test."""
    reference = CircuitCompiler(placed_blocks(distance, count), logical_to_block={}).compile(
        operations, noise_model=noise, allow_open_outputs=open_outputs,
    )
    actual = parse_logical_circuit(source, source_name="equivalence.lstim").compile(
        noise_model=noise, allow_open_outputs=open_outputs,
    )
    return actual, reference


def assert_experiment_equal(actual, reference, *, shots=17, seed=810):
    """Exact circuits/DEMs/public metadata/flows, then same-seed and shared-raw views."""
    for field in fields(actual):
        if not field.name.startswith("_"):
            assert_exact(getattr(actual, field.name), getattr(reference, field.name))
    assert actual.measurement_index_by_key == reference.measurement_index_by_key
    for a, b in [(actual.ideal_circuit, reference.ideal_circuit),
                 (actual.circuit, reference.circuit)]:
        assert a == b
        assert a.detector_error_model() == b.detector_error_model()
        assert a.get_detector_coordinates() == b.get_detector_coordinates()
        assert a.get_final_qubit_coordinates() == b.get_final_qubit_coordinates()
        for name in ("num_qubits", "num_measurements", "num_detectors", "num_observables"):
            assert getattr(a, name) == getattr(b, name)
    for circuit in (actual, reference):
        circuit.validate_metadata()
        for fragment in circuit.fragments:
            fragment.verify()
    raw = actual.circuit.compile_sampler(seed=seed).sample(shots)
    separately_sampled = reference.circuit.compile_sampler(seed=seed).sample(shots)
    np.testing.assert_array_equal(raw, separately_sampled)
    a_events, a_obs = actual.circuit.compile_m2d_converter().convert(
        measurements=raw, separate_observables=True,
    )
    b_events, b_obs = reference.circuit.compile_m2d_converter().convert(
        measurements=separately_sampled, separate_observables=True,
    )
    np.testing.assert_array_equal(a_events, b_events)
    np.testing.assert_array_equal(a_obs, b_obs)
    a_view, b_view = actual.make_decoder_view(), reference.make_decoder_view()
    assert_exact(a_view, b_view)
    assert_exact(a_view.inputs_from_raw(raw), b_view.inputs_from_raw(raw))
    np.testing.assert_array_equal(a_view.events_from_raw(raw), a_events)
    np.testing.assert_array_equal(a_view.observable_flips_from_raw(raw), a_obs)
    return raw
