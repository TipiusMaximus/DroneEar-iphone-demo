# Codex Prompt — Implement DroneEar v0.2a

Work on the existing repository:

```text
TipiusMaximus/DroneEar-iphone-demo
```

Implement **v0.2a detection improvements** into the current project.

Do not create a second parallel demo.

## Preflight

Before editing:

1. inspect repository structure;
2. inspect `index.html`;
3. inspect README;
4. inspect git status;
5. identify current microphone callback size;
6. identify current FFT size;
7. identify current scoring and persistence logic;
8. preserve current GitHub Pages deployment.

Do not make unrelated changes.

---

## Main goal

Improve the detector while keeping it:

- browser-only;
- iPhone Safari compatible;
- local;
- lightweight;
- explainable;
- ML-free.

Implement only these core changes:

```text
4096 real-sample rolling FFT
power spectrum
harmonic lattice search
temporal f0 tracking
debug telemetry
```

---

## 1. Rolling analysis buffer

Current audio arrives in smaller blocks.

Create a rolling analysis buffer containing:

```text
4096 real samples
```

Do not use zero-padding as a substitute for missing history.

The analysis should run every incoming audio block once the ring is full.

Use:

```text
FFT size = 4096
```

unless runtime compatibility requires another documented value.

Apply Hann window before FFT.

---

## 2. Power spectrum

Calculate:

```text
power[i] = magnitude[i] * magnitude[i]
```

Use power for:

- band energy;
- harmonic energy;
- ratios;
- contrast.

dB may be used for display/debug.

---

## 3. Frequency handling

Ignore frequencies below:

```text
60 Hz
```

for detection.

Prefer this frequency-domain rejection over the current block-resetting forward/backward high-pass filter.

If the existing high-pass is retained, justify why and ensure it does not create per-frame state-reset artifacts.

---

## 4. Harmonic-lattice detector

Search candidate fundamentals:

```text
60–400 Hz
```

Make this configurable.

For each candidate evaluate up to:

```text
6 harmonics
```

at:

```text
f0
2f0
3f0
4f0
5f0
6f0
```

Use tolerance approximately:

```text
max(8 Hz, 4–5% of target frequency)
```

For every candidate calculate:

```text
harmonic energy
harmonic hit count
harmonic consistency
harmonic contrast
```

Select the candidate with the best combined harmonic score.

Return at least:

```text
bestF0
harmonicHits
harmonicConsistency
harmonicContrast
harmonicScore
```

Do not assume bestF0 is a physically verified rotor frequency.

---

## 5. Harmonic contrast

Compare expected harmonic regions with surrounding/inter-harmonic power.

Prefer a relative measurement.

Example:

```text
harmonicContrastDb
```

or normalized:

```text
harmonicContrast 0..1
```

Avoid rewarding a broadband noisy spectrum simply because every harmonic region contains energy.

---

## 6. Temporal f0 tracking

Keep roughly:

```text
1–2 seconds
```

of recent bestF0 values.

Calculate:

```text
trackStability 0..1
```

Reward smooth/continuous frequency evolution.

Do not require a fixed f0.

Slow drift must remain valid.

Strong frame-to-frame jumps should lower track stability.

Reset/decay the track when harmonic confidence is very low.

---

## 7. Update drone score

Use an explainable weighted score.

Initial target:

```text
0.40 harmonicScore
0.20 harmonicContrast
0.15 harmonicConsistency
0.15 trackStability
0.10 mechanical band score
```

Weights must be configurable.

Do not treat the score as calibrated probability.

Reduce the existing absolute RMS influence.

Keep only a low silence/no-signal gate.

---

## 8. Persistence

Preserve:

```text
CLEAR
POSSIBLE
DETECTED
```

Keep the current hysteresis/persistence concept.

Do not aggressively retune thresholds until the new score has been tested.

---

## 9. Debug UI

Add a collapsible debug section.

Display:

```text
actual sample rate
FFT size
FFT resolution
RMS
best f0
harmonic hits
harmonic consistency
harmonic contrast
harmonic score
track stability
band ratios
raw score
smoothed score
state
```

Keep the normal top-level UI simple.

---

## 10. Spectrum UI

Draw the selected harmonic lattice on the existing spectrum.

For the current bestF0, visually mark:

```text
f0
2f0
3f0
...
```

Only draw harmonics inside the displayed frequency range.

---

## 11. Privacy and deployment

Preserve:

```text
no raw audio recording
```

Do not introduce network upload.

Keep GitHub Pages compatibility.

Do not add build tooling unless absolutely necessary.

---

## 12. README

Update README with:

- v0.2a detector summary;
- 4096-sample rolling FFT;
- harmonic lattice idea;
- debug mode;
- limitations;
- no probability claim;
- no audio recording.

---

## 13. Manual validation

Before finishing, verify as much as possible:

1. page loads;
2. JS has no obvious syntax errors;
3. detector functions can run on synthetic arrays if practical;
4. harmonic test signal near 90 Hz + harmonics produces bestF0 near 90 Hz;
5. a single sine produces lower harmonic consistency than the harmonic test;
6. score remains bounded 0..1;
7. persistence still transitions correctly;
8. start/stop code remains intact.

If microphone access cannot be tested in the environment, say so explicitly.

---

## 14. Scope control

Do NOT add:

- ML;
- TensorFlow.js;
- React;
- Node build pipeline;
- native iOS project;
- backend server;
- audio uploads;
- location tracking;
- direction finding.

---

## Definition of done

Do not stop at planning.

Continue until the code is in a testable state.

Final report must include:

1. files changed;
2. detector changes;
3. test/validation results;
4. exact iPhone test steps;
5. known limitations;
6. next smallest recommended change;
7. whether a git commit is recommended.

Keep the implementation scoped and readable.
