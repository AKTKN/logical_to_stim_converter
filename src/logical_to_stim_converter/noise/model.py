"""Memory noise settings: instance > operation type > global defaults."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from types import MappingProxyType

import stimflow as sf

from ..core.lifecycle import BlockUseId


@dataclass(frozen=True)
class NoiseOverride:
    """None inherits a channel; an explicit zero disables the inherited channel."""

    reset: float | None = None
    one_qubit: float | None = None
    two_qubit: float | None = None
    measurement: float | None = None
    idle: float | None = None

    def __post_init__(self) -> None:
        for f in fields(self):
            p = getattr(self, f.name)
            if p is not None and (
                not isinstance(p, (int, float))
                or isinstance(p, bool)
                or not math.isfinite(p)
                or not 0 <= p <= 1
            ):
                raise ValueError(f"{f.name} must be a probability in [0, 1]")


@dataclass(frozen=True)
class NoiseParameters(NoiseOverride):
    reset: float = 0
    one_qubit: float = 0
    two_qubit: float = 0
    measurement: float = 0
    idle: float = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        if any(getattr(self, f.name) is None for f in fields(self)):
            raise ValueError("Global noise probabilities cannot be None")

    def to_stimflow(self) -> sf.NoiseModel:
        def after(gate, p):
            return sf.NoiseRule(after={gate: p} if p else {})

        return sf.NoiseModel(
            gate_rules={
                "R": after("X_ERROR", self.reset),
                "RX": after("Z_ERROR", self.reset),
                "RY": after("X_ERROR", self.reset),
            },
            any_clifford_1q_rule=after("DEPOLARIZE1", self.one_qubit),
            any_clifford_2q_rule=after("DEPOLARIZE2", self.two_qubit),
            any_measurement_rule=sf.NoiseRule(flip_result=self.measurement),
            idle_depolarization=self.idle,
        )


@dataclass(frozen=True)
class ResourcePreparationNoise:
    """Ideal Bell-resource initialization followed by independent data depolarization.

    Zero probability still suppresses ordinary initialization/SE noise when enabled.
    This policy applies to explicit BellStatePrep composites, including nested ones.
    Probabilities in [0, 0.75] support native exact DEM extraction with pinned Stim.
    """

    enabled: bool = False
    p_st_transversal: float = 0.0

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("enabled must be a boolean")
        p = self.p_st_transversal
        if (not isinstance(p, (int, float)) or isinstance(p, bool)
                or not 0 <= p <= .75 or not math.isfinite(p)):
            raise ValueError("p_st_transversal must be a finite probability in [0, 0.75] "
                             "for exact DEM compatibility")


@dataclass(frozen=True)
class PostInitializationNoise:
    """Independent data depolarization after one named LogicalInit/use's final SE.

    Both identities must match. Probability zero records the cut without adding
    a channel. Ordinary initialization noise is controlled separately by overrides.
    """

    operation_id: str
    block_use_id: BlockUseId
    probability: float

    def __post_init__(self):
        if not isinstance(self.operation_id, str) or not self.operation_id:
            raise ValueError("Post-initialization noise needs an operation_id")
        if not isinstance(self.block_use_id, BlockUseId):
            raise ValueError("Post-initialization noise needs a BlockUseId")
        p = self.probability
        if (not isinstance(p, (int, float)) or isinstance(p, bool)
                or not 0 <= p <= .75 or not math.isfinite(p)):
            raise ValueError("probability must be finite in [0, 0.75] for exact DEM compatibility")


@dataclass(frozen=True)
class NoiseModel:
    default: NoiseParameters = field(default_factory=NoiseParameters)
    operation_overrides: Mapping[str, NoiseOverride] = field(default_factory=dict)
    resource_preparation: ResourcePreparationNoise = field(default_factory=ResourcePreparationNoise)
    post_initialization: tuple[PostInitializationNoise, ...] = ()

    def __post_init__(self) -> None:
        policies = tuple(self.post_initialization)
        if any(not isinstance(p, PostInitializationNoise) for p in policies):
            raise ValueError("post_initialization requires PostInitializationNoise policies")
        if len({p.block_use_id for p in policies}) != len(policies):
            raise ValueError("Duplicate post-initialization physical-use policy")
        object.__setattr__(self, "post_initialization", policies)
        if not isinstance(self.resource_preparation, ResourcePreparationNoise):
            raise ValueError("resource_preparation must be ResourcePreparationNoise")
        if not isinstance(self.default, NoiseParameters):
            raise ValueError("default must be NoiseParameters")
        for operation, override in self.operation_overrides.items():
            if operation not in (
                "LogicalInit",
                "SyndromeExtraction",
                "LogicalMeasure",
                "TransversalH",
                "TransversalCNOT",
                "LogicalPauli",
            ):
                raise ValueError(f"Unknown memory operation {operation!r}")
            if not isinstance(override, NoiseOverride):
                raise ValueError("Operation overrides must be NoiseOverride objects")
        object.__setattr__(
            self, "operation_overrides", MappingProxyType(dict(self.operation_overrides))
        )

    def resolve(
        self, operation_type: str | None = None, instance: NoiseOverride | None = None
    ) -> NoiseParameters:
        result = self.default
        for override in (self.operation_overrides.get(operation_type), instance):
            if override is not None:
                result = replace(
                    result,
                    **{
                        f.name: getattr(override, f.name)
                        for f in fields(override)
                        if getattr(override, f.name) is not None
                    },
                )
        return result

    @classmethod
    def uniform_depolarizing(cls, probability: float) -> "NoiseModel":
        return cls(NoiseParameters(*(probability for _ in range(5))))
