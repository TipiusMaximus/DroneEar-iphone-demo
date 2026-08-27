from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt


def simulate_distance(samples, sample_rate, *, attenuation_db=12.0, lowpass_hz=3500.0, noise_level=0.01, comb_delay_ms=2.0, comb_gain=0.25, slow_fade_depth=0.12, seed=1234):
    """Create a controlled, explicitly synthetic farther-field version.

    This is not an atmospheric propagation solver. It combines effects that
    commonly become important with distance: level loss, high-frequency loss,
    background masking, direct+reflected-path combing, and slow amplitude
    fluctuation. The output is only for robustness testing.
    """
    x = np.asarray(samples, dtype=float).copy()
    gain = 10.0 ** (-float(attenuation_db) / 20.0)
    x *= gain

    nyquist = sample_rate / 2.0
    cutoff = min(max(float(lowpass_hz), 100.0), nyquist * 0.95)
    sos = butter(4, cutoff / nyquist, btype="lowpass", output="sos")
    x = sosfiltfilt(sos, x)

    delay = max(1, int(round(float(comb_delay_ms) * sample_rate / 1000.0)))
    reflected = np.zeros_like(x)
    reflected[delay:] = x[:-delay]
    x = x + float(comb_gain) * reflected

    if slow_fade_depth > 0.0:
        t = np.arange(len(x)) / float(sample_rate)
        # Deterministic slow fluctuation; not intended to model one exact wind field.
        fade = 1.0 + float(slow_fade_depth) * (
            0.6 * np.sin(2 * np.pi * 0.7 * t) + 0.4 * np.sin(2 * np.pi * 1.3 * t + 0.8)
        )
        x *= fade

    if noise_level > 0.0:
        rng = np.random.default_rng(seed)
        # Mild low-frequency-coloured background plus white component.
        white = rng.standard_normal(len(x))
        coloured = np.cumsum(rng.standard_normal(len(x)))
        coloured -= np.mean(coloured)
        coloured /= np.std(coloured) + 1e-12
        noise = 0.75 * white + 0.25 * coloured
        noise /= np.std(noise) + 1e-12
        x += float(noise_level) * noise

    return np.clip(x, -0.999, 0.999)


DISTANCE_PRESETS = {
    "near": dict(attenuation_db=0.0, lowpass_hz=7600.0, noise_level=0.002, comb_delay_ms=1.0, comb_gain=0.08, slow_fade_depth=0.03),
    "mid": dict(attenuation_db=12.0, lowpass_hz=4000.0, noise_level=0.008, comb_delay_ms=1.8, comb_gain=0.18, slow_fade_depth=0.08),
    "far": dict(attenuation_db=24.0, lowpass_hz=2200.0, noise_level=0.018, comb_delay_ms=2.6, comb_gain=0.30, slow_fade_depth=0.16),
}
