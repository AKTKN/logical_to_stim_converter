# STATUS — Package root

**2026-11-07:** The top-level public memory API exports CodeSpec, PhysicalLayout,
LogicalBlock, CodeBackend, CompilerContext, ModuleFragment,
RotatedSurfaceCodeBackend, OperationModule, LogicalInit, SyndromeExtraction,
LogicalMeasure, CircuitCompiler, CompiledCircuit, NoiseModel, NoiseParameters,
NoiseOverride, and NoiseInjector.

Required pinned dependencies are Stim 1.15.0 and stimflow at Stim commit
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. There are no machine-specific paths
or imports from external source copies. Surface-sim, Hex, lomatching, and
knill_bench are not runtime dependencies.

Evidence and limitations are recorded in root STATUS and per-component ledgers.
All other operation/code-family/decoder modules remain placeholders. History:
initially a docstring-only scaffold on 2026-11-07; memory-core task introduces the
first physics API and its tests. No general-purpose logical compiler is claimed.
