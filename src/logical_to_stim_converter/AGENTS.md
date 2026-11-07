# AGENTS.md — Python package root

The public memory/Clifford API is exported from `__init__.py`: code/layout/block models,
backend/context/fragment contracts, memory operations, H/CNOT/Pauli primitives, ordered operand contexts, affine frames,
compiler/artifact, and noise types. Stim/stimflow are pinned required dependencies. Surface-sim,
Hex, lomatching, and knill_bench must not be imported here. BellStatePrep, KnillEC, CompositeOperation, and PhysicalPauliFrame are public. Do not export future
placeholder operations until implemented with physics tests. Preserve the `src/`
layout and consult per-directory AGENTS/STATUS before changes.

M6-A exports global MeasurementInfo/MeasurementKey/DetectorInfo/ObservableInfo,
DetectorBoundaryCandidate, PreparationDependencyEvent, PreparationInfo,
LogicalReadout, BellMeasurementResult, and RelocationRecord at package level.
Keep principal compiled circuits complete and legacy stage separation explicit.
