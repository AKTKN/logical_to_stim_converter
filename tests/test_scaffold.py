"""Package import smoke test; physics is covered in the memory tests."""

import logical_to_stim_converter


def test_package_imports() -> None:
    assert logical_to_stim_converter.__name__ == "logical_to_stim_converter"
