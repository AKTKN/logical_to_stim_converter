"""Physical patch instances with stable identities distinct from Stim indices."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .code_spec import CodeSpec, positive_int
from .physical_layout import PhysicalLayout

# A global site is an opaque stable identity, never a Stim integer or coordinate.
GlobalSiteId = tuple[str, str]


@dataclass(frozen=True, eq=False)
class LogicalBlock:
    block_id: str
    code: CodeSpec
    layout: PhysicalLayout
    origin: complex = 0j
    site_map: Mapping[str, GlobalSiteId] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.block_id, str) or not self.block_id:
            raise ValueError("block_id must be a nonempty string")
        if not math.isfinite(self.origin.real) or not math.isfinite(self.origin.imag):
            raise ValueError("Block origin must be finite")
        self.layout.validate_code(self.code)
        object.__setattr__(
            self,
            "site_map",
            MappingProxyType({q: (self.block_id, q) for q in self.layout.qubit_ids}),
        )

    def position(self, local_id: str) -> complex:
        return self.origin + self.layout.coordinates[local_id]

    def global_site(self, local_id: str) -> GlobalSiteId:
        return self.site_map[local_id]

    def local_site(self, site_id: GlobalSiteId) -> str:
        block_id, local_id = site_id
        if block_id != self.block_id or local_id not in self.site_map:
            raise KeyError(site_id)
        return local_id

    @classmethod
    def placed(cls, block_id: str, code: CodeSpec, *, patch_index: int = 0) -> "LogicalBlock":
        """Deterministic separated placement for equal-distance patches."""
        positive_int(patch_index, "patch_index", minimum=0)
        return cls(
            block_id,
            code,
            PhysicalLayout.rotated_surface(code),
            complex(patch_index * (2 * code.d + 2), 0),
        )
