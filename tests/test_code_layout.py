"""Algebra and geometry checks independent of circuit assembly."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest
import stim

from logical_to_stim_converter.core.code_spec import CodeSpec, gf2_rank
from logical_to_stim_converter.core.physical_layout import PhysicalLayout


@pytest.mark.parametrize("d", [3, 5])
def test_code_algebra(d):
    code = CodeSpec.rotated_surface(d)
    assert (code.n, code.k, code.d) == (d * d, 1, d)
    assert code.H_X.shape == code.H_Z.shape == ((d * d - 1) // 2, d * d)
    assert gf2_rank(code.H_X) + gf2_rank(code.H_Z) == d * d - 1
    assert not np.any((code.H_X @ code.H_Z.T) % 2)
    assert not np.any((code.H_X @ code.L_Z.T) % 2)
    assert not np.any((code.H_Z @ code.L_X.T) % 2)
    assert ((code.L_X @ code.L_Z.T) % 2).tolist() == [[1]]
    x = stim.PauliString("".join("X" if b else "_" for b in code.L_X[0]))
    z = stim.PauliString("".join("Z" if b else "_" for b in code.L_Z[0]))
    assert not x.commutes(z)
    assert x.weight == z.weight == d
    with pytest.raises(ValueError):
        code.H_X[0, 0] = 1
    with pytest.raises(ValueError):
        code.H_X.setflags(write=True)
    with pytest.raises(FrozenInstanceError):
        code.d = 7
    with pytest.raises(TypeError):
        code.metadata["bad"] = "bad"


@pytest.mark.parametrize("distance", [0, 1, 2, 4, 3.0, True])
def test_bad_distance(distance):
    with pytest.raises(ValueError):
        CodeSpec.rotated_surface(distance)


def test_bad_specs():
    code = CodeSpec.rotated_surface(3)
    for key, value in [
        ("H_X", [[2] * 9]),
        ("L_X", np.zeros((1, 9))),
        ("H_X", np.zeros((4, 9))),
        ("L_Z", np.eye(9)),
        ("k", 2),
    ]:
        with pytest.raises(ValueError):
            replace(code, **{key: value})
    corrupted = code.H_X.copy()
    corrupted[0, 8] ^= 1
    with pytest.raises(ValueError, match="commute"):
        replace(code, H_X=corrupted)
    # This matrix has real rank 3 but GF(2) rank 2.
    assert gf2_rank([[1, 1, 0], [1, 0, 1], [0, 1, 1]]) == 2


@pytest.mark.parametrize("d", [3, 5])
def test_layout(d):
    code = CodeSpec.rotated_surface(d)
    layout = PhysicalLayout.rotated_surface(code)
    assert len(layout.data_ids) == d * d
    assert len(layout.ancilla_ids) == d * d - 1
    assert len(set(layout.coordinates.values())) == 2 * d * d - 1
    assert {len(c.support) for c in layout.checks} == {2, 4}
    layout.validate_code(code)
    assert layout.data_column("D1") == 0
    with pytest.raises(KeyError):
        layout.data_column("X1")
    expected_order = {
        "X": [-1 + 1j, -1 - 1j, 1 + 1j, 1 - 1j],
        "Z": [-1 + 1j, 1 + 1j, -1 - 1j, 1 - 1j],
    }
    for index, layer in enumerate(layout.cnot_layers):
        used = [q for pair in layer for q in pair]
        assert len(used) == len(set(used))
        for control, target in layer:
            anc = control if control.startswith("X") else target
            data = target if control.startswith("X") else control
            check = layout.check_for_ancilla(anc)
            assert (control == anc) == (check.basis == "X")
            assert (
                layout.coordinates[data] - layout.coordinates[anc]
                == expected_order[check.basis][index]
            )


def test_distance_three_reference():
    # Explicit supports from surface-sim's pinned standard rotated layout (D1 southwest).
    layout = PhysicalLayout.rotated_surface(CodeSpec.rotated_surface(3))
    assert {c.check_id: set(c.support) for c in layout.checks} == {
        "X1": {"D1", "D2"},
        "X2": {"D2", "D3", "D5", "D6"},
        "X3": {"D4", "D5", "D7", "D8"},
        "X4": {"D8", "D9"},
        "Z1": {"D1", "D2", "D4", "D5"},
        "Z2": {"D3", "D6"},
        "Z3": {"D4", "D7"},
        "Z4": {"D5", "D6", "D8", "D9"},
    }
