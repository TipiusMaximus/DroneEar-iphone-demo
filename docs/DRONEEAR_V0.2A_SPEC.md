# DroneEar v0.2a — Detection Upgrade Specification

**Status:** Planned  
**Scope:** Improve the existing browser/iPhone demo detector without introducing ML.  
**Primary goal:** Make the current DSP detector materially more reliable and diagnosable before collecting training data or adding a learned model.

---

## 1. Why v0.2a exists

The current demo already has:

- microphone input;
- FFT-based analysis;
- harmonic feature extraction;
- a heuristic `drone_score`;
- `CLEAR / POSSIBLE / DETECTED` persistence logic;
- live visualization.

The main weakness is not the overall architecture. The main weakness is that the detector currently works from short analysis frames and combines several broad heuristics without enough temporal and spectral structure.

v0.2a focuses only on four improvements:

1. **real 4096-sample rolling analysis window;**
2. **power-spectrum based measurements;**
3. **explicit harmonic-lattice search;**
4. **debug telemetry for understanding why a frame scored high or low.**

Do not add ML yet.

---

## 2. Current known issue: zero-padded FFT

Current behavior:

```text
microphone callback: 1024 real samples
↓
analyze()
↓
2048 sample FFT buffer
↓
only ~1024 positions contain real audio
remaining positions are zero
```

Zero-padding can make the frequency plot look more finely sampled, but it does **not** add real spectral resolution.

The detector needs more real audio history.

---

## 3. Change 1 — 4096-sample rolling ring buffer

### Goal

Always analyze the latest **4096 real microphone samples**.

At a 16 kHz sample rate:

```text
4096 / 16000 = 0.256 s
```

So every analysis window contains about **256 ms of real audio**.

The resulting FFT bin spacing is:

```text
16000 / 4096 ≈ 3.906 Hz
```

This is much better suited to tracking low-frequency rotor-related fundamentals and harmonics than the current short frame.

### Recommended flow

```text
microphone callback
    ↓
1024 new samples
    ↓
rolling 4096-sample buffer
    ↓
Hann window
    ↓
4096-point FFT
```

The analysis still updates every 1024 new samples.

At 16 kHz:

```text
1024 / 16000 = 0.064 s
```

So the UI/detector updates about:

```text
15.625 times / second
```

This gives a useful compromise:

- long enough window for spectral resolution;
- frequent enough updates for temporal tracking.

### Implementation requirement

Maintain a rolling buffer such as:

```javascript
let ring = new Float32Array(4096);
```

On every incoming block:

```text
shift old samples left
append newest samples
analyze only after the ring buffer has filled
```

A true circular/ring implementation is preferable if practical, but a simple shift/copy version is acceptable for this small MVP if performance remains good on iPhone Safari.

### Acceptance criteria

- FFT input contains 4096 real microphone samples.
- No implicit zero-padding is used as a substitute for history.
- Detector updates approximately every 1024 new samples.
- First detection result is delayed until enough real audio has filled the analysis window.

---

## 4. Change 2 — use power spectrum

### Problem

The current detector mostly sums FFT magnitude values:

```text
magnitude
```

For energy-like comparisons, use:

```text
power = magnitude²
```

### Required representation

After FFT:

```javascript
power[i] = mag[i] * mag[i];
```

Optionally derive dB values for visualization/debug:

```javascript
db[i] = 10 * Math.log10(power[i] + epsilon);
```

Use a small epsilon to avoid `log(0)`.

Example:

```javascript
const EPS = 1e-12;
const db = 10 * Math.log10(power + EPS);
```

### Important distinction

Use:

```text
power spectrum
```

for scoring and energy ratios.

Use:

```text
dB
```

mainly for:

- debug output;
- plots;
- relative SNR-like measurements.

Do not mix magnitude, power and dB values in the same ratio without explicitly converting them.

---

## 5. Normalize band measurements

Current frequency bands are different widths:

```text
low:   60–250 Hz
mid:   250–2000 Hz
high:  2000–8000 Hz
```

A simple sum favors wider bands.

Preferred v0.2a options:

### Option A — mean spectral power per bin

```text
bandMeanPower =
sum(power in band) / number_of_bins
```

