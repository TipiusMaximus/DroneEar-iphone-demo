# DroneEar × Universal DDP — research branch

**Branch:** `ddp_haara`  
**Current research version:** v0.2  
**Runtime product impact:** none; `index.html` and `dsp.js` remain untouched.

## Why v0.2 exists

The v0.1 audit produced:

```text
DDP_RESULT = NO_CLEAR_GAIN
```

That result is kept as the baseline rather than hidden or retuned away.

The main v0.1 findings were:

- top results were mostly `harmonic_score`, `raw_score`, `smoothed_score` and related detector state;
- many top parameter sets used `g=0`, so the DDP gradient term was not adding information;
- strongest delays were usually `D=1..2` = 64–128 ms, close to adjacent-frame smoothness;
- synthetic base detector separation was much larger than the derived DDP structure margin;
- real-only evidence had only one noise-floor negative;
- the official small-real manifest mixed synthetic and real examples;
- within-clip z-score could hide absolute level differences that naturally change with distance;
- isolated parameter points could be over-promoted in v0.1 robustness logic.

v0.2 therefore does **not** try to rescue v0.1 by retuning thresholds. It changes the research question.

## v0.2 research question

Can DroneEar find temporal relationships between **different acoustic observables** that:

1. remain meaningful as distance changes;
2. are not just a monotone transformation of `harmonic_score`;
3. survive comparison with `g=0` delayed-source ablations;
4. eventually fail on fewer hard mechanical negatives than the base detector?

Pipeline:

```text
WAV
 ↓
4096 / 1024 STFT + existing detector
 ↓
┌──────────────────────────────────────┐
│ harmonic features                    │
│ f0 / f0_delta                        │
│ narrow frequency-band ratios         │
│ spectral centroid / flatness / flux  │
│ amplitude envelope / envelope delta  │
│ modulation depth                     │
│ sideband ratio                       │
│ high / low frequency share           │
└──────────────────┬───────────────────┘
                   ↓
        same-feature DDP baseline
                   +
        cross-feature DDP v0.2
                   ↓
         g=0 vs g>0 ablation
                   ↓
      robustness / consensus / motifs
```

## Research frequency coverage

The browser detector is not changed by this branch.

The Python research detector now searches candidate fundamentals over:

```text
40–800 Hz
```

The analysed spectrum extends to the 16 kHz sample rate Nyquist limit:

```text
8 kHz
```

Distance-oriented bands are exported separately:

```text
40–120 Hz
120–250 Hz
250–500 Hz
500–1000 Hz
1000–2000 Hz
2000–4000 Hz
4000–8000 Hz
```

This prevents the DDP study from assuming that the useful structure must live below the old 400 Hz fundamental-search ceiling.

## Why distance changes the feature set

A farther drone does not simply become a quieter copy of a near drone.

Expected propagation / measurement effects include:

- overall level loss;
- stronger relative loss of high-frequency content;
- low-frequency components becoming masked by environmental noise;
- fewer clearly visible harmonics;
- broader / less stable spectral peaks;
- direct + reflected path comb filtering;
- slow amplitude fluctuation from wind / propagation;
- orientation and motion changes;
- possible Doppler shift during approach / departure;
- microphone gain / processing effects.

The v0.2 features therefore include both absolute and relative observables.

## New distance/modulation features

`ddp_experiment/spectral_features.py` adds:

```text
spectral_centroid_hz
spectral_flatness
spectral_flux
amplitude_envelope
envelope_delta
modulation_depth
sideband_ratio
low_frequency_share
high_frequency_share
band_40_120_ratio
band_120_250_ratio
band_250_500_ratio
band_500_1000_ratio
band_1000_2000_ratio
band_2000_4000_ratio
band_4000_8000_ratio
```

`sideband_ratio` measures broad energy beside harmonic cores. It is **not** a claim that sidebands uniquely identify drones; engines, reflections and other rotating systems can also produce them.

## Cross-feature DDP

v0.2 keeps the original same-feature DDP as a baseline but adds a deliberately small, predeclared cross-feature set.

For source feature `x` and target feature `y`:

```text
delayed_source = x(t-D)
target_gradient = diff(y)(t-D)
score = polarity(delayed_source) ×
        (delayed_source + g × target_gradient)
```

This is an **experimental extension**, not a claim about the original Universal DDP formula.

