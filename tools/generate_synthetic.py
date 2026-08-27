from pathlib import Path
import argparse
import numpy as np
from scipy.io import wavfile

def save(path, x, sr=16000):
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.clip(x, -0.999, 0.999)
    wavfile.write(path, sr, (y * 32767).astype(np.int16))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="example_data/synthetic")
    ap.add_argument("--seconds", type=float, default=6.0)
    args = ap.parse_args()

    out = Path(args.out)
    sr = 16000
    n = int(args.seconds * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(20260827)

    harmonic = sum((1.0/k) * np.sin(2*np.pi*90.0*k*t) for k in range(1, 7))
    harmonic /= np.max(np.abs(harmonic))
    save(out/"harmonic_90.wav", 0.30*harmonic + 0.005*rng.standard_normal(n), sr)

    f = np.linspace(80.0, 110.0, n)
    phase = 2*np.pi*np.cumsum(f)/sr
    sweep = sum((1.0/k) * np.sin(k*phase) for k in range(1, 7))
    sweep /= np.max(np.abs(sweep))
    save(out/"harmonic_sweep_80_110.wav", 0.28*sweep + 0.005*rng.standard_normal(n), sr)

    save(out/"single_sine_90.wav", 0.30*np.sin(2*np.pi*90.0*t), sr)
    save(out/"white_noise.wav", 0.05*rng.standard_normal(n), sr)

    envelope = 0.5 + 0.5*np.sin(2*np.pi*7.0*t)
    save(out/"am_noise.wav", 0.04*rng.standard_normal(n)*envelope, sr)

    print(f"Generated 5 synthetic WAV files in {out}")

if __name__ == "__main__":
    main()
