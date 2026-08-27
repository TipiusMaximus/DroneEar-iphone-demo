# DroneEar — iPhone Safari demo (v0.2a)

Live: https://tipiusmaximus.github.io/DroneEar-iphone-demo/

Browser-only DSP detector. No ML. The on-screen **drone score is not a probability**. Audio is not recorded or uploaded.

## Detector

- 4096-sample rolling FFT (about 256 ms at 16 kHz, ~3.9 Hz bins)
- Power spectrum (`magnitude²`) for energy, ratios, and contrast
- Bins below 60 Hz ignored (no per-frame IIR high-pass)
- Harmonic-lattice search for a 60–400 Hz fundamental, up to 6 harmonics
- Temporal f0 tracking (~1.5 s) so slow RPM drift stays valid and random jumps do not
- `CLEAR / POSSIBLE / DETECTED` persistence (same thresholds as v0.1)
- Collapsible debug panel and harmonic markers on the spectrum

## Limitations

- Music, fans, engines, and other harmonic sources can still score high
- Not a field-ready detector
- Open in **Safari over HTTPS** (GitHub Pages). Do not use jsDelivr; it serves this HTML as `text/plain` and the microphone will not work.

## Docs

- [v0.2a spec](docs/DRONEEAR_V0.2A_SPEC.md)
- [Implementation prompt](docs/CODEX_V0.2A_PROMPT.md)
- [Field test log template](docs/FIELD_TEST_LOG.md)