Most important rule:

```text
g = 0
```

means the target-feature gradient contributes nothing.

Therefore a cross-feature result is interesting only if `g>0` adds something reproducible beyond the corresponding `g=0` baseline.

Default cross-feature pairs:

```text
f0_delta -> harmonic_contrast_db
amplitude_envelope -> sideband_ratio
sideband_ratio -> harmonic_score
modulation_depth -> sideband_ratio
spectral_flux -> harmonic_contrast_db
high_frequency_share -> harmonic_score
low_frequency_share -> harmonic_score
band_40_120_ratio -> band_500_1000_ratio
band_120_250_ratio -> band_1000_2000_ratio
```

The list is intentionally small to reduce parameter fishing.

## Distance stress simulation

`ddp_experiment/distance_simulation.py` provides controlled synthetic stress variants.

It combines:

```text
attenuation
progressive low-pass
background masking noise
simple reflected-path comb filtering
slow gain fluctuation
```

Presets:

```text
near
mid
far
```

This is **not** an atmospheric propagation solver and does not map to a reliable physical distance in metres. It is only a robustness test asking which features survive plausible degradation mechanisms.

Build the benchmark:

```powershell
python tools\generate_synthetic.py
python tools\build_distance_benchmark.py
```

## Audit fixes / guardrails

v0.2 includes these methodological changes:

### Isolated parameter handling

A D/g point with no neighbours is:

```text
isolated
```

not automatically `robust`, even if its in-sample AUC is perfect.

### Real-only ranking

Use:

```text
--exclude-synthetic
```

when evaluating the 1/10/30 m research recordings. This prevents the synthetic harmonic controls from silently influencing the real ranking.

### Normalized vs raw-scale ablation

Every one-click v0.2 run produces both:

```text
within-clip robust-z normalized
raw-scale
```

runs where appropriate.

This is important because normalization can deliberately remove level information, while physical distance strongly affects level.

### Dependent clips

Adjacent 5 s segments from the same source recording must not be counted as fully independent evidence in scientific interpretation.

### In-sample AUC

AUC in these reports is a discovery ranking, not held-out field accuracy.

## Run v0.2 — synthetic

Double-click:

```text
RUN_DDP_V02_SYNTHETIC.bat
```

Outputs:

```text
outputs/ddp_v02_synthetic/
outputs/ddp_v02_synthetic_raw/
```

## Run v0.2 — distance stress

Double-click:

```text
RUN_DDP_V02_DISTANCE.bat
```

Outputs:

```text
outputs/ddp_v02_distance/
outputs/ddp_v02_distance_raw/
```

## Run v0.2 — small real-only

Double-click:

```text
RUN_DDP_V02_SMALL_REAL.bat
```

The downloader may still create a manifest containing synthetic controls, but the v0.2 runner explicitly excludes them from the ranking.

Outputs:

```text
outputs/ddp_v02_real_only/
outputs/ddp_v02_real_only_raw/
```

## Output files

Each v0.2 output directory contains:

```text
ddp_v02_clip_signatures.csv
ddp_v02_parameter_rankings.csv
ddp_v02_motifs.csv
DDP_V02_EXPERIMENT_REPORT.md
```

The report includes:

- DDP mode (`same_feature` / `cross_feature`);
- source feature;
- target feature;
- delay in frames and milliseconds;
- gain;
- polarity;
- AUC / separation ranking;
- robustness;
- consensus.

## Decision rule for cross-feature DDP

A cross-feature candidate is worth carrying forward only if:

1. `g>0` improves or stabilizes the result compared with the same pair at `g=0`;
2. the result forms a local D/g island rather than a needle-like optimum;
3. it survives normalized and/or raw-scale ablations for a defensible reason;
4. it survives distance degradation;
5. it remains useful on held-out hard negatives such as helicopter / engine / vacuum / chainsaw / airplane / wind;
6. it adds information beyond base detector `p95(harmonic_score)`.

If not, the correct research result remains:

```text
NO_CLEAR_GAIN
```

## Do not overclaim

- DDP scores are not probabilities.
- Synthetic distance variants do not establish range.
- Zenodo 1/10/30 m recordings do not establish iPhone range.
- Cross-feature DDP is an experimental extension.
- No rule should be ported to Safari before hard-negative held-out validation.
