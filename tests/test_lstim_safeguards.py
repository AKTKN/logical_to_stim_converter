"""Frontend validation cannot bypass physical lifecycle, geometry, flow or epoch checks."""

import numpy as np
import pytest
import stim

from logical_to_stim_converter import (
    BindPatch,
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LSTIMCompileError,
    LSTIMError,
    RotatedSurfaceCodeBackend,
    TransversalH,
    parse_logical_circuit,
)
from logical_to_stim_converter.decoding import (
    CorrectionBatch,
    DecoderViewError,
    SourceMismatchError,
)
from tests.helpers.lstim_equivalence import compile_pair, declarations, placed_blocks
from tests.helpers.lstim_programs import knill_operations, knill_source


@pytest.mark.parametrize("body", [
    "PARALLEL {\nH D\n", "H[] D", "H[dup] D\nH[dup] D",
    "TICK", "DETECTOR rec[-1]", "S D", "SE(word) D", "H Δ",
    "REPEAT 999999999999999999 {\nH D\n}",
    "REPEAT 2 {\nINIT_Z(1) D\n}", "REPEAT 2 {\nMZ D\n}",
    "REPEAT 2 {\nBIND A P0\n}", "REPEAT 2 {\nKNILL_EC D A B\n}",
    "X D mode=random", "KNILL_EC D A B prepare_resource=1",
])
def test_bad_source_rejected_without_compiling_or_sampling(monkeypatch, body):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid source reached physical compilation")

    monkeypatch.setattr(CircuitCompiler, "compile", forbidden)
    monkeypatch.setattr(stim.Circuit, "compile_sampler", forbidden)
    source = declarations(3, 3) + "BIND D P0\nBIND A P1\nBIND B P2\n" + body
    with pytest.raises(LSTIMError) as caught:
        parse_logical_circuit(source, "bad-input.lstim")
    assert caught.value.source_name == "bad-input.lstim" and caught.value.line is not None


@pytest.mark.parametrize("version", ["FORMAT(0)", "FORMAT(2)", "FORMAT(foo)", ""])
def test_invalid_header_is_never_a_successful_empty_circuit(version):
    with pytest.raises(LSTIMError):
        parse_logical_circuit(declarations().replace("FORMAT(1)", version))


@pytest.mark.parametrize("body,operations", [
    ("INIT_Z(1) D\nINIT_X(1) D", (LogicalInit("D", "Z", 1), LogicalInit("D", "X", 1))),
    ("INIT_Z(1) D\nMZ D\nH D", (LogicalInit("D", "Z", 1), LogicalMeasure("D", "Z"),
                                  TransversalH("D"))),
    ("INIT_Z(1) D\nBIND other P0", (LogicalInit("D", "Z", 1), BindPatch("other", "P0"))),
    ("INIT_Z(1) D\nPARALLEL {\nH D\nH D\n}",
     (LogicalInit("D", "Z", 1), (TransversalH("D"), TransversalH("D")))),
    ("INIT_Z(1) D\nMX D", (LogicalInit("D", "Z", 1), LogicalMeasure("D", "X"))),
])
def test_runtime_safeguards_match_independently_authored_python_failures(body, operations):
    source = declarations() + "BIND D P0\n" + body
    with pytest.raises(ValueError) as direct:
        CircuitCompiler(placed_blocks(3, 1), logical_to_block={}).compile(
            (BindPatch("D", "P0"), *operations),
        )
    with pytest.raises(LSTIMCompileError) as text:
        parse_logical_circuit(source, "lifecycle.lstim").compile()
    assert str(text.value.original_error) == str(direct.value)
    assert type(text.value.original_error) is type(direct.value)
    assert text.value.__cause__ is text.value.original_error
    assert text.value.source_name == "lifecycle.lstim" and text.value.span is None


def test_invalid_bell_resource_fails_identically_without_preparation():
    source = declarations(3, 3) + """BIND D P0
BIND A P1
BIND B P2
INIT_Z(1) D
INIT_Z(1) A
INIT_Z(1) B
KNILL_EC D A B prepare_resource=false
"""
    operations = (BindPatch("D", "P0"), BindPatch("A", "P1"), BindPatch("B", "P2"),
                  LogicalInit("D", "Z", 1), LogicalInit("A", "Z", 1), LogicalInit("B", "Z", 1),
                  KnillEC("D", "A", "B", prepare_resource=False))
    with pytest.raises(ValueError, match="Bell XX=ZZ") as direct:
        CircuitCompiler(placed_blocks(3, 3), logical_to_block={}).compile(operations)
    with pytest.raises(LSTIMCompileError) as text:
        parse_logical_circuit(source).compile()
    assert str(text.value.original_error) == str(direct.value)


