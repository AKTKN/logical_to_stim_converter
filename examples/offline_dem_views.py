"""An external consumer samples once, then chooses different offline model views."""

import numpy as np

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    DetectorSelector,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    NoiseModel,
    SyndromeExtraction,
    observable_local_views,
)


def main():
    code = CodeSpec.rotated_surface(3)
    blocks = [LogicalBlock.placed(q, code, patch_index=i) for i, q in enumerate(("A", "B"))]
    compiled = CircuitCompiler(blocks).compile(
        [
            [LogicalInit("A", "X", 1), LogicalInit("B", "Z", 1)],
            SyndromeExtraction(("A", "B"), 3),
            [LogicalMeasure("A", "X"), LogicalMeasure("B", "Z")],
        ],
        noise_model=NoiseModel.uniform_depolarizing(0.001),
    )
    global_view = compiled.make_decoder_view()
    local_views = observable_local_views(compiled)
    strict_a = compiled.make_decoder_view(
        detector_selector=DetectorSelector(block_ids=("A",), block_membership="strict")
    )
    # This is the only physical sampling call. Every consumer receives a projection.
    raw = compiled.circuit.compile_sampler(seed=100).sample(512)
    original = raw.copy()
    global_inputs = global_view.inputs_from_raw(raw)
    for view in (*local_views, strict_a):
        view.assert_source(compiled)
        inputs = view.inputs_from_raw(raw, source_fingerprint=global_inputs.source_fingerprint)
        assert np.array_equal(
            inputs.detection_events, view.project_detection_events(global_inputs.detection_events)
        )
        print("Global detector IDs:", view.detector_map.global_ids)
        print("Global observable IDs:", view.observable_map.global_ids)
        print(
            "Selected sample shapes:", inputs.detection_events.shape, inputs.observable_flips.shape
        )
        print("Local DEM mechanisms:", view.detector_error_model.num_errors)
    # A caller's software record frame edits a copy and recomputes event parity.
    record_flips = np.zeros_like(raw)
    record_flips[:, 0] = True  # illustrative caller-supplied mask, not a decoder result
    updated = strict_a.inputs_from_raw(raw, record_flips=record_flips)
    assert np.array_equal(
        updated.detection_events,
        strict_a.update_detection_events(global_inputs.detection_events, record_flips),
    )
    assert np.array_equal(raw, original)
    print("One physical batch reused by global, observable-local and strictly local views.")
    print("Software record updates left the physical circuit and raw batch unchanged.")


if __name__ == "__main__":
    main()
