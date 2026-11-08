"""Insert gate noise and global idle noise once, after ideal flow composition."""

from collections.abc import Mapping
from dataclasses import replace

import stim

from ..core.compiler_context import TimeLayer
from ..core.logical_block import GlobalSiteId
from ..core.module_fragment import ModuleFragment
from .model import NoiseModel


class NoiseInjector:
    """Apply primitive gate rules and one idle channel per eligible physical site."""
    def apply(
        self,
        ideal: stim.Circuit,
        *,
        model: NoiseModel,
        physical_map: Mapping[GlobalSiteId, int],
        layers: tuple[TimeLayer, ...],
        fragments: tuple[ModuleFragment, ...],
    ) -> stim.Circuit:
        """Return a noisy copy using inclusive reset-to-readout use intervals.

        All data/check ancillas of active_use_ids are idle-eligible. Available or
        reserved patches receive no idle channel until their next physical reset.
        """
        if ideal != ideal.without_noise():
            raise ValueError("Noise must be applied once to a noiseless ideal circuit")
        by_module = {f.module_id: f for f in fragments}
        by_block: dict[str, set[int]] = {}
        for (block, _), index in physical_map.items():
            by_block.setdefault(block, set()).add(index)
        parameters = {f.module_id: model.resolve(f.operation_type, f.noise) for f in fragments}
        # Per-operation noise excludes idle: the latter is computed globally below.
        upstream = {key: replace(value, idle=0).to_stimflow() for key, value in parameters.items()}
        result = stim.Circuit()
        layer_index = 0

        def append_idle():
            """Insert each active use's unused physical sites once for this TICK interval."""
            layer = layers[layer_index]
            for use in layer.active_use_ids:
                block = use.block_id
                module = layer.operation_by_block.get(block)
                resolved = parameters[module] if module else model.default
                idle = sorted(by_block[block] - layer.used_qubits)
                if idle and resolved.idle:
                    result.append("DEPOLARIZE1", idle, resolved.idle)

        for instruction in ideal:
            if isinstance(instruction, stim.CircuitRepeatBlock):
                raise ValueError("Noise injection expects the exported expanded time schedule")
            if instruction.name == "TICK":
                append_idle()
                result.append(instruction)
                layer_index += 1
            elif instruction.tag in by_module:
                single = stim.Circuit()
                single.append(instruction)
                result += upstream[instruction.tag].noisy_circuit(
                    single, system_qubit_indices=set()
                )
            else:
                if instruction.name not in (
                    "QUBIT_COORDS",
                    "SHIFT_COORDS",
                    "DETECTOR",
                    "OBSERVABLE_INCLUDE",
                ):
                    raise ValueError("Physical instructions require module noise provenance")
                result.append(instruction)
        append_idle()
        return result
