# Browser JS vs Python reference drift

`dsp.js` is the live Safari/Node detector. `benchmark/reference_detector.py` is a **reference** used by the automated benchmark. They implement the same v0.2a idea, not the same code. Scores are **not** a probability.

Do not retune JS thresholds just to match Python unless a real bug appears (for example a WAV-encoded single sine reaching DETECTED in JS).

`dsp.js` is already DOM-independent. `index.html` loads it via `<script src="dsp.js">`. Do not merge the math back into a single HTML file.

## Same (or close)

| Item | JS (`dsp.js` / `index.html` CFG) | Python (`reference_detector.py`) |
|---|---|---|
| FFT size | 4096 | 4096 |
| Hop | 1024 (`ScriptProcessor` buffer) | 1024 |
| Window | Hann | `np.hanning` |
| Spectrum | `magnitude²` power | `abs(rfft)²` |
| High-pass | bins `< 60 Hz` zeroed | only `>= 60 Hz` used as relevant |
| f0 search | 60–400 Hz | 60–400 Hz |
| Harmonic count | 6 | 6 |
| Final score weights | 0.40 / 0.20 / 0.15 / 0.15 / 0.10 | 0.40 / 0.20 / 0.15 / 0.15 / 0.10 |
| Persistence | POSSIBLE 0.55, DETECTED 0.72 for 2 s, CLEAR 0.45 for 3 s, smooth 0.35 | same |
| Candidate mix | energy 0.35, consistency 0.40, contrast 0.25 | same mix, then extra coverage gate |
| Octave / harmonic-collapse preference | After max `harmonicScore`, if a ~best/2 or ~best/3 candidate scores within margin (`>= best-0.05` or `>= 0.92*best`), within 4% or 2 bins, and winner is `> 200 Hz`, prefer lower f0. Defaults in `OCTAVE_DEFAULTS` inside `dsp.js` (CFG keys optional). | Same rule via `prefer_lower_octave_candidate` + `DetectorConfig.octave_*` |

## Different (intentional / known)

- **Harmonic tolerance.** JS: `max(8 Hz, 4% of target)`. Python: `max(8 Hz, 4.5% of target)`.
- **Harmonic hit rule.** JS: `hMean > max(bgMean * hitMargin, minHitPower)` with `hitMargin = 2.5`. Python: `contrast_db >= 6` **and** `h_fraction >= 0.003` of relevant spectral power (sine-leakage fix; a WAV-encoded single 90 Hz sine used to look like extra harmonics from FFT leakage).
- **Contrast.** JS gates contrast by consistency (`clip01((dB-0)/15) * clip01(consistency/0.5)`) and uses a **median power floor above 60 Hz** plus inter-harmonic gaps. Python uses **local sidebands** (`target ± 1.5–3 × tol`) and `clip01((dB-1)/19)` with no consistency gate on contrast.
- **Coverage gate.** Python multiplies candidate harmonic score by `clip01((hits-1)/3)`. JS has no equivalent.
- **Silence RMS.** JS `8e-4`. Python `2e-4`.
- **Track stability.** JS: 1.5 s history, median absolute deviation vs median f0, plus jump penalty (`max(25 Hz, 20% of max f0)`). Python: last 24 confident f0s, `clip01(1 - median_jump/25)`; unconfident frames return 0.20.
- **Mechanical band.** JS: `clip01(low+mid) * (1 - 0.65*high)` on 60–250 / 250–2000 / 2000–8000. Python: fraction of relevant power in 60–2000 Hz.
- **f0 grid.** JS steps by bin width (~3.9 Hz). Python iterates FFT bins in 60–400 Hz (same grid in practice).

## Regression to keep

WAV-encoded single 90 Hz sine must stay **not DETECTED**. That was a real Python bug (leakage treated as harmonic hits) and is locked by `tests/test_reference_detector.py`. If JS ever DETECTEDs that fixture, fix JS hit/fraction logic — do not lower Python thresholds to hide it.

## Remaining drift after octave preference

- JS still uses its own hit rule / contrast / coverage (no Python coverage gate, no `h_fraction` gate). Octave folding uses the same numeric margins in both, but candidate *scores* feeding the comparison still differ, so JS and Python may fold on different frames.
- `index.html` CFG does not list `octave*` keys; `dsp.js` falls back to `OCTAVE_DEFAULTS`. Python always uses `DetectorConfig` fields.
- Persistence thresholds and the Python sine-leakage hit gate were not changed for this step.
