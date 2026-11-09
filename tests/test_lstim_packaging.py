"""Real built distributions consumed away from the checkout on Linux and Windows."""

import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from tests.helpers.package_build import copy_package_source

CONSUMER = r'''
import importlib.abc
import pathlib
import sys
from importlib.metadata import distribution
from importlib.resources import files

installed, checkout, build_tree, samples = map(pathlib.Path, sys.argv[1:])
sys.path[:] = [p for p in sys.path if p and pathlib.Path(p).resolve() not in {
    checkout, checkout / 'src', build_tree, build_tree / 'src',
}]
sys.path.insert(0, str(installed))

class NoOptionalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {
            'examples', 'tests', 'external_lib', 'pymatching', 'matplotlib',
            'knill_bench', 'surface_sim', 'lomatching', 'hex',
        }:
            raise AssertionError('installed API imported ' + fullname)

sys.meta_path.insert(0, NoOptionalImports())
import logical_to_stim_converter as package
from logical_to_stim_converter import (
    CompiledCircuit, LogicalProgram, NoiseModel, format_logical_circuit,
    ResourcePreparationNoise, parse_logical_circuit, parse_logical_file,
)
assert pathlib.Path(package.__file__).is_relative_to(installed)
installed_distribution = distribution('logical-to-stim-converter')
assert installed_distribution.version == '0.0.1'
assert pathlib.Path(installed_distribution.locate_file('')).resolve() == installed.resolve()
grammar = files('logical_to_stim_converter.language').joinpath('grammar.lark')
assert 'start:' in grammar.read_text(encoding='utf-8')
for name, width in [('memory_d3.lstim', 17), ('three_patch_knill_d3.lstim', 51)]:
    path = samples / name
    program = parse_logical_file(path)
    assert isinstance(program, LogicalProgram) and program.source_name == str(path)
    text = format_logical_circuit(program)
    assert text == path.read_text(encoding='utf-8')
    reparsed = parse_logical_circuit(text, source_name='roundtrip.lstim')
    assert reparsed.to_operations() == program.to_operations()
    first = program.compile(noise_model=NoiseModel.uniform_depolarizing(0.001))
    second = reparsed.compile(noise_model=NoiseModel.uniform_depolarizing(0.003))
    assert type(first) is CompiledCircuit and type(second) is CompiledCircuit
    assert first.circuit.num_qubits == width
    assert first.ideal_circuit == second.ideal_circuit and first.circuit != second.circuit
    first.validate_metadata()
    first.circuit.detector_error_model()
    assert first.make_decoder_view() is not None and first.make_frame_plan() is not None
    events, obs = first.ideal_circuit.compile_detector_sampler(seed=87).sample(
        4, separate_observables=True,
    )
    assert not events.any() and not obs.any()
    if width == 51:
        from logical_to_stim_converter.decoding import make_stage_requests
        assert make_stage_requests(first) is not None
        assert tuple(program.label_spans) == ('cycle0', 'cycle1', 'cycle2')
        for label, span in program.label_spans.items():
            assert program.source[span.start_offset:span.end_offset].startswith('KNILL_EC[' + label)
            assert any(c.composite_id == label for c in first.composites)
            assert any(label in f.composite_ids for f in first.fragments)
        assert first.logical_to_block['D'] == 'P0'
        special = program.compile(noise_model=NoiseModel(
            resource_preparation=ResourcePreparationNoise(True, .003)))
        assert special.ideal_circuit == first.ideal_circuit
        special.validate_metadata()
        assert len(special.resource_preparation_boundaries) == 6
        assert sum(len(special.circuit[b.channel_instruction].targets_copy())
                   for b in special.resource_preparation_boundaries) == 54
        from logical_to_stim_converter.decoding import make_conditional_readout_model
        assert len(make_stage_requests(special).boundaries) > 6
        for bell in special.bell_measurements:
            model = make_conditional_readout_model(special, bell)
            assert 'before post-SE' in model.boundary_convention
            assert len(model.faults) == 54
for name, module in tuple(sys.modules.items()):
    if name == 'logical_to_stim_converter' or name.startswith('logical_to_stim_converter.'):
        assert pathlib.Path(module.__file__).is_relative_to(installed), (name, module.__file__)
print('installed public API and both source samples passed')
'''


def test_wheel_sdist_and_installed_public_api_without_checkout_or_optional_imports(tmp_path):
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    def check_metadata(contents):
        metadata = BytesParser().parsebytes(contents)
        assert metadata["Name"] == project["name"] == "logical-to-stim-converter"
        assert metadata["Version"] == project["version"] == "0.0.1"
        assert metadata["Requires-Python"] == project["requires-python"]
        assert metadata["License"] is None and metadata["License-Expression"] is None
        runtime = [r for r in metadata.get_all("Requires-Dist", []) if ";" not in r]
        assert sorted(r.replace(" ", "") for r in runtime) == sorted(
            r.replace(" ", "") for r in project["dependencies"]
        )

    source = copy_package_source(tmp_path / "source")
    dist = tmp_path / "dist"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist)],
        cwd=source, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheel, = dist.glob("*.whl")
    sdist, = dist.glob("*.tar.gz")
    grammar = "logical_to_stim_converter/language/grammar.lark"
    expected = (root / "src" / grammar).read_bytes()
    with tarfile.open(sdist) as archive:
        prefix = archive.getmembers()[0].name.split("/")[0]
        check_metadata(archive.extractfile(prefix + "/PKG-INFO").read())
        assert archive.extractfile(prefix + "/src/" + grammar).read() == expected
        contract = archive.extractfile(prefix + "/docs/lstim_v1.md").read().decode("utf-8")
        for name in ("memory_d3.lstim", "three_patch_knill_d3.lstim"):
            example = (root / "examples/lstim" / name).read_bytes()
            assert archive.extractfile(prefix + "/examples/lstim/" + name).read() == example
            assert example.decode("utf-8").rstrip("\n") in contract
    installed = tmp_path / "installed"
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read(grammar) == expected
        assert not any(name.startswith(("tests/", "examples/", "external_lib/"))
                       for name in archive.namelist())
        metadata, = (name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        check_metadata(archive.read(metadata))
        assert "Requires-Dist: lark==1.3.1" in archive.read(metadata).decode("utf-8")
        for name in archive.namelist():
            if name.startswith("logical_to_stim_converter/") and name.endswith((".py", ".lark")):
                assert archive.read(name) == (root / "src" / name).read_bytes()
        archive.extractall(installed)
    # Only two input files accompany the wheel; no example Python modules are copied.
    samples = tmp_path / "inputs"
    samples.mkdir()
    for name in ("memory_d3.lstim", "three_patch_knill_d3.lstim"):
        (samples / name).write_bytes((root / "examples/lstim" / name).read_bytes())
    consumer_cwd = tmp_path / "consumer"
    consumer_cwd.mkdir()
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", CONSUMER,
         str(installed), str(root), str(source), str(samples)],
        cwd=consumer_cwd, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "installed public API and both source samples passed" in result.stdout
