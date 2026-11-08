"""Independent source authoring and direct Python references for fixed Knill schedules."""

from logical_to_stim_converter import (
    BindPatch,
    KnillEC,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    SyndromeExtraction,
)

from .lstim_equivalence import declarations


def knill_source(*, distance=3, basis="Z", bit=0, cycles=3, post_rounds=1, open_outputs=False):
    """Author v1 text on the explicit P0/P1/P2 schedule; no operation inspection."""
    text = declarations(distance, 3) + f"""BIND D P0
BIND A0 P1
BIND B0 P2
INIT_{basis}({distance}) D
"""
    if bit:
        text += ("Z" if basis == "X" else "X") + "[sign] D\n"
    text += f"KNILL_EC[cycle0]({distance}) D A0 B0\n"
    if post_rounds:
        text += f"SE({post_rounds}) D\n"
    if cycles == 3:
        text += f"BIND A1 P0\nBIND B1 P1\nKNILL_EC[cycle1]({distance}) D A1 B1\n"
        if post_rounds:
            text += f"SE({post_rounds}) D\n"
        text += f"BIND A2 P2\nBIND B2 P0\nKNILL_EC[cycle2]({distance}) D A2 B2\n"
        if post_rounds:
            text += f"SE({post_rounds}) D\n"
    else:
        assert cycles == 1
    if not open_outputs:
        text += f"M{basis} D\n"
    return text


def knill_operations(*, distance=3, basis="Z", bit=0, cycles=3, post_rounds=1, open_outputs=False):
    """Manually authored public objects, independent of text/AST/lowering/helper runners."""
    operations = [
        BindPatch("D", "P0"), BindPatch("A0", "P1"), BindPatch("B0", "P2"),
        LogicalInit("D", basis, distance),
    ]
    if bit:
        operations.append(LogicalPauli(
            "D", "Z" if basis == "X" else "X", mode="physical", operation_id="sign",
        ))
    operations.append(KnillEC("D", "A0", "B0", rounds=distance, operation_id="cycle0"))
    if post_rounds:
        operations.append(SyndromeExtraction("D", post_rounds))
    if cycles == 3:
        operations.extend((
            BindPatch("A1", "P0"), BindPatch("B1", "P1"),
            KnillEC("D", "A1", "B1", rounds=distance, operation_id="cycle1"),
        ))
        if post_rounds:
            operations.append(SyndromeExtraction("D", post_rounds))
        operations.extend((
            BindPatch("A2", "P2"), BindPatch("B2", "P0"),
            KnillEC("D", "A2", "B2", rounds=distance, operation_id="cycle2"),
        ))
        if post_rounds:
            operations.append(SyndromeExtraction("D", post_rounds))
    else:
        assert cycles == 1
    if not open_outputs:
        operations.append(LogicalMeasure("D", basis))
    return tuple(operations)
