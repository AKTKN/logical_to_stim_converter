"""Smoke test: installing this scaffold makes the package importable."""

import logical_to_stim_converter


def test_package_imports_without_public_api() -> None:
    assert logical_to_stim_converter.__name__ == "logical_to_stim_converter"
