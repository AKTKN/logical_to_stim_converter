"""Production construction boundary. Nothing in this module is an oracle."""

from dataclasses import asdict

from logical_to_stim_converter import (
    CircuitCompiler,
    CodeSpec,
    KnillEC,
    LogicalBlock,
    LogicalInit,
    LogicalMeasure,
    LogicalPauli,
    NoiseModel,
    NoiseOverride,
    NoiseParameters,
    ResourcePreparationNoise,
)


def compile_dut(
    distance,
    basis,
    noise=None,
    *,
    open_output=False,
    bit=0,
    virtual=False,
    type_overrides=None,
    instance_overrides=None,
    m9_enabled=False,
    p_st=0,
):
    """Compile the public three-patch program with explicit independent roles."""
    instance_overrides = instance_overrides or {}
    blocks = [
        LogicalBlock.placed(f"P{i}", CodeSpec.rotated_surface(distance), patch_index=i)
        for i in range(3)
    ]

    def override(name):
        value = instance_overrides.get(name)
        return NoiseOverride(**value) if value is not None else None

    program = [LogicalInit("D", basis, 1, noise=override("D.init"))]
    if bit:
        program.append(
            LogicalPauli("D", "Z" if basis == "X" else "X", mode="frame" if virtual else "physical")
        )
    program.append(KnillEC("D", "A", "B", rounds=distance, noise=override("KnillEC")))
    if not open_output:
        program.append(LogicalMeasure("D", basis, noise=override("B.readout")))
    model = (
        None
        if noise is None
        else NoiseModel(
            NoiseParameters(**asdict(noise)),
            {name: NoiseOverride(**value) for name, value in (type_overrides or {}).items()},
            ResourcePreparationNoise(m9_enabled, p_st),
        )
    )
    return CircuitCompiler(blocks, logical_to_block={"D": "P0", "A": "P1", "B": "P2"}).compile(
        program,
        noise_model=model,
        allow_open_outputs=open_output,
    )


def protocol_sections(compiled):
    """Extract actual tagged DUT sections; expected geometry is supplied separately."""
    import stim

    fragments = compiled.fragments
    selected = {
        "D": [
            f.module_id
            for f in fragments
            if f.operation_type == "LogicalInit" and f.block_id == "P0"
        ],
        "A": [
            f.module_id
            for f in fragments
            if f.operation_type == "LogicalInit" and f.block_id == "P1"
        ],
        "B": [
            f.module_id
            for f in fragments
            if f.operation_type == "LogicalInit" and f.block_id == "P2"
        ],
        "entangle": [
            f.module_id
            for f in fragments
            if f.operation_type == "TransversalCNOT" and f.block_ids == ("P1", "P2")
        ],
        "bell_measure": [
            f.module_id
            for f in fragments
            if (f.operation_type == "TransversalCNOT" and f.block_ids == ("P0", "P1"))
            or (f.operation_type == "LogicalMeasure" and f.block_id in ("P0", "P1"))
        ],
        "readout": [
            f.module_id
            for f in fragments
            if f.operation_type == "LogicalMeasure" and f.block_id == "P2"
        ],
    }
    result = {name: stim.Circuit() for name in selected}
    for inst in compiled.ideal_circuit.flattened():
        for name, tags in selected.items():
            if inst.tag in tags:
                result[name].append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    # Signed physical input Paulis occur between initialization and resources.
    for f in fragments:
        if f.operation_type == "LogicalPauli":
            for inst in compiled.ideal_circuit.flattened():
                if inst.tag == f.module_id:
                    result["D"].append(inst.name, inst.targets_copy(), inst.gate_args_copy())
    return result