### Option B — relative power

```text
bandRatio =
bandPower / totalRelevantPower
```

Use one consistent method.

For MVP, use both if useful:

```text
bandLowRatio
bandMidRatio
bandHighRatio
```

and optionally:

```text
bandLowMean
bandMidMean
bandHighMean
```

---

## 6. Change 3 — explicit harmonic-lattice search

### Goal

Stop relying mainly on median spacing between detected peaks.

Instead explicitly ask:

> “For which candidate fundamental frequency does the current spectrum contain the strongest repeated harmonic structure?”

### Candidate fundamental range

Start with:

```text
60 Hz ≤ f0 ≤ 400 Hz
```

Keep it configurable.

Suggested step:

```text
1–2 Hz
```

Because FFT bins are about 3.9 Hz apart, the implementation may map the candidate to the nearest FFT bin instead of interpolating.

### Harmonic search

For each candidate:

```text
f0
2 × f0
3 × f0
4 × f0
5 × f0
6 × f0
```

Use up to:

```text
6 harmonics
```

or until Nyquist is reached.

### Frequency tolerance

Do not require the harmonic to fall on one exact bin.

Use a tolerance window around each expected harmonic.

Example:

```text
tolerance = max(8 Hz, 0.04 × targetFrequency)
```

This handles:

- RPM movement;
- FFT leakage;
- imperfect frequency-bin alignment;
- multiple motor speeds.

### Harmonic energy

For each expected harmonic:

```text
target = k × f0
```

Measure power inside:

```text
target - tolerance
...
target + tolerance
```

Then compute:

```text
harmonicEnergy
```

as the sum of these regions.

---

## 7. Harmonic contrast

A motor-like harmonic pattern should not only have energy at expected harmonic locations.

It should preferably also have **more energy there than between them**.

For every candidate `f0`, measure:

```text
harmonic regions
vs.
inter-harmonic/background regions
```

Possible metric:

```text
harmonicContrast =
harmonicMeanPower / (backgroundMeanPower + epsilon)
```

or in dB:

```text
harmonicContrastDb =
10 * log10(harmonicMeanPower / backgroundMeanPower)
```

This is more useful than simply asking whether six peaks exist.

---

## 8. Harmonic hit count

For each candidate f0, count how many expected harmonics are meaningfully present.

Example:

```text
f0 = 86 Hz

86 Hz   → hit
172 Hz  → hit
258 Hz  → hit
344 Hz  → hit
430 Hz  → hit
516 Hz  → miss
```

Result:

```text
harmonicHits = 5 / 6
harmonicConsistency = 0.833
```

A hit should require the harmonic region to exceed the local/background floor by a configurable margin.

---

## 9. Fundamental selection

For each candidate `f0`, calculate a score such as:

```text
candidateScore =
    harmonicEnergyScore
  + harmonicConsistencyScore
  + harmonicContrastScore
```

Normalize components to 0–1 before weighting.

Example initial weights:

```text
harmonic energy       0.35
harmonic consistency  0.40
harmonic contrast     0.25
```

The best candidate becomes:

```text
bestF0
bestHarmonicScore
bestHarmonicHits
bestHarmonicContrast
```

Do not interpret `bestF0` as the proven physical rotor RPM frequency.

It is simply the fundamental that best explains the measured harmonic pattern.

---

## 10. Temporal harmonic tracking

The existing persistence logic tracks only the final detector score.

v0.2a should additionally retain recent `bestF0` estimates.

Example:

```text
t0   86 Hz
t1   87 Hz
t2   87 Hz
t3   89 Hz
t4   88 Hz
```

This looks coherent.

Compare:

```text
86
212
74
355
91
```

This does not.

### Track structure

Maintain recent values for approximately:

```text
1–2 seconds
```

Example buffer:

```javascript
f0History = [
  { t, f0, harmonicScore },
  ...
];
```

### Track stability metric

Possible first implementation:

```text
median f0 over recent frames
mean absolute deviation from median
```

Convert to:

```text
trackStability = 0..1
```

Example idea:

```text
very small variation  → 1
moderate variation    → 0.5
large random jumps    → 0
```

Do not require an absolutely fixed frequency.

