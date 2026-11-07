# STATUS — Package root

## M6-B update — 2026-11-08

Public DecoderView/DetectorSelector/DEMOptions, GF2Map/RecordFlipMap, factories,
observable-local selections and record XOR transforms now expose decoder-neutral
offline inputs. Mapping/input/audit/error types and source_fingerprint are public
in decoding. Principal circuits remain complete and unchanged; every local DEM
is re-extracted from the same physical instructions/noise. Actual detector basis
and full underlying data support are public. No runtime decoder or runner added.
See README/architecture and root STATUS for tested contracts and limitations.

## M6-A update — 2026-11-08

Public exports now include global measurement/detector/observable metadata,
DetectorBoundaryCandidate, PreparationDependencyEvent, PreparationInfo,
LogicalReadout, BellMeasurementResult and RelocationRecord. Compiled artifacts
retain canonical full circuits, immutable semantic record mappings, causal
preparation histories, explicit legacy stage views and their global detector IDs.
Strict noiseless frame proof is separate from well-formed noisy hypothesis replay.
The read-only suppressed_detectors alias now identifies present boundary candidates.
Migration and exact verification are documented in README and root STATUS.
No runtime decoder or knill_bench dependency was added.

## M5 update — 2026-11-07

Public exports now include CompositeOperation, BellStatePrep, KnillEC, and
PhysicalPauliFrame. Existing memory/Clifford APIs are preserved. CompiledCircuit
exports preparations/readouts/Bell results, detector stages and excluded relations,
relocation history, current/open mappings, and open flow interfaces. External
physical corrections enter evaluate_frames; no production decoder is imported.
PyMatching 2.3.1 belongs only to the development extra and required CI tests.
See root STATUS for exact executed verification and remaining limits.

**2026-11-07:** The top-level public memory/Clifford API exports CodeSpec, PhysicalLayout,
LogicalBlock, CodeBackend, CompilerContext, ModuleFragment,
RotatedSurfaceCodeBackend, OperationModule, LogicalInit, SyndromeExtraction,
LogicalMeasure, CircuitCompiler, CompiledCircuit, NoiseModel, NoiseParameters,
NoiseOverride, NoiseInjector, TransversalH, TransversalCNOT, LogicalPauli,
OperationContext, PauliFrame, and ParityExpression.

Required pinned dependencies are Stim 1.15.0 and stimflow at Stim commit
`ffe0d043598ed5df0851a3e6b4920359a23fafbd`. There are no machine-specific paths
or imports from external source copies. Surface-sim, Hex, lomatching, and
knill_bench are not runtime dependencies.

Evidence and limitations are recorded in root STATUS and per-component ledgers.
Dedicated Bell/Knill, other code-family, and decoder modules remain placeholders. History:
initially a docstring-only scaffold on 2026-11-07; memory-core task introduces the
first physics API and its tests. No general-purpose logical compiler is claimed.

M3 validation: 173-test extended suite plus Ruff/build/example checks recorded in
root STATUS. Logical Cliffords are H/CNOT/Pauli only; no broader API is claimed.
