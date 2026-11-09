"""Export the exact memory and Knill example circuits as inspectable Stim text.

Run: python examples/export_stim_circuits.py
Files are written beside this script, independently of the current directory.
"""

from pathlib import Path

import stim

try:
    from .knill_ec_single_round import main as knill_example
    from .two_patch_memory import main as memory_example
except ImportError:  # Direct execution from the examples directory.
    from knill_ec_single_round import main as knill_example
    from two_patch_memory import main as memory_example


def main():
    memory = memory_example()
    opened, closed = knill_example()
    directory = Path(__file__).resolve().parent
    for stem, compiled in (
        ("two_patch_memory", memory),
        ("knill_ec_single_round.open", opened),
        ("knill_ec_single_round.closed", closed),
    ):
        for kind, circuit in (("ideal", compiled.ideal_circuit), ("noisy", compiled.noisy_circuit)):
            text = str(circuit) + "\n"
            if stim.Circuit(text) != circuit:
                raise ValueError(f"Stim text would lose circuit precision: {stem}.{kind}")
            path = directory / f"{stem}.{kind}.stim"
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"Exported {path.name}: {len(text.splitlines())} lines")


if __name__ == "__main__":
    main()
