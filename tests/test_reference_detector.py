from pathlib import Path
import sys, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.reference_detector import analyze_clip, analyze_wav

def harmonic_signal(f0=90.0, seconds=6.0, sr=16000):
    t = np.arange(int(seconds*sr))/sr
    x = sum((1.0/k)*np.sin(2*np.pi*f0*k*t) for k in range(1,7))
    x /= np.max(np.abs(x))
    return 0.30*x

def single_sine(f=90.0, seconds=6.0, sr=16000):
    t = np.arange(int(seconds*sr))/sr
    return 0.30*np.sin(2*np.pi*f*t)

def white_noise(seconds=6.0, sr=16000):
    rng = np.random.default_rng(123)
    return 0.05*rng.standard_normal(int(seconds*sr))

def test_harmonic_recovers_f0():
    _, s = analyze_clip(harmonic_signal())
    assert abs(s["median_best_f0"]-90.0) < 8.0

def test_harmonic_scores_above_sine_and_noise():
    _, h = analyze_clip(harmonic_signal())
    _, s = analyze_clip(single_sine())
    _, n = analyze_clip(white_noise())
    assert h["p95_score"] > s["p95_score"] + 0.25
    assert h["p95_score"] > n["p95_score"] + 0.40

def test_score_bounds():
    rows, _ = analyze_clip(harmonic_signal())
    assert rows
    assert all(0 <= r["raw_score"] <= 1 for r in rows)
    assert all(0 <= r["smoothed_score"] <= 1 for r in rows)

def test_harmonic_reaches_detected():
    _, s = analyze_clip(harmonic_signal())
    assert s["max_state"] == "DETECTED"

def test_single_sine_not_detected():
    _, s = analyze_clip(single_sine())
    assert s["max_state"] != "DETECTED"

def test_white_noise_not_detected():
    _, s = analyze_clip(white_noise())
    assert s["max_state"] != "DETECTED"

def test_slow_f0_sweep_stays_strong():
    sr = 16000
    n = int(6*sr)
    f = np.linspace(80.0,110.0,n)
    phase = 2*np.pi*np.cumsum(f)/sr
    x = sum((1.0/k)*np.sin(k*phase) for k in range(1,7))
    x /= np.max(np.abs(x))
    _, s = analyze_clip(0.30*x)
    assert s["p95_score"] > 0.75
    assert 75 <= s["median_best_f0"] <= 115


def test_generated_wav_harmonic_is_detected():
    path = ROOT / "example_data" / "synthetic" / "harmonic_90.wav"
    _, s = analyze_wav(path)
    assert abs(s["median_best_f0"] - 90.0) < 8.0
    assert s["max_state"] == "DETECTED"


def test_generated_wav_single_sine_is_not_detected():
    path = ROOT / "example_data" / "synthetic" / "single_sine_90.wav"
    _, s = analyze_wav(path)
    assert s["max_state"] != "DETECTED"
