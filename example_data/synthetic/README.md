# Synthetic fixtures

WAV files in this directory are **generated**, not stored in git (MCP text pushes would corrupt binaries).

From the repo root:

```text
python tools/generate_synthetic.py
```

This writes:

```text
harmonic_90.wav
harmonic_sweep_80_110.wav
single_sine_90.wav
white_noise.wav
am_noise.wav
```

`RUN_SYNTHETIC_TESTS.bat` and `python tools/run_all.py --profile synthetic` call the generator first.
