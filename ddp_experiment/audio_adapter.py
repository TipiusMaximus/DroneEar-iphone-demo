from __future__ import annotations

from pathlib import Path

import numpy as np

from benchmark.reference_detector import DetectorConfig, load_audio, analyze_clip


DEFAULT_FEATURES = (
    "harmonic_score",
    "harmonic_energy_ratio",
    "harmonic_consistency",
    "harmonic_contrast_db",
    "track_stability",
    "mechanical_band_score",
    "rms",
    "raw_score",
    "smoothed_score",
    "best_f0",
    "f0_delta",
)


def robust_zscore(values):
    x = np.asarray(values, dtype=float)
    if len(x) == 0:
        return x
    median = float(np.median(x))
    mad = float(np.median(np.abs(x - median)))
    scale = 1.4826 * mad
    if scale < 1e-9:
        scale = float(np.std(x))
    if scale < 1e-9:
        return np.zeros_like(x)
    return np.clip((x - median) / scale, -8.0, 8.0)


def detector_rows_for_wav(path, cfg=None):
    """Run the existing DroneEar reference detector and return frame rows."""
    cfg = cfg or DetectorConfig()
    _, samples = load_audio(path, cfg.sample_rate)
    rows, summary = analyze_clip(samples, cfg)
    return rows, summary


def rows_to_feature_series(rows, *, normalized=True):
    """Convert detector-frame dictionaries into DDP-ready time series.

    DDP is intentionally applied to detector behavior over time, not directly
    to 16 kHz raw PCM. This keeps delays interpretable in detector-hop units.
    With the current 1024/16 kHz hop, one DDP delay unit is about 64 ms.
    """
    if not rows:
        return {}

    f0 = np.asarray([float(row.get("best_f0", 0.0)) for row in rows], dtype=float)
    f0_delta = np.zeros_like(f0)
    if len(f0) > 1:
        f0_delta[1:] = np.diff(f0)

    raw = {
        "harmonic_score": np.asarray([row.get("harmonic_score", 0.0) for row in rows], dtype=float),
        "harmonic_energy_ratio": np.asarray([row.get("harmonic_energy_ratio", 0.0) for row in rows], dtype=float),
        "harmonic_consistency": np.asarray([row.get("harmonic_consistency", 0.0) for row in rows], dtype=float),
        "harmonic_contrast_db": np.asarray([row.get("harmonic_contrast_db", 0.0) for row in rows], dtype=float),
        "track_stability": np.asarray([row.get("track_stability", 0.0) for row in rows], dtype=float),
        "mechanical_band_score": np.asarray([row.get("mechanical_band_score", 0.0) for row in rows], dtype=float),
        "rms": np.asarray([row.get("rms", 0.0) for row in rows], dtype=float),
        "raw_score": np.asarray([row.get("raw_score", 0.0) for row in rows], dtype=float),
        "smoothed_score": np.asarray([row.get("smoothed_score", 0.0) for row in rows], dtype=float),
        "best_f0": f0,
        "f0_delta": f0_delta,
    }

    if not normalized:
        return raw

    # The research question is temporal structure, not which feature has the
    # largest physical units. Robust within-clip scaling makes DDP signatures
    # more comparable across f0 Hz, contrast dB, RMS and bounded scores.
    return {name: robust_zscore(values) for name, values in raw.items()}


def wav_to_ddp_features(path, cfg=None, *, normalized=True):
    rows, summary = detector_rows_for_wav(Path(path), cfg)
    return rows_to_feature_series(rows, normalized=normalized), summary
