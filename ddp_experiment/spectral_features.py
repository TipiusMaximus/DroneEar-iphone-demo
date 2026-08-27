from __future__ import annotations

from collections import deque

import numpy as np

from benchmark.reference_detector import DetectorConfig


FREQUENCY_BANDS = {
    "band_40_120_ratio": (40.0, 120.0),
    "band_120_250_ratio": (120.0, 250.0),
    "band_250_500_ratio": (250.0, 500.0),
    "band_500_1000_ratio": (500.0, 1000.0),
    "band_1000_2000_ratio": (1000.0, 2000.0),
    "band_2000_4000_ratio": (2000.0, 4000.0),
    "band_4000_8000_ratio": (4000.0, 8000.0),
}


def _band_power(power, freqs, low, high):
    mask = (freqs >= low) & (freqs < high)
    return float(power[mask].sum()) if mask.any() else 0.0


def _sideband_ratio(power, freqs, f0, *, harmonics=6):
    """Energy beside the harmonic cores, relative to core+sideband energy.

    This is intentionally a broad research feature rather than a rotor model.
    The core uses +/-6 Hz. Sidebands use 8..40 Hz offsets around each
    harmonic, clipped at Nyquist. Multiple rotors, RPM jitter and reflections
    can all contribute, so this must not be interpreted as a unique drone cue.
    """
    if not np.isfinite(f0) or f0 <= 0.0:
        return 0.0

    core = 0.0
    side = 0.0
    nyquist = float(freqs[-1])
    for k in range(1, harmonics + 1):
        target = float(k * f0)
        if target >= nyquist:
            break
        core_mask = (freqs >= target - 6.0) & (freqs <= target + 6.0)
        side_mask = (
            ((freqs >= target - 40.0) & (freqs <= target - 8.0))
            | ((freqs >= target + 8.0) & (freqs <= target + 40.0))
        )
        core += float(power[core_mask].sum()) if core_mask.any() else 0.0
        side += float(power[side_mask].sum()) if side_mask.any() else 0.0
    return float(side / (core + side + 1e-18))


def spectral_feature_rows(samples, detector_rows, cfg=None):
    """Build frame-aligned distance/modulation features from the same STFT grid.

    The features are designed around what changes with propagation distance:
    high-frequency share, low-band masking, spectral flux, envelope movement,
    sideband energy and slow modulation depth. They are research observables,
    not a calibrated propagation or drone model.
    """
    cfg = cfg or DetectorConfig()
    x = np.asarray(samples, dtype=float)
    if len(x) < cfg.n_fft:
        x = np.pad(x, (0, cfg.n_fft - len(x)))

    freqs = np.fft.rfftfreq(cfg.n_fft, d=1.0 / cfg.sample_rate)
    window = np.hanning(cfg.n_fft)
    relevant = (freqs >= 40.0) & (freqs <= cfg.sample_rate / 2)

    rows = []
    previous_norm = None
    envelope_history = deque(maxlen=max(4, int(round(1.0 / (cfg.hop / cfg.sample_rate)))))

    for frame_index, start in enumerate(range(0, len(x) - cfg.n_fft + 1, cfg.hop)):
        frame = x[start : start + cfg.n_fft]
        power = np.abs(np.fft.rfft(frame * window)) ** 2
        total = float(power[relevant].sum()) + 1e-18
        norm = power / total

        rms = float(np.sqrt(np.mean(frame * frame)))
        envelope_history.append(rms)
        hist = np.asarray(envelope_history, dtype=float)
        if len(hist) >= 3:
            p10, p90 = np.percentile(hist, [10, 90])
            modulation_depth = float((p90 - p10) / (np.median(hist) + 1e-12))
        else:
            modulation_depth = 0.0

        spectral_flux = 0.0
        if previous_norm is not None:
            spectral_flux = float(np.maximum(norm - previous_norm, 0.0).sum())
        previous_norm = norm

        centroid = float((freqs[relevant] * power[relevant]).sum() / total)
        rel_power = power[relevant] + 1e-18
        spectral_flatness = float(
            np.exp(np.mean(np.log(rel_power))) / (np.mean(rel_power) + 1e-18)
        )

        detector_row = detector_rows[frame_index] if frame_index < len(detector_rows) else {}
        f0 = float(detector_row.get("best_f0", 0.0))

        row = {
            "spectral_centroid_hz": centroid,
            "spectral_flatness": spectral_flatness,
            "spectral_flux": spectral_flux,
            "amplitude_envelope": rms,
            "envelope_delta": 0.0 if not rows else rms - rows[-1]["amplitude_envelope"],
            "modulation_depth": modulation_depth,
            "sideband_ratio": _sideband_ratio(power, freqs, f0),
            "low_frequency_share": _band_power(power, freqs, 40.0, 250.0) / total,
            "high_frequency_share": _band_power(power, freqs, 2000.0, 8000.0) / total,
        }
        for name, (low, high) in FREQUENCY_BANDS.items():
            row[name] = _band_power(power, freqs, low, high) / total
        rows.append(row)

    return rows
