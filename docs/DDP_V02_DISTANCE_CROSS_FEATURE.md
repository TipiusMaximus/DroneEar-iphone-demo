# DroneEar DDP v0.2 — distance + cross-feature research note

## Baseline

The external audit of v0.1 concluded:

```text
DDP_RESULT = NO_CLEAR_GAIN
```

This is the baseline for v0.2. The goal is not to improve the old score by retuning it.

## Why distance matters

With increasing distance, acoustic drone observations can change in several ways at once:

- level decreases;
- high-frequency energy tends to become less available before lower-frequency energy;
- low frequencies can become masked by traffic, wind and machinery;
- visible harmonic count can fall;
- harmonic peaks can broaden or become unstable;
- direct/reflected path interference can reshape the spectrum;
- slow propagation/wind fluctuations can modulate amplitude;
- source orientation and motion can alter the spectrum;
- Doppler can shift tonal components during flyby;
- device gain/processing can change the observation further.

Therefore a useful distance-tolerant signature may be a *relationship* between observables rather than one absolute spectrum.

## v0.2 observables

The research detector exports:

```text
fundamental search: 40–800 Hz
analysis spectrum:   40–8000 Hz
```

Band features:

```text
40–120
120–250
250–500
500–1000
1000–2000
2000–4000
4000–8000 Hz
```

Temporal / structural features:

```text
spectral flux
spectral centroid
spectral flatness
amplitude envelope
envelope delta
modulation depth
sideband ratio
high-frequency share
low-frequency share
```

These are added to the previous harmonic detector features.

## Cross-feature DDP hypothesis

Same-feature v0.1 effectively asked questions like:

```text
is harmonic_score still structured D frames later?
```

v0.2 additionally asks questions such as:

```text
if f0 changes, does harmonic contrast respond later?
if amplitude changes, does sideband structure respond later?
does modulation depth covary with sideband energy?
does high-frequency loss alter harmonic score in a repeatable delayed way?
```

The experimental cross-feature equation is:

```text
delayed_source = source(t-D)
target_gradient = diff(target)(t-D)
score = polarity(delayed_source) ×
        (delayed_source + g × target_gradient)
```

This is a research extension and is not presented as the original Universal DDP formula.

## Mandatory ablation

Every cross-feature pair is tested with:

```text
g = 0
```

and positive gain values.

Interpretation:

```text
g=0   delayed source only
g>0   target gradient is active
```

If `g>0` does not improve held-out discrimination or robustness over `g=0`, cross-feature DDP has not demonstrated added value.

## Distance stress generator

The synthetic distance generator combines:

```text
attenuation
low-pass degradation
background noise
simple delayed reflection / comb filtering
slow amplitude fluctuation
```

The presets `near`, `mid`, and `far` are deliberately qualitative. They do not correspond to claimed metre distances.

The primary use is feature survival analysis:

```text
which features collapse?
which remain structured?
which relationships remain stable?
```

## Methodological corrections after v0.1 audit

- v0.2 isolated D/g points are flagged `isolated`, not `robust`.
- real runs support `--exclude-synthetic`.
- normalized and raw-scale arms are both available.
- cross-feature pairs are predeclared rather than exhaustively data-mined.
- g=0 is kept as a mandatory baseline.
- adjacent clips from one recording must be treated as dependent evidence.
- in-sample AUC remains a discovery ranking only.

## One-click runs

```text
RUN_DDP_V02_SYNTHETIC.bat
RUN_DDP_V02_DISTANCE.bat
RUN_DDP_V02_SMALL_REAL.bat
```

Each produces a Markdown report plus CSV signatures/rankings/motifs.

## Next falsification step

After the local/small-real passes, lock a small parameter shortlist **before** opening hard negatives.

Recommended negative classes:

```text
helicopter
engine
chainsaw
vacuum_cleaner
washing_machine
airplane
wind
insects
```

Then compare:

```text
A: base p95(harmonic_score)
B: same-feature DDP, g=0
C: same-feature DDP, g>0
D: cross-feature DDP, g=0
E: cross-feature DDP, g>0
```

Only D/E are interesting as new information if they beat the relevant g=0 controls and the base detector on held-out hard negatives.

## Outcome rule

The intended result labels remain:

```text
PROMISING
WEAK_COMPLEMENT
NO_CLEAR_GAIN
INVALID_EXPERIMENT
```

`NO_CLEAR_GAIN` remains a fully valid result.
