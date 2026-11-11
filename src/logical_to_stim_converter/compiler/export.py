"""JSON-compatible public provenance export with exact instruction arguments."""

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from importlib.metadata import distribution, version

import stim

from ..decoding.views import source_fingerprint


def export_metadata(compiled):
    """Export owned JSON values; floats retain Python's roundtrip precision.

    Stim text is useful for inspection but can round probabilities. The exported
    instruction arrays preserve exact arguments, target spellings and tags.
    No compiler-private objects or shot data enter the export.
    """

    def json_value(v):
        if isinstance(v, Enum):
            return v.value
        if is_dataclass(v):
            return {f.name: json_value(getattr(v, f.name)) for f in fields(v)}
        if isinstance(v, Mapping):
            # Non-string keys (physical uses/sites) remain explicit ordered pairs.
            if all(isinstance(k, str) for k in v):
                return {k: json_value(value) for k, value in v.items()}
            return [[json_value(k), json_value(value)] for k, value in v.items()]
        if isinstance(v, (tuple, list, set, frozenset)):
            return [json_value(x) for x in (sorted(v) if isinstance(v, (set, frozenset)) else v)]
        return v

    def target_text(t):
        if t.is_combiner:
            return "*"
        if t.is_measurement_record_target:
            return f"rec[{t.value}]"
        if t.is_sweep_bit_target:
            return f"sweep[{t.value}]"
        axis = t.pauli_type if t.pauli_type in ("X", "Y", "Z") else ""
        return ("!" if t.is_inverted_result_target else "") + axis + str(t.value)

    def instructions(circuit):
        return [
            {
                "name": "REPEAT",
                "repeat_count": i.repeat_count,
                "body": instructions(i.body_copy()),
                "tag": i.tag,
            }
            if isinstance(i, stim.CircuitRepeatBlock)
            else {
                "name": i.name,
                "targets": [target_text(t) for t in i.targets_copy()],
                "arguments": i.gate_args_copy(),
                "tag": i.tag,
            }
            for i in circuit
        ]

    names = (
        "physical_qubit_map",
        "logical_to_block",
        "measurements",
        "detectors",
        "observables",
        "frames",
        "block_status",
        "time_layers",
        "orientations",
        "preparations",
        "readouts",
        "bell_measurements",
        "relocation_history",
        "composites",
        "detector_boundary_candidates",
        "open_logical_outputs",
        "preparation_dependencies",
        "block_preparation_dependencies",
        "ancestry_events",
        "block_uses",
        "binding_history",
        "available_blocks",
        "use_preparation_dependencies",
        "resource_preparation_boundaries",
        "post_initialization_boundaries",
        "logical_output_stabilizers",
    )
    result = {name: json_value(getattr(compiled, name)) for name in names}
    result.update(
        schema="compiled-metadata-v1",
        noise_model=json_value(compiled._noise_model),
        stimflow_source_commit=json.loads(
            distribution("stimflow").read_text("direct_url.json") or "{}"
        )
        .get("vcs_info", {})
        .get("commit_id"),
        source_fingerprint=source_fingerprint(compiled),
        versions={
            name: version(name) for name in ("stim", "stimflow", "logical-to-stim-converter")
        },
        ideal_instructions=instructions(compiled.ideal_circuit),
        selected_instructions=instructions(compiled.circuit),
        fragments=[
            {
                name: json_value(getattr(f, name))
                for name in (
                    "module_id",
                    "operation_type",
                    "operation_id",
                    "logical_ids",
                    "block_ids",
                    "block_use_ids",
                    "composite_ids",
                    "stage",
                    "orientations_before",
                    "orientations_after",
                    "logical_action",
                    "frame_transition",
                    "noise",
                )
            }
            for f in compiled.fragments
        ],
    )
    return result
