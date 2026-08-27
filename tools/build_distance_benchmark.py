from __future__ import annotations

from pathlib import Path
import argparse
import csv

import numpy as np
from scipy.io import wavfile

from benchmark.reference_detector import load_audio
from ddp_experiment.distance_simulation import DISTANCE_PRESETS, simulate_distance


def _write_wav(path, samples, sample_rate):
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(np.asarray(samples, dtype=float), -0.999, 0.999)
    wavfile.write(path, sample_rate, (x * 32767).astype(np.int16))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="example_data/synthetic/harmonic_90.wav")
    parser.add_argument("--negative", default="example_data/synthetic/white_noise.wav")
    parser.add_argument("--out-dir", default="data/distance_benchmark")
    parser.add_argument("--manifest", default="data/distance_benchmark/manifest.csv")
    args = parser.parse_args()

    source = Path(args.source)
    negative = Path(args.negative)
    if not source.exists():
        raise FileNotFoundError(f"Source WAV not found: {source}. Run tools/generate_synthetic.py first.")

    sample_rate, samples = load_audio(source, 16000)
    out_dir = Path(args.out_dir)
    rows = []

    for index, (name, preset) in enumerate(DISTANCE_PRESETS.items()):
        degraded = simulate_distance(samples, sample_rate, seed=20260827 + index, **preset)
        path = out_dir / f"{source.stem}__{name}.wav"
        _write_wav(path, degraded, sample_rate)
        rows.append({
            "file": path.as_posix(),
            "label": "drone_like_synthetic",
            "source": "synthetic_distance",
            "category": f"distance_{name}",
            "distance_m": name,
            "clip_index": 0,
            "notes": "Synthetic propagation stress-test; not a physical distance calibration.",
        })

    if negative.exists():
        rows.append({
            "file": negative.as_posix(),
            "label": "no_drone",
            "source": "synthetic",
            "category": "white_noise",
            "distance_m": "",
            "clip_index": 0,
            "notes": "Negative control.",
        })

    manifest = Path(args.manifest)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "label", "source", "category", "distance_m", "clip_index", "notes"]
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[distance benchmark] {manifest} ({len(rows)} clips)")


if __name__ == "__main__":
    main()
