"""Stim standard generator: semantic oracle with a different physical schedule."""

import stim


def reflect(coordinate):
    """Occupied Stim coordinates -> independently chosen golden coordinates."""
    x, y = coordinate
    return y, x


def build_standard(distance, basis, *, common_noise=False):
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis.lower()}",
        distance=distance,
        rounds=3,
        after_reset_flip_probability=0.01 if common_noise else 0,
        before_measure_flip_probability=0.01 if common_noise else 0,
    )
