"""Thin extraction of actual, unmodified pinned Hex circuit constructors.

Normal validation loads reviewed fixtures and needs neither Hex nor its decoder
dependencies. Only explicit fixture maintenance imports the local upstream tree.
Decoder callbacks are zero stubs used to satisfy constructors; their output is
never consumed by the independent physical oracle.
"""

import hashlib
import importlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import stim

from validation.golden_memory.normalize import require

HEX_COMMIT = "5de58f2f80791054411ad3c0885a4fe3671ed56a"
SECTION_NAMES = ("input", "prep_A", "prep_B", "entangle", "bell_measure", "readout")


@dataclass
class HexBundle:
    distance: int
    basis: str
    bit: int
    sections: dict[str, stim.Circuit]
    matrices: dict[str, np.ndarray]
    blocks: dict[str, dict[str, list[int]]]
    correction_array: list
    provenance: dict

    @property
    def open_circuit(self):
        result = stim.Circuit()
        for name in SECTION_NAMES[:-1]:
            result += self.sections[name]
        return result

    @property
    def circuit(self):
        return self.open_circuit + self.sections["readout"]

    @property
    def closed_circuit(self):
        return self.circuit

    @property
    def data_supports(self):
        return {role: tuple(block["data_qubits"]) for role, block in self.blocks.items()}


def _zero_decoder(matrix):
    """Constructor-only no-op, with the legacy ndarray interface Hex expects."""
    width = matrix.shape[1]

    class ZeroDecoder:
        def decode(self, syndromes):
            syndromes = np.asarray(syndromes)
            return np.zeros((*syndromes.shape[:-1], width), dtype=np.int8)

        decode_batch = decode

    return ZeroDecoder()


def extract_hex(distance, basis, bit=0, hex_repo=None):
    """Call pinned Hex public primitives; explicitly select its hook-aware SE."""
    require(
        distance in (3, 5) and basis in ("X", "Z") and bit in (0, 1),
        "Hex case outside certification",
    )
    repo = (
        Path(hex_repo) if hex_repo else Path(__file__).resolve().parents[2] / "external_lib" / "Hex"
    )
    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    require(
        commit == HEX_COMMIT, f"Hex extraction requires pinned revision {HEX_COMMIT}, got {commit}"
    )
    require(
        not subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True),
        "Hex upstream tree is modified",
    )
    source = repo / "src"
    sys.path.insert(0, str(source))
    try:
        cg = importlib.import_module("hex_qec.circuit_generation.circuit_generation")
        mg = importlib.import_module("hex_qec.modularisation.module_generation")
        modules = importlib.import_module("hex_qec.modularisation.modularised_circuit")
        require(
            Path(cg.__file__).resolve().is_relative_to(source.resolve()),
            "Imported a different Hex installation",
        )
        parity = cg.get_parity_check_matrices("surface", distance)
        template, _, _, _ = cg.create_stabilizers_and_block_template(*parity)
        blocks = dict(zip(("D", "A", "B"), cg.generate_blocks(3, template), strict=True))
        input_circuit = cg.noiseless_unitary_state_prep(parity, basis.lower(), eigenvalue=bit)
        input_module = modules.no_measurement_module(input_circuit, blocks["D"]["data_qubits"])
        sections = {"input": input_module.circuit}
        for role, pauli in (("A", "z"), ("B", "x")):
            local = cg.stabilizer_measurement_circuit_both_detectors(
                parity, pauli=pauli, syndrome_repetitions=distance, prob=0, surface_code=True
            )
            # Use Hex's original support remapper without constructing a DEM/decoder.
            support = sum(
                (blocks[role][k] for k in ("data_qubits", "x_ancillas", "z_ancillas")), []
            )
            remapped = modules.measurement_module(
                local, lambda samples: np.zeros((len(samples), 0), dtype=np.uint8), [], support
            )
            sections[f"prep_{role}"] = remapped.circuit
        sections["entangle"] = mg.generate_transversal_cnot_module(
            0, blocks["B"]["data_qubits"], blocks["A"]["data_qubits"]
        ).circuit
        bell = mg.generate_bell_measurement_and_correction_module(
            parity,
            0,
            blocks["D"]["data_qubits"],
            blocks["A"]["data_qubits"],
            blocks["B"]["data_qubits"],
            _zero_decoder,
        )
        sections["bell_measure"] = bell.circuit
        sections["readout"] = mg.generate_logical_measurement_module(
            parity, 0, basis.lower(), blocks["B"]["data_qubits"], _zero_decoder
        ).circuit
        matrices = {
            key: np.asarray(value.toarray(), dtype=np.uint8) % 2
            for key, value in zip(("X", "Z", "LX", "LZ"), parity, strict=True)
        }
        files = [Path(cg.__file__), Path(mg.__file__), Path(modules.__file__)]
        files += sorted(
            (source / "hex_qec/circuit_generation/parity_check_matrices/surface").glob(
                f"surface_{distance**2}_1_{distance}_*.mtx"
            )
        )
        hashes = {
            str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }
        provenance = {
            "repository": "https://github.com/AKTKN/Hex.git",
            "commit": commit,
            "version": "0.1.0",
            "surface_code": True,
            "source_sha256": hashes,
            "decoder": "constructor-only zero stub; never oracle truth",
            "resource_control": "B",
            "resource_target": "A",
        }
        return HexBundle(
            distance, basis, bit, sections, matrices, blocks, bell.correction_array, provenance
        )
    finally:
        sys.path.remove(str(source))


def bundle_to_dict(bundle):
    """JSON-safe complete upstream extraction, including exact section text."""
    return {
        "schema": 1,
        "distance": bundle.distance,
        "basis": bundle.basis,
        "bit": bundle.bit,
        "sections": {name: str(bundle.sections[name]) for name in SECTION_NAMES},
        "matrices": {key: value.tolist() for key, value in bundle.matrices.items()},
        "blocks": bundle.blocks,
        "correction_array": bundle.correction_array,
        "provenance": bundle.provenance,
    }


def bundle_from_dict(data):
    require(
        data["schema"] == 1
        and data["provenance"]["commit"] == HEX_COMMIT
        and data["provenance"]["surface_code"] is True,
        "Invalid Hex fixture provenance",
    )
    return HexBundle(
        data["distance"],
        data["basis"],
        data["bit"],
        {key: stim.Circuit(value) for key, value in data["sections"].items()},
        {key: np.asarray(value, dtype=np.uint8) for key, value in data["matrices"].items()},
        data["blocks"],
        data["correction_array"],
        data["provenance"],
    )


def load_hex_bundle(path):
    return bundle_from_dict(json.loads(Path(path).read_bytes()))


def save_hex_bundle(bundle, path):
    Path(path).write_bytes(
        (json.dumps(bundle_to_dict(bundle), indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