Drone RPM can drift and change.

The purpose is to reject **randomly jumping unrelated spectral peaks**.

---

## 11. Do not overfit the temporal tracker

Allowed:

```text
85 → 86 → 88 → 91 → 94 Hz
```

Potentially useful coherent movement.

Not useful:

```text
85 → 290 → 71 → 360 → 102 Hz
```

The algorithm should reward continuity, not exact stationarity.

---

## 12. Updated v0.2a score

The final heuristic score should become easier to interpret.

Suggested first structure:

```text
droneScore =
  0.40 × harmonicScore
+ 0.20 × harmonicContrast
+ 0.15 × harmonicConsistency
+ 0.15 × trackStability
+ 0.10 × spectral/mechanicalBandScore
```

Then apply only a light level/noise gate.

These are starting values, not validated constants.

All weights must live in configuration.

---

## 13. RMS gate: reduce its importance

The current detector uses a strong absolute RMS gate.

This can fail when:

- a drone is distant;
- the environment is loud;
- different phones have different microphone gains;
- iOS applies device-specific audio behavior.

v0.2a should not rely heavily on an absolute amplitude threshold.

### First safe improvement

Keep only a very low silence gate:

```text
if input is effectively silent:
    score = 0
```

Otherwise let spectral structure dominate.

---

## 14. Optional adaptive noise floor

If implementation remains simple, add an adaptive background estimate.

For every FFT bin or coarse frequency band:

```text
noiseFloor
```

should update slowly when no strong candidate is present.

Then calculate approximate local contrast:

```text
signal power
vs.
estimated background power
```

This can later become a true SNR-like detector.

### Important

Do not let a sustained drone immediately become the new noise floor.

Use slow updating and/or freeze noise-floor learning when:

```text
state == POSSIBLE
or
state == DETECTED
```

If this makes v0.2a too large, defer adaptive noise-floor estimation to v0.2b.

---

## 15. High-pass handling

Current frame-by-frame forward/backward IIR filtering can reset its internal state on every frame.

This can create block-edge artifacts.

For v0.2a choose one:

### Preferred simple solution

Do not time-domain high-pass for the detector.

Instead:

```text
FFT
↓
ignore bins below 60 Hz
```

This is already compatible with the current detector design.

### Later

If a time-domain high-pass is needed:

- implement a continuous stateful filter;
- preserve filter state between callbacks.

Do not repeatedly reset an IIR filter inside each independent analysis frame.

---

## 16. Change 4 — debug telemetry

The detector must explain why it thinks a signal is drone-like.

Add a debug section to the UI.

Minimum values:

```text
sample rate
FFT size
FFT resolution

RMS
best f0
harmonic hits
harmonic consistency
harmonic contrast
harmonic score
track stability
band low
band mid
band high
raw score
smoothed score
state
```

Example:

```text
FFT:              4096
Resolution:       3.91 Hz

RMS:              0.012
Best f0:          87.9 Hz
Harmonics:        5 / 6
Consistency:      0.83
Contrast:         +12.4 dB
Harmonic score:   0.78
Track stability:  0.91

Raw score:        0.72
Smoothed score:   0.68
State:            POSSIBLE
```

This section may be behind:

```text
Show debug
```

to keep the normal UI simple.

---

## 17. Spectrum visualization improvements

Mark the chosen harmonic lattice on the graph.

If:

```text
bestF0 = 88 Hz
```

draw markers at:

```text
88
176
264
352
440
528 Hz
```

This makes debugging dramatically easier.

Also show:

```text
bestF0
```

as text.

---

## 18. Persistence state machine

Keep the existing concept:

```text
CLEAR
POSSIBLE
DETECTED
```

Do not radically tune thresholds in the same change unless required.

Initial values can remain close to:

```text
possible       0.55
detected       0.72
detected time  2.0 s
clear          0.45
clear time     3.0 s
```

The purpose of v0.2a is first to improve **what the score means**, not to hide poor scoring behind different thresholds.

---

## 19. Files and code organization

The current single-file demo may remain single-file for this iteration if that keeps deployment simple.

However, logically separate sections:

