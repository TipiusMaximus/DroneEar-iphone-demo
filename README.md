# DroneEar — iPhone Safari demo (v0.2a)

Live: https://tipiusmaximus.github.io/DroneEar-iphone-demo/

Selain-DSP, ei ML. **Drone score ei ole todennäköisyys.** Ääntä ei tallenneta eikä lähetetä.

## Detector

- 4096-sample rolling FFT (about 256 ms at 16 kHz, ~3.9 Hz bins)
- Power spectrum (`magnitude²`) for energy, ratios, and contrast
- Bins below 60 Hz ignored (no per-frame IIR high-pass)
- Harmonic-lattice search for a 60–400 Hz fundamental, up to 6 harmonics (prefer lower f0 on near-tie octave/harmonic collapse above 200 Hz)
- Temporal f0 tracking (~1.5 s) so slow RPM drift stays valid and random jumps do not
- `CLEAR / POSSIBLE / DETECTED` persistence (same thresholds as v0.1)
- Collapsible debug panel and harmonic markers on the spectrum
- Browser math lives in `dsp.js` (Node + Safari). Do not merge it back into `index.html`.

## Limitations

- Music, fans, engines, and other harmonic sources can still score high
- Not a field-ready detector
- Open in **Safari over HTTPS** (GitHub Pages). Do not use jsDelivr; it serves this HTML as `text/plain` and the microphone will not work.

## Automated benchmark

Python reference detector + synthetic controls + optional Zenodo 1/10/30 m clips. Plan: [docs/BENCHMARK_PLAN.md](docs/BENCHMARK_PLAN.md). Drift vs browser JS: [docs/BROWSER_REFERENCE_DRIFT.md](docs/BROWSER_REFERENCE_DRIFT.md).

The Python detector in `benchmark/reference_detector.py` is a **reference**, not identical to `dsp.js`. Do not call score a probability.

Synthetic WAV fixtures are **generated** by `tools/generate_synthetic.py` (not committed as binaries).

### Windows (no network)

Double-click:

```text
RUN_SYNTHETIC_TESTS.bat
```

Or PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements-benchmark.txt
python tools\run_all.py --profile synthetic
```

Results: `outputs/synthetic/results.csv` and `outputs/synthetic/summary.md`.

### Small real (Zenodo ~83 MB)

Double-click `RUN_SMALL_REAL_BENCHMARK.bat`, or:

```powershell
python tools\run_all.py --profile small-real
```

Downloads 1 m / 10 m / 30 m drone WAVs + noisefloor, MD5-checks, mono 16 kHz, 5 s clips. Does **not** peak-normalize clips. Does **not** download ESC-50 (~600 MB) or DDL (12.6 GB).

```powershell
python tools\run_all.py --profile small-real --include-esc50
```

## Docs

- [v0.2a spec](docs/DRONEEAR_V0.2A_SPEC.md)
- [Implementation prompt](docs/CODEX_V0.2A_PROMPT.md)
- [Field test log template](docs/FIELD_TEST_LOG.md)
- [Benchmark plan](docs/BENCHMARK_PLAN.md)
- [Datasets](docs/DATASETS.md)
- [Metrics](docs/METRICS.md)
- [Validation](docs/VALIDATION.md)
- [Browser vs Python drift](docs/BROWSER_REFERENCE_DRIFT.md)
