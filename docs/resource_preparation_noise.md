# Opt-in Bell-resource preparation noise (M9)

`ResourcePreparationNoise` is a frozen noise-compilation option. Its default is
`enabled=False`. Existing `NoiseModel()`, `uniform_depolarizing(p)` and ideal
`noise_model=None` compilation retain their previous behavior. The new option
needs an explicit `NoiseModel`; it is not an operation or LSTIM language feature.

```python
from logical_to_stim_converter import (
    NoiseModel, NoiseParameters, ResourcePreparationNoise, parse_logical_file,
)

noise = NoiseModel(
    default=NoiseParameters(
        reset=.001, one_qubit=.001, two_qubit=.001,
        measurement=.001, idle=.001,
    ),
    resource_preparation=ResourcePreparationNoise(
        enabled=True, p_st_transversal=.003,
    ),
)
compiled = parse_logical_file(
    "examples/lstim/three_patch_knill_d3.lstim"
).compile(noise_model=noise)
```

The enable flag must be a boolean. The probability must be finite, numeric,
non-boolean and in the closed interval **[0, 0.75]** for exact native DEM
compatibility. This policy-level limit applies even when `enabled=False` and
without the example CLI. Invalid probabilities and configuration types fail at
construction with `ValueError`; nothing is clamped, rescaled or approximated.
`enabled=True, p_st_transversal=0` still makes the resource
initialization ideal; it emits no post-SE stochastic instruction. A nonzero
probability with `enabled=False` has no effect. Continuations made with
`CompiledCircuit.append()` retain the complete noise model.

## Physical contract

Eligibility comes from an executed `BellStatePrep` composite. This includes a
Bell preparation nested in `KnillEC(prepare_resource=True)`, a standalone Bell
experiment and a separately prepared resource later consumed by
`KnillEC(prepare_resource=False)`. The latter Knill call adds no preparation or
phantom channel. Bare `LogicalInit` operations followed by a manually authored
CNOT do not opt in.

For each eligible composite, only its X-initialized and Z-initialized resource
`LogicalInit` primitives are noiseless: all their data/ancilla resets, SE gates,
measurement result flips and data/ancilla idle channels are suppressed from their
actual first reset layer through their actual final SE measurement layer,
inclusive. This takes precedence over positive global, primitive-type and
inherited composite/instance overrides within that interval.

Immediately after that final layer's idle accounting and its existing `TICK`,
before the resource-entangling CNOT, each resource patch receives
`DEPOLARIZE1(p_st_transversal)` on every physical **data site** exactly once.
It implements probabilities `(I,X,Y,Z) = (1-p,p/3,p/3,p/3)` independently on each
target, including when targets share one printed instruction. There is no added
physical `TICK` or duration. Ancillas, the Knill input D and spectators are never
targets. Ordinary background noise remains on D and spectators during resource
preparation. Resource waiting layers after its own final SE, resource and
teleportation CNOTs, destructive readouts and all other operations retain their
ordinary rules and precedence.

The ideal circuit, physical ordering/indices/TICKs, measurement records, canonical
detectors/observables, signed stabilizer flows and logical frames are unchanged.
Random stabilizer-sign sectors still come from the actual recorded measurements;
external frame selection remains necessary. There is no postselection, forced
positive sector, replacement of raw outcomes or synthesized physical correction.

A rotated-surface patch contributes d² data targets. One Bell preparation adds
2d² independent target locations; three d=3 Knill cycles add **54**, across six
resource uses, despite reuse of only P0/P1/P2. At d=5 that count is 150.

## Boundary provenance and offline decoding

`compiled.resource_preparation_boundaries` is an immutable tuple of
`noise.ResourcePreparationBoundary` records. Each records the executed Bell ID,
initialization and resource-CNOT module IDs, `BlockUseId`, first/final SE layers,
exclusive ideal-prefix index, exact data-site keys and optional noisy-channel
instruction index. `channel_tag` uses distinct `resource_post_se:<module>`
stochastic provenance. Layout data IDs and the physical map determine targets;
final logical bindings and stage/name substrings never determine eligibility.
Ambiguous membership, missing uses, duplicate sites/epochs and misplaced channels
fail validation. The resolver runs after ideal metadata/flow validation; the
injector consumes an indexed insertion plan.

