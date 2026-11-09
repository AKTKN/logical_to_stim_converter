"""Opt-in M9 noise through direct Python and the unchanged three-cycle LSTIM file."""

import argparse
import json
from pathlib import Path

from logical_to_stim_converter import NoiseModel, ResourcePreparationNoise

try:
    from .lstim_equivalence import compare_sample, python_knill_reference
except ImportError:
    from lstim_equivalence import compare_sample, python_knill_reference


def main():
    """Compare one paired experiment with the existing external restricted decoder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p", type=float, default=.001, help="ordinary background probability")
    parser.add_argument("--p-st", type=float, default=.003,
                        help="post-SE data depolarization in [0, 0.75] (DEM-compatible policy)")
    parser.add_argument("--shots", type=int, default=32)
    parser.add_argument("--seed", type=int, default=929)
    args = parser.parse_args()
    try:
        policy = ResourcePreparationNoise(enabled=True, p_st_transversal=args.p_st)
    except ValueError as ex:
        parser.error(str(ex))
    if args.shots <= 0:
        parser.error("shots must be positive")
    noise = NoiseModel(default=NoiseModel.uniform_depolarizing(args.p).default,
                       resource_preparation=policy)
    # The helper explicitly authors BindPatch/LogicalInit/KnillEC/SE/Measure
    # operations; it never derives them from a parsed source or lowering result.
    direct = python_knill_reference(noise)
    source = Path(__file__).with_name("lstim") / "three_patch_knill_d3.lstim"
    report = compare_sample(source, direct, noise=noise, shots=args.shots, seed=args.seed)
    boundaries = direct.resource_preparation_boundaries
    report["resource_preparation"] = dict(
        enabled=True, p_st_transversal=args.p_st, preparations=len(boundaries)//2,
        target_locations=sum(len(direct.circuit[b.channel_instruction].targets_copy())
                             for b in boundaries if b.channel_instruction is not None),
        incoming_hypothesis="before post-SE data channels",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
