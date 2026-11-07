"""Code orientation and physical Pauli utilities; coordinates never move states."""

import stim
import stimflow as sf

from .logical_block import LogicalBlock


def validate_orientation(orientation: int) -> None:
    if type(orientation) is not int or orientation not in (0, 1):
        raise ValueError("Rotated code orientation must be 0 or 1")


def rotate(position: complex, distance: int, quarter_turns: int) -> complex:
    """Rotate a template coordinate counterclockwise about the patch center."""
    for _ in range(quarter_turns % 4):
        position = complex(2 * distance - position.imag, position.real)
    return position


def frame_position(block: LogicalBlock, local_id: str, orientation: int) -> complex:
    validate_orientation(orientation)
    return block.origin + rotate(block.layout.coordinates[local_id], block.code.d, -orientation)


def transformed_pauli(
    pauli: sf.PauliMap, circuit: stim.Circuit, q2i: dict[complex, int], *, inverse: bool = False
):
    """Use Stim's signed physical conjugation, never a second flow simulator."""
    ps = pauli.to_stim_pauli_string(q2i)
    ps += stim.PauliString(max(q2i.values(), default=-1) + 1 - len(ps))
    result = ps.before(circuit) if inverse else ps.after(circuit)
    i2q = {i: q for q, i in q2i.items()}
    out = sf.PauliMap(
        {i2q[i]: "_XYZ"[result[i]] for i in range(len(result)) if result[i]},
        obs_name=pauli.obs_name,
    )
    return out, result.sign == -1
