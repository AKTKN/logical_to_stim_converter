"""Insert gate noise and global idle noise once, after ideal flow composition."""

from collections.abc import Mapping
from dataclasses import replace

import stim

from ..core.compiler_context import TimeLayer
from ..core.logical_block import GlobalSiteId
from ..core.module_fragment import ModuleFragment
from .model import NoiseModel
from .resource_preparation import ResourcePreparationBoundary


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
        resource_preparation_boundaries: tuple[ResourcePreparationBoundary, ...] | None = None,
    ) -> stim.Circuit:
        """Return a noisy copy using inclusive reset-to-readout use intervals.

        All data/check ancillas of active_use_ids are idle-eligible. Available or
        reserved patches receive no idle channel until their next physical reset.
        An enabled resource policy requires an explicit verified boundary tuple;
        () declares no eligible resources. Use CircuitCompiler.compile to resolve
        that plan. Omission remains supported when the policy is disabled.
        """
        if ideal != ideal.without_noise():
            raise ValueError("Noise must be applied once to a noiseless ideal circuit")
        if resource_preparation_boundaries is None:
            if model.resource_preparation.enabled:
                raise ValueError(
                    "Enabled resource preparation requires explicit "
                    "resource_preparation_boundaries; "
                    "pass verified boundaries or use CircuitCompiler.compile")
            resource_preparation_boundaries = ()
        elif not isinstance(resource_preparation_boundaries, tuple) or any(
            not isinstance(b, ResourcePreparationBoundary) for b in resource_preparation_boundaries
        ):
            raise ValueError("resource_preparation_boundaries must be a tuple of "
                             "ResourcePreparationBoundary objects")
        if resource_preparation_boundaries and not model.resource_preparation.enabled:
            raise ValueError("Resource preparation boundaries require an enabled policy")
        eligible = {b.preparation_module_id for b in resource_preparation_boundaries}
        intervals = {b.block_use_id: (b.first_layer, b.final_se_layer)
                     for b in resource_preparation_boundaries}
        insertions = {}
        for boundary in resource_preparation_boundaries:
            insertions.setdefault(boundary.ideal_boundary_instruction, []).append(boundary)
        if (len(eligible) != len(resource_preparation_boundaries)
                or len(intervals) != len(resource_preparation_boundaries)):
            raise ValueError("Duplicate resource preparation module/use epoch")
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
                interval = intervals.get(use)
                if interval is not None and interval[0] <= layer_index <= interval[1]:
                    continue
                block = use.block_id
                module = layer.operation_by_block.get(block)
                resolved = parameters[module] if module else model.default
                idle = sorted(by_block[block] - layer.used_qubits)
                if idle and resolved.idle:
                    result.append("DEPOLARIZE1", idle, resolved.idle)

        for index, instruction in enumerate(ideal):
            if isinstance(instruction, stim.CircuitRepeatBlock):
                raise ValueError("Noise injection expects the exported expanded time schedule")
            if instruction.name == "TICK":
                append_idle()
                result.append(instruction)
                layer_index += 1
                for boundary in insertions.get(index + 1, ()):
                    p = model.resource_preparation.p_st_transversal
                    if p:
                        result.append(
                            "DEPOLARIZE1", [physical_map[s] for s in boundary.data_sites],
                            p, tag=boundary.channel_tag,
                        )
            elif instruction.tag in eligible:
                result.append(instruction)
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