def test_impossible_layout_and_unsupported_mixed_distance_cnot_are_not_bypassed():
    from logical_to_stim_converter import TransversalCNOT

    source = """FORMAT(1)
CODE small ROTATED_SURFACE(3)
CODE large ROTATED_SURFACE(5)
PATCH P0 small index=3
PATCH P1 large index=2
"""
    blocks = (LogicalBlock.placed("P0", CodeSpec.rotated_surface(3), patch_index=3),
              LogicalBlock.placed("P1", CodeSpec.rotated_surface(5), patch_index=2))
    with pytest.raises(ValueError, match="overlapping physical coordinates") as direct:
        CircuitCompiler(blocks, logical_to_block={})
    with pytest.raises(LSTIMCompileError) as text:
        parse_logical_circuit(source).compile(allow_open_outputs=True)
    assert str(text.value.original_error) == str(direct.value)
    source = source.replace("P0 small index=3", "P0 small index=0") + """BIND D P0
BIND A P1
INIT_Z(1) D
INIT_Z(1) A
CX D A
"""
    blocks = (LogicalBlock.placed("P0", CodeSpec.rotated_surface(3), patch_index=0), blocks[1])
    operations = (BindPatch("D", "P0"), BindPatch("A", "P1"),
                  LogicalInit("D", "Z", 1), LogicalInit("A", "Z", 1), TransversalCNOT("D", "A"))
    with pytest.raises(ValueError, match="equal-distance") as direct:
        CircuitCompiler(blocks, logical_to_block={}).compile(operations)
    with pytest.raises(LSTIMCompileError) as text:
        parse_logical_circuit(source).compile()
    assert str(text.value.original_error) == str(direct.value)


def test_corrupted_physical_h_still_fails_signed_backend_flow_validation(monkeypatch):
    original = RotatedSurfaceCodeBackend.hadamard

    def corrupt(self, *args, **kwargs):
        correct = original(self, *args, **kwargs)
        return correct.with_edits(circuit=stim.Circuit())

    monkeypatch.setattr(RotatedSurfaceCodeBackend, "hadamard", corrupt)
    operations = (BindPatch("D", "P0"), LogicalInit("D", "Z", 1), TransversalH("D"))
    with pytest.raises(ValueError) as direct:
        CircuitCompiler(placed_blocks(3, 1), logical_to_block={}).compile(
            operations, allow_open_outputs=True,
        )
    with pytest.raises(LSTIMCompileError) as text:
        parse_logical_circuit(declarations() + "BIND D P0\nINIT_Z(1) D\nH D\n").compile(
            allow_open_outputs=True,
        )
    assert str(text.value.original_error) == str(direct.value)


def test_stale_epoch_and_source_corrections_are_rejected_for_both_artifacts():
    actual, reference = compile_pair(knill_source(), knill_operations(), count=3)
    raw = actual.circuit.compile_sampler(seed=825).sample(3)
    for c in (actual, reference):
        plan = c.make_frame_plan()
        old, fresh = c.preparations[0], c.preparations[-1]
        boundary = plan.boundary_by_id[fresh.module_id]
        bits = np.zeros((len(raw), len(boundary.input_ids)), dtype=bool)
        state = plan.start(raw, source_fingerprint=plan.source_fingerprint)
        with pytest.raises(DecoderViewError, match="different physical use"):
            state.apply(CorrectionBatch(plan.source_fingerprint, fresh.module_id,
                                        bits, old.block_use_id))
        with pytest.raises(SourceMismatchError):
            state.apply(CorrectionBatch("another-source", fresh.module_id, bits))
        with pytest.raises(SourceMismatchError):
            plan.start(raw, source_fingerprint="another-source")
        view = c.make_decoder_view()
        with pytest.raises(SourceMismatchError):
            view.events_from_raw(raw, source_fingerprint="another-source")
