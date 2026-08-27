# DroneEar × Universal DDP — research experiment v0.1

**Branch:** `ddp_haara`  
**Status:** research-only / offline feature discovery  
**Runtime product impact:** none; `index.html` and the iPhone detector are intentionally untouched.

## Research question

Can the temporal behavior of DroneEar detector features contain repeatable DDP-style structure that:

1. appears across real/synthetic drone clips;
2. survives changes in distance;
3. does not repeat in hard negative mechanical/environmental sounds?

This branch does **not** apply DDP directly to 16 kHz PCM.

Pipeline:

```text
WAV benchmark
    ↓
existing DroneEar 4096/1024 reference detector
    ↓
feature time series (~15.6 frames/s)
    ↓
robust within-clip scaling
    ↓
DDP delay/gain/polarity sweep
    ↓
clip structure signatures
    ↓
drone vs no-drone ranking
    ↓
parameter-neighbor robustness
    ↓
local consensus
    ↓
motif families
```

## Why DDP is used here

The source idea comes from `TipiusMaximus/universal_ddp`.

Its core feedback proxy is:

```text
delayed = signal(t-D)
gradient = diff(signal)(t-D)
feedback = delayed + gain × gradient
score = polarity × feedback
```

The especially useful concepts for DroneEar are not one magic score but:

- sweep multiple delays;
- sweep multiple gains;
- reject isolated parameter spikes;
- reward local parameter-space neighborhoods;
- reward repeatability / consensus;
- aggregate stable patterns into motif families.

A small NumPy port is kept in this repository so the public DroneEar benchmark does not acquire a runtime dependency on the separate private `universal_ddp` repository.

## Input features

Current adapter sends these detector-frame series to DDP:

```text
harmonic_score
harmonic_energy_ratio
harmonic_consistency
harmonic_contrast_db
track_stability
mechanical_band_score
rms
raw_score
smoothed_score
best_f0
f0_delta
```

Each feature is robust-z-scaled inside its own clip before the DDP sweep. The experiment therefore concentrates on temporal shape instead of comparing Hz, dB and RMS units directly.

## Default DDP sweep

One detector hop is currently:

```text
1024 / 16000 = 64 ms
```

Default delays:

```text
D = 1, 2, 4, 8, 16 frames
≈ 64, 128, 256, 512, 1024 ms
```

Gains:

```text
0.0, 0.5, 1.0
```

Polarity rules:

```text
fixed_positive
threshold_switch
```

The first goal is discovery, not exhaustive parameter optimization.

## Outputs

```text
outputs/ddp_experiment/
  ddp_clip_signatures.csv
  ddp_parameter_rankings.csv
  ddp_motifs.csv
  DDP_EXPERIMENT_REPORT.md
```

### `ddp_clip_signatures.csv`

One row per:

```text
clip × feature × delay × gain × polarity
```

Contains scale-aware temporal structure metrics.

### `ddp_parameter_rankings.csv`

Compares positive clips:

```text
drone
drone_like_synthetic
```

against:

```text
no_drone
```

AUC is used only as a scale-free research ranking.

The row is then checked against neighboring delay/gain choices.

Important:

```text
high AUC + weak neighborhood = fragile outlier
high AUC + strong neighborhood = interesting candidate
```

### `ddp_motifs.csv`

Groups the ranking into feature/polarity/delay/gain families.

The first useful candidates are `motif_strong`, but even these remain research hypotheses until they survive real hard-negative data.

## Run — synthetic first

From repository root on Windows:

```powershell
python tools\generate_synthetic.py
python tools\build_benchmark.py --profile synthetic
pytest -q
python -m ddp_experiment.run_experiment
```

Or double-click:

```text
RUN_DDP_SYNTHETIC.bat
```

## Run — small real benchmark

This uses the existing 1 m / 10 m / 30 m + noise-floor downloader:

```powershell
python tools\generate_synthetic.py
python tools\build_benchmark.py --profile small-real
python -m ddp_experiment.run_experiment --output outputs/ddp_experiment_real
```

Or double-click:

```text
RUN_DDP_SMALL_REAL.bat
```

## Next dataset

After the small-real pass works, run the same experiment with ESC-50 hard negatives.

Especially useful:

```text
helicopter
engine
chainsaw
vacuum_cleaner
washing_machine
airplane
wind
```

Only after that should DDP-derived features be considered for the browser/iPhone runtime.

## Decision rule

The branch succeeds if we find one or more feature/parameter motif families that:

- separate drone-positive and negative clips;
- remain strong in neighboring `D/g` settings;
- repeat across more than one positive recording condition;
- survive hard mechanical negatives.

The branch is also successful if the answer is **no**. That tells us DDP does not add useful discrimination beyond the existing DSP feature set.

## Do not overclaim

- DDP score is not a drone probability.
- Synthetic separation is not field validation.
- 1/10/30 m research recordings do not establish iPhone range.
- Do not port a discovered rule into the live detector before hard-negative validation.