Direct public `NoiseInjector.apply()` calls use an explicit presence contract for
`resource_preparation_boundaries`:

- Omitted or `None`: accepted for a disabled policy; an enabled policy raises
  `ValueError` before noise setup, including when the post-SE probability is zero.
- Explicit `()`: declares that there are no eligible Bell preparations and applies
  ordinary background noise, including when the policy is enabled.
- A verified nonempty tuple of `ResourcePreparationBoundary` objects: applies the
  special policy; a disabled policy rejects this contradictory request.

Other container types and invalid tuple elements are rejected. An explicit tuple
is the direct caller's declared boundary plan. The injector cannot establish Bell
composite eligibility from its primitive-only inputs and does not duplicate the
compiler's resolver; use `CircuitCompiler.compile()` to resolve and validate the
complete plan. Standard compilation always supplies an explicit tuple, including
`()` for resource-free programs. Existing duplicate module/use checks remain.

Preparation `BoundaryRequest` model-only probes stop at the existing final-layer
TICK, **before** all post-SE channels. Their temporal models therefore do not own
these faults. The matching conditional Bell model starts at the earliest of its
two explicitly indexed post-SE channels and keeps the original destructive
readout end. Its incoming sector/frame hypothesis applies immediately **before
the post-SE channels**. With no emitted channel the existing resource-CNOT window
and convention are retained. Each depolarizing target has three mutually exclusive
Pauli atoms; raw Bell flips, measured syndromes, logical parities and survivor
physical X/Z support retain their joint action. The model is not a deterministic
Bell DEM, decoder or assertion that an incoming hypothesis is correct.

A separately prepared resource may wait before consumption. The conditional
window includes actual intervening gates and waiting faults. In enabled nonzero
mode, an intervening preparation/SE measurement on D or either resource operand
is explicitly unsupported by the conditional model: it would require an additional
measured-sector/temporal-decoder hypothesis. Construction raises
`UnsupportedProjectionError` rather than silently omitting faults or assigning
them to two modular stages. The canonical physical circuit and its global DEM
remain available. General inference across such intermediate boundaries is deferred.

Decoder views retain all physical channels and re-extract exact marginals with
Stim. Their existing exact snapshots retain full double probabilities and
correlations. Enabled artifacts add the immutable boundary contract under
`resource_preparation_v1` to source fingerprint metadata; disabled v3 source
fingerprints stay unchanged. Cached views/requests/plans from another policy,
probability, boundary or epoch must be regenerated. No runtime decoder dependency
is added; PyMatching and the restricted example adapters remain in dev/examples.

**DEM compatibility:** pinned Stim 1.15.0 cannot extract an exact DEM for an
over-mixing `DEPOLARIZE1(p > 3/4)` channel. The M9 policy therefore rejects these
probabilities at construction. The mathematical channel definition above is
unchanged. Compilation validates the actual noisy circuit directly with Stim;
there is no temporary reweighted circuit or fallback. Unrelated
`NoiseOverride`/`NoiseParameters` channels keep their existing `[0,1]` validation,
and native errors from DEM-incompatible background channels propagate normally.

## Runnable paired example

```sh
python examples/knill_resource_preparation_noise.py --p .001 --p-st .003 --shots 32
```

The example compiles independently authored direct Python operations and the
unchanged three-cycle LSTIM source with the same option. It compares exact
ideal/noisy circuits, DEMs, source identities, same-seed raw records and same-raw
external offline decoding, and reports target counts and finite failure counts.
The existing baseline and replacement adapters are restricted decoders, with no
optimality, threshold or numerical LER guarantee. See root `STATUS.md` for actual
local and CI evidence, including the d=3/5 signed X/Z and physical-fault matrix.
