# Validation status

Validated in the build environment on 2026-08-27 (EEST).

Python: 3.13 + numpy 2.5.2 + scipy 1.18.1 + pytest 9.1.1. Detector: `benchmark/reference_detector.py` (reference, not identical to `dsp.js`).

## Offline tests

```text
10 passed in 16.74s
```

Command:

```text
python tools/run_all.py --profile synthetic
```

Verified regression cases:

- 90 Hz six-harmonic synthetic signal -> DETECTED, f0 89.8 Hz
- 80–110 Hz slowly changing harmonic signal -> DETECTED, f0 93.8 Hz
- single 90 Hz sine WAV -> CLEAR (p95 0.130)
- white noise -> CLEAR (p95 0.233)
- AM noise -> CLEAR (p95 0.249)
- scores stay within 0..1
- synthetic manifest builds correctly

Required checks:

1. 90 Hz harmonic lattice recovers f0 near 90 Hz — **pass** (89.8 Hz)
2. Harmonic scores materially above single sine — **pass** (1.000 vs 0.130)
3. Harmonic scores materially above white noise — **pass** (1.000 vs 0.233)
4. Scores 0..1 — **pass**
5. Harmonic reaches DETECTED — **pass**
6. Single sine does not reach DETECTED — **pass**
7. White noise does not reach DETECTED — **pass**

Node `test_v02a.js` (browser math in `dsp.js`): harmonic f0 91.25 Hz, 6/6 hits, score 0.97; single sine consistency 0.17, score 0.51 (CLEAR vs POSSIBLE 0.55). Not retuned.

## End-to-end synthetic benchmark

```text
WAV -> manifest -> detector -> results.csv -> summary.md
```

This run (`outputs/synthetic/summary.md`) — **AFTER** low-f0 / octave-collapse preference:

```text
| category                 | p95   | max   | state    | f0   | consistency | contrast dB | track |
| synthetic_harmonic       | 1.000 | 1.000 | DETECTED | 89.8 | 1.00        | 43.2        | 1.00  |
| synthetic_harmonic_sweep | 1.000 | 1.000 | DETECTED | 93.8 | 1.00        | 42.3        | 1.00  |
| single_sine              | 0.130 | 0.130 | CLEAR    | 62.5 | 0.00        | -2.4        | 0.20  |
| white_noise              | 0.233 | 0.243 | CLEAR    | 62.5 | 0.25        | 1.7         | 0.20  |
| am_noise                 | 0.249 | 0.397 | CLEAR    | 74.2 | 0.33        | 2.7         | 0.20  |
```

Vs before: essentially unchanged (white/AM f0 noise within a bin or two). False-positive DETECTED negatives: **0**.

## Small-real (Zenodo 7329733)

Network worked. `python tools/run_all.py --profile small-real` used cached downloads under `data/raw`, MD5-checked, mono 16 kHz, 5 s clips, **no peak-normalize**. ESC-50 and DDL were not downloaded.

Clips: **12**. False-positive DETECTED negatives: **0**. Real drone clips not DETECTED: **6** (all 1/10/30 m clips).

### BEFORE (prior run, no octave preference)

```text
| category    | distance | state    | p95   | f0    | consistency |
| drone_noise | 1        | POSSIBLE | 0.700 | 140.6 | 0.83        |
| drone_noise | 1        | POSSIBLE | 0.717 | 144.5 | 0.83        |
| drone_noise | 10       | CLEAR    | 0.281 | 363.3 | 0.33        |
| drone_noise | 10       | CLEAR    | 0.290 | 285.2 | 0.33        |
| drone_noise | 30       | CLEAR    | 0.240 | 281.2 | 0.33        |
| drone_noise | 30       | CLEAR    | 0.234 | 281.2 | 0.33        |
| noise_floor |          | CLEAR    | 0.236 | 74.2  | 0.33        |
```

### AFTER (octave / harmonic-collapse preference)

```text
| category    | distance | state    | p95   | f0    | consistency | contrast dB | track |
| drone_noise | 1        | POSSIBLE | 0.700 | 140.6 | 0.83        | 10.2        | 0.84  |
| drone_noise | 1        | POSSIBLE | 0.717 | 144.5 | 0.83        | 9.8         | 1.00  |
| drone_noise | 10       | CLEAR    | 0.281 | 363.3 | 0.33        | 7.5         | 0.20  |
| drone_noise | 10       | CLEAR    | 0.290 | 285.2 | 0.33        | 8.2         | 0.20  |
| drone_noise | 30       | CLEAR    | 0.240 | 281.2 | 0.33        | 4.9         | 0.20  |
| drone_noise | 30       | CLEAR    | 0.234 | 281.2 | 0.33        | 4.7         | 0.20  |
| noise_floor |          | CLEAR    | 0.236 | 66.4  | 0.33        | 2.2         | 0.20  |
```

### What changed

Implemented low-f0 preference when a ~best/2 or ~best/3 lattice candidate scores nearly as well (`score >= best - 0.05` or `>= 0.92 * best`, within 4% or 2 FFT bins), only when the current winner is above 200 Hz (so a true ~140 Hz 1 m lattice is not halved to ~70 Hz). Mirrored in `dsp.js` `searchLattice`. DETECTED (0.72) and the sine-leakage hit gate (`contrast_db>=6 AND h_fraction>=0.003`) were **not** changed.

Honest outcome:

- **1 m:** no regression (still POSSIBLE, same p95 / f0 / consistency).
- **10 m / 30 m:** f0 did **not** drop. Per-frame dumps show half-f0 candidates around 140 Hz have **harmonic_score 0** (0 hits) while the weak 280–360 Hz winners only have 2/6 hits. The preference rule correctly does nothing when the lower candidate is not competitive — so the earlier “octave collapse” diagnosis does not hold under the current scoring (coverage gate + hit fraction). High f0 here is “least-bad weak lattice,” not a near-tie with a strong half-f0.

Caveat: research mics, not iPhone. Do not infer iPhone detection range.

## Important regression found and fixed during packaging

An earlier version falsely classified a WAV-encoded single 90 Hz sine as DETECTED because local spectral contrast alone could treat extremely small FFT leakage components as harmonic hits.

The detector now requires a harmonic to have both:

```text
local contrast >= 6 dB
AND
power fraction >= 0.003 of relevant spectral power
```

and applies a harmonic-coverage gate. A WAV regression test prevents this failure from silently returning.

## Next smallest detector change

Do **not** lower DETECTED (0.72) and do **not** weaken the sine-leakage fraction gate. Octave preference is in place but does not help 10/30 m because half-f0 scores are zero. Next: a weak-signal f0 estimator that does not rely on the coverage-gated harmonic score alone — e.g. harmonic product spectrum / peak-seeded subharmonic search to propose f0, then score — so distant clips can land in the rotor band when only upper harmonics are audible. Measure on the same 1/10/30 m clips before any threshold edit.

## Fixtures

Synthetic WAVs are generated by `python tools/generate_synthetic.py`. They are not stored as git binaries.
