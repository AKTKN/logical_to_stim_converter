"""Direct-Stim three-patch oracle from geometry and the written Knill schedule.

Expected gates, role lifetimes, records and parity anchors are authored here.
Nothing is constructed by consulting DUT circuits, metadata, layouts or noise.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

import stim

from .spec import (
    DIRECTIONS,
    PATCHES,
    Action,
    ReferenceMoment,
    absolute_coordinate,
    check_key,
    protocol_geometry,
    readout_key,
)


@dataclass(frozen=True)
class ReferenceBundle:
    circuit: stim.Circuit
    geometry: object
    indices: Mapping
    records: Mapping
    moments: tuple[ReferenceMoment, ...]
    annotation_rows: tuple[int, ...]
    observables: Mapping[int, int]
    annotation_anchors: Mapping
    resource_boundary_moment: int
    resource_first_moment: int
    open_output: bool
    basis: str
    bit: int

    @property
    def canonical_keys(self):
        return tuple(sorted(self.records))

    @property
    def sites(self):
        return {
            i: absolute_coordinate(self.geometry.distance, p, q)
            for (p, q), i in self.indices.items()
        }


def _parity(indices):
    row = 0
    for i in indices:
        row ^= 1 << i
    return row


def _expected_annotations(g, basis, records, open_output):
    """Check eigenvalue propagation through A->B then D->A, over GF(2).

    After both CXs, X_D has syndrome s_DX+s_AX+s_BX, Z_A has
    s_DZ+s_AZ, X_B has s_BX and Z_B has s_AZ+s_BZ. These local
    check identities define the boundary anchors without consulting annotations.
    """
    columns = {key: i for i, key in enumerate(sorted(records))}
    anchors = {}

    def add(anchor, keys):
        anchors[anchor] = _parity(columns[k] for k in keys)

    for patch, init_basis, rounds in (
        ("D", basis, 1),
        ("A", "X", g.distance),
        ("B", "Z", g.distance),
    ):
        for c in g.checks:
            if c.basis == init_basis:
                add(("initial", patch, c.basis, c.coordinate, 1), [check_key(patch, c, 1)])
            for t in range(2, rounds + 1):
                add(
                    ("temporal", patch, c.basis, c.coordinate, t),
                    [check_key(patch, c, t - 1), check_key(patch, c, t)],
                )
    for c in g.checks:
        if c.basis == "X":
            add(
                ("bell_readout", "D", c.basis, c.coordinate, 1),
                [check_key("D", c, 1), check_key("A", c, g.distance), check_key("B", c, g.distance)]
                + [readout_key("D", "X", q) for q in c.support],
            )
        else:
            add(
                ("bell_readout", "A", c.basis, c.coordinate, 1),
                [check_key("D", c, 1), check_key("A", c, g.distance)]
                + [readout_key("A", "Z", q) for q in c.support],
            )
        if not open_output and c.basis == basis:
            terms = [check_key("B", c, g.distance)]
            if basis == "Z":
                terms.append(check_key("A", c, g.distance))
            add(
                ("final_readout", "B", c.basis, c.coordinate, 1),
                terms + [readout_key("B", basis, q) for q in c.support],
            )
    observables = {}
    if not open_output:
        bell_patch = "D" if basis == "X" else "A"
        observables[0] = _parity(
            columns[readout_key(p, basis, q)] for p in (bell_patch, "B") for q in g.logical(basis)
        )
    return anchors, observables


def build_reference(distance: int, basis: str, *, open_output: bool = False, bit: int = 0):
    """Author one teleportation: D one SE; concurrent A/B d SE; two CXs.

    The exact physical same-schedule envelope uses bit=0. For independent
    negative-eigenstate channel checks, bit=1 adds its logical Pauli directly
    after the D initialization and before resource preparation.
    """
    if basis not in ("X", "Z") or type(open_output) is not bool or bit not in (0, 1):
        raise ValueError("Expected X/Z, boolean open_output and input bit 0/1")
    g = protocol_geometry(distance)
    indices = {(p, q): i for i, (p, q) in enumerate((p, q) for p in PATCHES for q in g.sites)}
    moments = []

    def moment(actions, active, stage, operations):
        used = [q for a in actions for q in a.targets]
        if len(used) != len(set(used)):
            raise AssertionError(f"Independent schedule overlap in {stage}")
        moments.append(ReferenceMoment(tuple(actions), tuple(active), stage, operations))

    def init(patches, bases, rounds, active, stage, operations):
        moment(
            [
                Action("RX" if b == "X" else "R", tuple((p, q) for q in g.data), operations[p])
                for p, b in zip(patches, bases, strict=True)
            ],
            active,
            stage,
            operations,
        )
        for r in range(1, rounds + 1):
            moment(
                [
                    Action(
                        "RX" if b == "X" else "R",
                        tuple((p, c.coordinate) for c in g.checks if c.basis == b),
                        operations[p],
                    )
                    for p in patches
                    for b in "XZ"
                ],
                active,
                stage,
                operations,
            )
            for layer in range(4):
                actions = []
                for p in patches:
                    pairs = []
                    for c in g.checks:
                        dx, dy = DIRECTIONS[c.basis][layer]
                        q = c.coordinate[0] + dx, c.coordinate[1] + dy
                        if q in c.support:
                            pairs.extend(
                                ((p, c.coordinate), (p, q))
                                if c.basis == "X"
                                else ((p, q), (p, c.coordinate))
                            )
                    actions.append(Action("CX", tuple(pairs), operations[p]))
                moment(actions, active, stage, operations)
            moment(
                [
                    Action(
                        "MX" if b == "X" else "M",
                        tuple((p, c.coordinate) for c in g.checks if c.basis == b),
                        operations[p],
                        tuple(check_key(p, c, r) for c in g.checks if c.basis == b),
                    )
                    for p in patches
                    for b in "XZ"
                ],
                active,
                stage,
                operations,
            )

    init(("D",), (basis,), 1, ("D",), "D.init", {"D": "D.init"})
    if bit:
        # A logical anticommuting string changes only the desired eigenvalue.
        gate = "Z" if basis == "X" else "X"
        moment(
            [Action(gate, tuple(("D", q) for q in g.logical(gate)), "D.input_bit")],
            ("D",),
            "D.input_bit",
            {"D": "D.input_bit"},
        )
    first_resource = len(moments)
    init(("A", "B"), ("X", "Z"), distance, PATCHES, "A/B.prep", {"A": "A.prep", "B": "B.prep"})
    resource_boundary = len(moments) - 1
    for control, target, stage in (("A", "B", "Bell.entangle"), ("D", "A", "Bell.measure.cnot")):
        moment(
            [Action("CX", tuple(s for q in g.data for s in ((control, q), (target, q))), stage)],
            PATCHES,
            stage,
            {control: stage, target: stage},
        )
    moment(
        [
            Action(
                "MX",
                tuple(("D", q) for q in g.data),
                "D.bell_readout",
                tuple(readout_key("D", "X", q) for q in g.data),
            ),
            Action(
                "M",
                tuple(("A", q) for q in g.data),
                "A.bell_readout",
                tuple(readout_key("A", "Z", q) for q in g.data),
            ),
        ],
        PATCHES,
        "Bell.readout",
        {"D": "D.bell_readout", "A": "A.bell_readout"},
    )
    if not open_output:
        moment(
            [
                Action(
                    "MX" if basis == "X" else "M",
                    tuple(("B", q) for q in g.data),
                    "B.readout",
                    tuple(readout_key("B", basis, q) for q in g.data),
                )
            ],
            ("B",),
            "B.readout",
            {"B": "B.readout"},
        )
    circuit = stim.Circuit()
    for (p, q), i in indices.items():
        circuit.append("QUBIT_COORDS", [i], absolute_coordinate(distance, p, q))
    records = {}
    for t, m in enumerate(moments):
        for a in m.actions:
            circuit.append(a.gate, [indices[q] for q in a.targets])
            for key in a.keys:
                records[key] = len(records)
        if t < len(moments) - 1:
            circuit.append("TICK")
    anchors, observables = _expected_annotations(g, basis, records, open_output)
    keys = sorted(records)
    for name, row in [("DETECTOR", r) for _, r in sorted(anchors.items())] + [
        ("OBSERVABLE_INCLUDE", r) for _, r in sorted(observables.items())
    ]:
        targets = [
            stim.target_rec(records[k] - len(records)) for i, k in enumerate(keys) if (row >> i) & 1
        ]
        circuit.append(name, targets, [] if name == "DETECTOR" else [0])
    return ReferenceBundle(
        circuit,
        g,
        MappingProxyType(indices),
        MappingProxyType(records),
        tuple(moments),
        tuple(r for _, r in sorted(anchors.items())),
        MappingProxyType(observables),
        MappingProxyType(anchors),
        resource_boundary,
        first_resource,
        open_output,
        basis,
        bit,
    )


def signed_measurement_constraints(bundle):
    """Complete affine relations by signed Stim-flow symplectic elimination.

    The sign is column ``len(records)`` after the canonical semantic records.
    Multiplication uses Stim's exact Pauli phases, including anticommuting
    factors; eliminating unsigned supports alone would lose those signs.
    """
    from validation.golden_memory.normalize import row_space

    width = bundle.circuit.num_qubits
    canonical = {key: i for i, key in enumerate(bundle.canonical_keys)}
    raw_keys = tuple(sorted(bundle.records, key=bundle.records.get))
    pivots, relations = {}, []

    def symplectic_bits(flow):
        bits = 0
        for pauli in (flow.input_copy(), flow.output_copy()):
            for i in range(width):
                bits = (bits << 2) | (0, 1, 3, 2)[pauli[i]]
        return bits

    for generator in bundle.circuit.flow_generators():
        pin, pout = generator.input_copy(), generator.output_copy()
        pin += stim.PauliString(width - len(pin))
        pout += stim.PauliString(width - len(pout))
        flow = stim.Flow(input=pin, output=pout, measurements=generator.measurements_copy())
        bits = symplectic_bits(flow)
        while bits:
            pivot = bits.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (bits, flow)
                break
            other_bits, other_flow = pivots[pivot]
            bits ^= other_bits
            flow *= other_flow
        if bits:
            continue
        if not bundle.circuit.has_flow(flow):
            raise AssertionError(f"Independent signed eliminated relation fails: {flow}")
        row = _parity(canonical[raw_keys[i]] for i in flow.measurements_copy())
        sign = int(flow.input_copy().sign != flow.output_copy().sign)
        relations.append(row | (sign << len(raw_keys)))
    return row_space(relations)


def verify_annotation_semantics(bundle):
    """Prove each authored anchor and the complete signed relation space."""
    from validation.golden_memory.normalize import row_space

    n = len(bundle.records)
    raw_keys = tuple(sorted(bundle.records, key=bundle.records.get))
    columns = {key: i for i, key in enumerate(bundle.canonical_keys)}
    rows = list(bundle.annotation_rows)
    rows.extend(row | (bundle.bit << n) for row in bundle.observables.values())
    for row in rows:
        flow = stim.Flow(
            measurements=[i for i, key in enumerate(raw_keys) if (row >> columns[key]) & 1],
            output=stim.PauliString("-" if (row >> n) & 1 else "+"),
        )
        if not bundle.circuit.has_flow(flow):
            raise AssertionError(f"Independent mathematical annotation fails signed flow: {flow}")
    actual = signed_measurement_constraints(bundle)
    expected = row_space(rows)
    if actual != expected:
        raise AssertionError(
            "Independent anchors/observable do not span complete signed "
            f"relations: expected rank={len(expected)} actual={len(actual)}"
        )
    return {
        "signed_anchor_checks": len(rows),
        "affine_rank": len(actual),
        "free_record_dimension": n - len(actual),
        "detector_rank": len(row_space(bundle.annotation_rows)),
    }
