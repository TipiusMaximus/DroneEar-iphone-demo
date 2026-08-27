from __future__ import annotations

from pathlib import Path

import numpy as np

from benchmark.reference_detector import DetectorConfig, load_audio, analyze_clip
from ddp_experiment.spectral_features import spectral_feature_rows


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
    "spectral_centroid_hz",
    "spectral_flatness",
    "spectral_flux",
    "amplitude_envelope",
    "envelope_delta",
    "modulation_depth",
    "sideband_ratio",
    "low_frequency_share",
    "high_frequency_share",
    "band_40_120_ratio",
    "band_120_250_ratio",
    "band_250_500_ratio",
    "band_500_1000_ratio",
    "band_1000_2000_ratio",
    "band_2000_4000_ratio",
    "band_4000_8000_ratio",
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


def rows_to_feature_series(rows, *, spectral_rows=None, normalized=True):
    """Convert detector/STFT frame dictionaries into DDP-ready time series.

    DDP is intentionally applied to feature behavior over time, not directly
    to 16 kHz raw PCM. With the current 1024/16 kHz hop, one DDP delay unit is
    about 64 ms.

    `spectral_rows` is optional so the original detector-only adapter remains
    testable. When supplied it adds distance-sensitive band, modulation,
    sideband and flux features aligned to the same frame grid.
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

    if spectral_rows:
        count = min(len(rows), len(spectral_rows))
        for name in DEFAULT_FEATURES:
            if name in raw:
                continue
            raw[name] = np.asarray(
                [float(spectral_rows[i].get(name, 0.0)) for i in range(count)],
                dtype=float,
            )
        # Keep every feature on the same aligned grid if a caller supplied a
        # shorter spectral stream.
        if count < len(rows):
            raw = {name: values[:count] for name, values in raw.items()}

    if not normalized:
        return raw

    return {name: robust_zscore(values) for name, values in raw.items()}


def wav_to_ddp_features(path, cfg=None, *, normalized=True):
    cfg = cfg or DetectorConfig()
    _, samples = load_audio(Path(path), cfg.sample_rate)
    detector_rows, summary = analyze_clip(samples, cfg)
    spectral_rows = spectral_feature_rows(samples, detector_rows, cfg)
    return rows_to_feature_series(
        detector_rows,
        spectral_rows=spectral_rows,
        normalized=normalized,
    ), summary
