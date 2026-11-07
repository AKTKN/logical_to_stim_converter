"""Physical Clifford proofs, independent support conventions, and corruptions."""

import pytest
import stim
import stimflow as sf

from logical_to_stim_converter import CodeSpec, LogicalBlock, RotatedSurfaceCodeBackend


def logical_support(block, axis, orientation):
    d = block.code.d
    sites = (
        [complex(2 * x + 1, 1) for x in range(d)]
        if axis == "X"
        else [complex(1, 2 * y + 1) for y in range(d)]
    )
    if orientation:
        sites = [complex(q.imag, 2 * d - q.real) for q in sites]
    return sf.PauliMap({q + block.origin: axis for q in sites})


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("orientations", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_cnot_physical_and_logical_action(d, orientations):
    backend = RotatedSurfaceCodeBackend()
    c = LogicalBlock.placed("control", CodeSpec.rotated_surface(d))
    t = LogicalBlock.placed("target", c.code, patch_index=1)
    oc, ot = orientations
    chunk, reflow = backend.transversal_cnot(c, t, "C", "T", oc, ot)
    chunk.verify()
    reflow.verify()
    assert len(chunk.flows) == 2 * (d * d - 1) + 4
    (gate,) = tuple(chunk.circuit)
    assert gate.name == "CX"
    targets = gate.targets_copy()
    assert len(targets) == 2 * d * d
    assert len(set(q.value for q in targets)) == 2 * d * d
    q2i = chunk.q2i
    coords = {i: q for q, i in q2i.items()}
    expected_pairs = set()
    for column in range(d * d):
        x, y = divmod(column, d)
        normal = complex(2 * x + 1, 2 * y + 1)
        pc = complex(normal.imag, 2 * d - normal.real) if oc else normal
        pt = complex(normal.imag, 2 * d - normal.real) if ot else normal
        expected_pairs.add((pc + c.origin, pt + t.origin))
    actual_pairs = {
        (coords[a.value], coords[b.value]) for a, b in zip(targets[::2], targets[1::2], strict=True)
    }
    assert actual_pairs == expected_pairs
    cx, cz = (logical_support(c, axis, oc) for axis in "XZ")
    tx, tz = (logical_support(t, axis, ot) for axis in "XZ")
    expected = {("C", "X"): cx * tx, ("C", "Z"): cz, ("T", "X"): tx, ("T", "Z"): cz * tz}
    for flow in chunk.flows:
        assert flow.sign is False
        if flow.obs_name is not None:
            assert sf.PauliMap(flow.end) == expected[flow.obs_name]
    # All old check generators are propagated; reflow reconstructs the full local basis.
    assert len(reflow.out2in) == 2 * (d * d - 1)
    assert len(reflow.removed_inputs) == len(reflow.out2in)
    assert any(len(inputs) == 2 for inputs in reflow.out2in.values())
    for inputs in reflow.out2in.values():
        assert inputs
    # The actual physical layer squares to identity, including its data pairing.
    assert stim.Tableau.from_circuit(chunk.circuit * 2) == stim.Tableau(2 * d * d)


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("orientation", [0, 1])
def test_h_geometry_and_next_syndrome(d, orientation):
    block = LogicalBlock.placed("physical", CodeSpec.rotated_surface(d))
    backend = RotatedSurfaceCodeBackend()
    h = backend.hadamard(block, "logical", orientation)
    (gate,) = tuple(h.circuit)
    assert gate.name == "H"
    actual = {q for q, i in h.q2i.items() if i in {t.value for t in gate.targets_copy()}}
    assert actual == {block.position(local) for local in block.layout.data_ids}
    assert len(gate.targets_copy()) == d * d
    assert len(h.flows) == d * d - 1 + 2
    assert not any(i.name == "SWAP" for i in h.circuit)
    backend.syndrome_round(block, "logical", 1 - orientation).verify()
    before = backend.stabilizer_code(block, "logical", orientation)
    after = backend.stabilizer_code(block, "logical", 1 - orientation)
    after_checks = {tile.to_pauli_map() for tile in after.tiles}
    assert {f.end for f in h.flows if f.obs_name is None} == after_checks
    for axis in "XZ":
        assert sf.PauliMap(before.flat_logicals["XZ".index(axis)]) == logical_support(
            block, axis, orientation
        )
    for flow in h.flows:
        assert dict(flow.end.items()) == {
            q: ("Z" if b == "X" else "X") for q, b in flow.start.items()
        }
    assert stim.Tableau.from_circuit(h.circuit * 2) == stim.Tableau(d * d)
    # The original code boundary is not valid after a bare physical H.
    wrong = [sf.Flow(start=tile, end=tile, sign=False) for tile in before.tiles]
    with pytest.raises(ValueError):
        h.with_edits(flows=wrong).verify()
    empty = stim.Circuit()
    with pytest.raises(ValueError):
        h.with_edits(circuit=empty).verify()


@pytest.mark.parametrize("kind", ["reverse", "wrong-pair", "missing", "orientation"])
def test_corrupted_cnot_is_rejected(kind):
    backend = RotatedSurfaceCodeBackend()
    c = LogicalBlock.placed("c", CodeSpec.rotated_surface(3))
    t = LogicalBlock.placed("t", c.code, patch_index=1)
    chunk, _ = backend.transversal_cnot(c, t, "C", "T", 1, 0)
    targets = [q.value for q in chunk.circuit[0].targets_copy()]
    pairs = list(zip(targets[::2], targets[1::2], strict=True))
    if kind == "reverse":
        pairs = [(b, a) for a, b in pairs]
    elif kind == "wrong-pair":
        bs = [b for _, b in pairs]
        pairs = [(a, bs[(i + 1) % len(bs)]) for i, (a, _) in enumerate(pairs)]
    elif kind == "missing":
        pairs = pairs[1:]
    else:
        pairs = [(chunk.q2i[c.position(q)], chunk.q2i[t.position(q)]) for q in c.layout.data_ids]
    bad = stim.Circuit()
    bad.append("CX", [i for pair in pairs for i in pair])
    with pytest.raises(ValueError):
        chunk.with_edits(circuit=bad).verify()


@pytest.mark.parametrize("d", [3, 5])
@pytest.mark.parametrize("axis", ["X", "Y", "Z"])
@pytest.mark.parametrize("orientation", [0, 1])
def test_physical_pauli_action(d, axis, orientation):
    backend = RotatedSurfaceCodeBackend()
    block = LogicalBlock.placed("p", CodeSpec.rotated_surface(d))
    chunk = backend.pauli(block, "q", axis, orientation)
    chunk.verify()
    lx, lz = (logical_support(block, a, orientation) for a in "XZ")
    expected = lx if axis == "X" else lz if axis == "Z" else lx * lz
    actual = {}
    for instruction in chunk.circuit:
        assert instruction.name in "XYZ"
        for target in instruction.targets_copy():
            position = next(q for q, i in chunk.q2i.items() if i == target.value)
            actual[position] = instruction.name
    assert actual == dict(expected.items())
    for flow in chunk.flows:
        assert flow.start == flow.end
        if flow.obs_name is None:
            assert flow.sign is False
        else:
            logical_axis = flow.obs_name[1]
            assert flow.sign == (axis != logical_axis)
    code = backend.stabilizer_code(block, "q", orientation)
    assert all(expected.commutes(tile.to_pauli_map()) for tile in code.tiles)


def test_required_check_reflow_and_corrupted_generator_product():
    from logical_to_stim_converter import ModuleFragment
    from logical_to_stim_converter.compiler._parallel import parallel_chunk

    backend = RotatedSurfaceCodeBackend()
    a = LogicalBlock.placed("a", CodeSpec.rotated_surface(3))
    b = LogicalBlock.placed("b", a.code, patch_index=1)

    def only_checks(chunk):
        return chunk.with_edits(
            flows=[f for f in chunk.flows if f.obs_name is None],
            discarded_inputs=[p for p in chunk.discarded_inputs if p.obs_name is None],
            discarded_outputs=[p for p in chunk.discarded_outputs if p.obs_name is None],
        )

    def combined(chunks, compiler):
        parts = [
            (only_checks(chunk), ModuleFragment(f"m{i}", "test", str(i), str(i), (chunk,)))
            for i, chunk in enumerate(chunks)
        ]
        return parallel_chunk(parts, compiler.cur_end_interface())

    initial = [backend.initialization(a, "A", "Z"), backend.initialization(b, "B", "Z")]
    se = [backend.syndrome_round(a, "A"), backend.syndrome_round(b, "B")]
    gate, reflow = backend.transversal_cnot(a, b, "A", "B")
    compiler = sf.ChunkCompiler()
    compiler.append(combined(initial, compiler))
    compiler.append(combined(se, compiler))
    compiler.append(only_checks(gate))
    with pytest.raises(ValueError, match="flow"):
        compiler.copy().append(combined(se, compiler))
    compiler.append(reflow)
    compiler.append(combined(se, compiler))
    terminal = [backend.measurement(a, "A", "Z"), backend.measurement(b, "B", "Z")]
    compiler.append(combined(terminal, compiler))
    compiler.finish_circuit().detector_error_model()
    broken = dict(reflow.out2in)
    output = next(p for p, inputs in broken.items() if len(inputs) == 2)
    broken[output] = broken[output][:1]
    with pytest.raises(ValueError, match="product"):
        sf.ChunkReflow(broken).verify()