```text
CONFIG

AUDIO INPUT
RING BUFFER

FFT / SPECTRAL PROCESSING
HARMONIC LATTICE
TEMPORAL TRACKER
SCORING
PERSISTENCE

VISUALIZATION
DEBUG UI
```

If the file becomes difficult to maintain, v0.2b can split JS into:

```text
audio.js
dsp.js
detector.js
ui.js
```

Do not refactor solely for aesthetics during v0.2a.

---

## 20. Test plan

### Test A — silence / quiet room

Expected:

```text
low score
CLEAR
```

No repeated false detection.

---

### Test B — human speech

Expected:

```text
may contain harmonics
but harmonic lattice should be less stable
and track should fluctuate
```

Should generally remain:

```text
CLEAR
```

or occasional short:

```text
POSSIBLE
```

but not sustained `DETECTED`.

---

### Test C — single sine wave

A single tone is not enough.

Expected:

```text
low harmonic hit count
low harmonic consistency
no DETECTED
```

---

### Test D — synthetic harmonic signal

Play a synthetic tone containing:

```text
90
180
270
360
450
540 Hz
```

Expected:

```text
bestF0 ≈ 90 Hz
high harmonic consistency
stable track
high detector score
```

This validates the harmonic-lattice implementation.

It does not validate real-world drone detection.

---

### Test E — changing synthetic RPM

Sweep the fundamental slowly:

```text
80 Hz → 110 Hz
```

and generate matching harmonics.

Expected:

```text
f0 track follows smoothly
track stability remains reasonably high
```

---

### Test F — music

Play several music examples.

Expected:

Music may contain strong harmonic structure.

Record:

```text
best f0
harmonic hits
track stability
score
```

This is an important false-positive class.

Do not tune only against one music track.

---

### Test G — mechanical negatives

Test:

```text
fan
vacuum
drill
lawn mower
car engine
motorcycle
HVAC
```

These are essential because many are more similar to a drone than speech is.

---

### Test H — real drone

Test:

```text
hover
approach
depart
different distances
```

Record observations before changing thresholds.

---

## 21. Field test logging

For each test, record:

```text
source
distance if relevant
phone model
environment
wind
best f0
peak score
state reached
false positive / true positive / false negative
notes
```

This will become the basis for v0.3.

---

## 22. Do not claim probability

UI label:

```text
Drone score
```

is acceptable.

Do not label it:

```text
Probability
```

or:

```text
82% chance of drone
```

until a labeled validation dataset and calibration process exist.

---

## 23. v0.2a Definition of Done

v0.2a is complete when:

- [ ] analyzer uses 4096 real rolling samples;
- [ ] analysis updates using overlapping windows;
- [ ] FFT scoring uses power spectrum;
- [ ] band metrics are normalized;
- [ ] candidate f0 range is configurable;
- [ ] harmonic-lattice search is implemented;
- [ ] best f0 is returned;
- [ ] harmonic hit count is returned;
- [ ] harmonic consistency is returned;
- [ ] harmonic contrast is returned;
- [ ] recent f0 values are tracked;
- [ ] track stability is included in score;
- [ ] absolute RMS gating is reduced to a minimal silence gate;
- [ ] debug values are visible in UI;
- [ ] chosen harmonics can be visualized on spectrum;
- [ ] existing persistence state machine still works;
- [ ] iPhone Safari microphone mode still starts and stops cleanly;
- [ ] existing GitHub Pages deployment remains functional;
- [ ] no raw audio is recorded;
- [ ] README is updated with the new detector description.

---

## 24. What v0.2a deliberately does NOT include

Do not add:

- ML;
- TensorFlow.js;
- Core ML;
- cloud inference;
- drone model identification;
- distance estimation;
- multi-microphone direction finding;
- automatic raw audio recording;
- native iOS app;
- major UI redesign.

Those are later milestones.

---

## 25. Next milestone after v0.2a

After testing v0.2a:

```text
collect false positives
↓
identify which feature causes them
↓
adjust detector
↓
build labeled test set
```

Only then decide whether the next step is:

```text
v0.2b — adaptive noise floor / SNR
```

or:

```text
v0.3 — baseline ML classifier
```

The decision should be based on measured behavior, not assumptions.
