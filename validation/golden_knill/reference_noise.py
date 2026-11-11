"""Independent primitive noise insertion, active lifetimes and M9 policy.

No converter/stimflow noise classes, rules, layers or metadata are imported.
All channels are appended directly to Stim from the independently authored
protocol moments. The occupied set follows reset-to-readout role lifetimes.
"""

import math
from dataclasses import dataclass, fields

import stim

from .spec import OPERATION_TYPES


@dataclass(frozen=True)
class ReferenceOverride:
    reset: float | None = None
    one_qubit: float | None = None
    two_qubit: float | None = None
    measurement: float | None = None
    idle: float | None = None

    def __post_init__(self):
        for field in fields(self):
            p = getattr(self, field.name)
            if p is not None and (
                isinstance(p, bool)
                or not isinstance(p, (int, float))
                or not math.isfinite(p)
                or not 0 <= p <= 1
            ):
                raise ValueError(f"{field.name}: expected a finite [0,1] probability or None")


@dataclass(frozen=True)
class ReferenceNoise(ReferenceOverride):
    reset: float = 0
    one_qubit: float = 0
    two_qubit: float = 0
    measurement: float = 0
    idle: float = 0

    def __post_init__(self):
        super().__post_init__()
        if any(getattr(self, f.name) is None for f in fields(self)):
            raise ValueError("Global probabilities cannot inherit")


FULL_NOISE = ReferenceNoise(0.01, 0.02, 0.03, 0.04, 0.05)


def resolve_parameters(default, operation, *, type_overrides=None, instance_overrides=None):
    """Resolve each channel instance > primitive type > default; zero is explicit."""
    values = {f.name: getattr(default, f.name) for f in fields(ReferenceNoise)}
    kind = OPERATION_TYPES.get(operation, "LogicalPauli")
    for override in ((type_overrides or {}).get(kind), (instance_overrides or {}).get(operation)):
        if override is not None:
            for name in values:
                value = (
                    override.get(name) if isinstance(override, dict) else getattr(override, name)
                )
                if value is not None:
                    values[name] = value
    return ReferenceNoise(**values)


def add_noise(
    bundle,
    noise=FULL_NOISE,
    *,
    type_overrides=None,
    instance_overrides=None,
    m9_enabled=False,
    p_st=0,
):
    """Insert exact primitive/result/idle channels into the independent schedule.

    Bell-owned A/B ordinary channels are suppressed from their initial data
    reset through final check measurement (inclusive). The independent post-SE
    channels follow the existing final preparation TICK, never a new TICK.
    """
    if not isinstance(noise, ReferenceNoise):
        raise TypeError("noise must be independent ReferenceNoise")
    if type(m9_enabled) is not bool:
        raise ValueError("m9_enabled must be boolean")
    if (
        isinstance(p_st, bool)
        or not isinstance(p_st, (int, float))
        or not math.isfinite(p_st)
        or not 0 <= p_st <= 0.75
    ):
        raise ValueError("p_st must be a finite non-boolean [0,.75] probability")
    result = stim.Circuit()
    for inst in bundle.circuit:
        if inst.name == "QUBIT_COORDS":
            result.append(inst)

    def resolved(operation):
        return resolve_parameters(
            noise, operation, type_overrides=type_overrides, instance_overrides=instance_overrides
        )

    for t, moment in enumerate(bundle.moments):
        suppression = (
            m9_enabled and bundle.resource_first_moment <= t <= bundle.resource_boundary_moment
        )
        for action in moment.actions:
            targets = [bundle.indices[q] for q in action.targets]
            p = (
                ReferenceNoise()
                if suppression and action.operation in ("A.prep", "B.prep")
                else resolved(action.operation)
            )
            args = [p.measurement] if action.gate in ("M", "MX") and p.measurement else []
            result.append(action.gate, targets, args, tag=action.operation)
            if action.gate in ("R", "RX") and p.reset:
                result.append(
                    "X_ERROR" if action.gate == "R" else "Z_ERROR",
                    targets,
                    p.reset,
                    tag=action.operation,
                )
            elif action.gate == "CX" and p.two_qubit:
                result.append("DEPOLARIZE2", targets, p.two_qubit, tag=action.operation)
            elif action.gate in ("H", "S", "S_DAG", "X", "Y", "Z") and p.one_qubit:
                result.append("DEPOLARIZE1", targets, p.one_qubit, tag=action.operation)
        used = moment.used_sites
        for patch in moment.active_patches:
            if suppression and patch in ("A", "B"):
                continue
            # Waiting patches use the global default; only a physical operation
            # operating this patch owns an operation-specific idle override.
            operation = moment.operations.get(patch)
            p = resolved(operation) if operation is not None else noise
            idle = [
                bundle.indices[(patch, q)] for q in bundle.geometry.sites if (patch, q) not in used
            ]
            if idle and p.idle:
                result.append(
                    "DEPOLARIZE1",
                    idle,
                    p.idle,
                    tag=operation if operation is not None else "idle.wait",
                )
        if t < len(bundle.moments) - 1:
            result.append("TICK")
        if m9_enabled and t == bundle.resource_boundary_moment and p_st:
            for patch in ("A", "B"):
                result.append(
                    "DEPOLARIZE1",
                    [bundle.indices[(patch, q)] for q in bundle.geometry.data],
                    p_st,
                    tag=f"resource_post_se:{patch}.prep",
                )
    for inst in bundle.circuit:
        if inst.name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            result.append(inst)
    return result
