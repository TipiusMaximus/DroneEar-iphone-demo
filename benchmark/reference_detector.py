from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

@dataclass
class DetectorConfig:
    sample_rate: int = 16000
    n_fft: int = 4096
    hop: int = 1024
    # Research branch only: broaden candidate fundamentals so the DDP study is
    # not locked to the live browser detector's earlier 60–400 Hz assumption.
    f0_min: float = 40.0
    f0_max: float = 800.0
    n_harmonics: int = 6
    min_freq: float = 40.0
    max_freq: float = 8000.0
    silence_rms: float = 2e-4
    possible: float = 0.55
    detected: float = 0.72
    detected_seconds: float = 2.0
    clear: float = 0.45
    clear_seconds: float = 3.0
    smooth: float = 0.35
    weight_harmonic: float = 0.40
    weight_contrast: float = 0.20
    weight_consistency: float = 0.15
    weight_track: float = 0.15
    weight_band: float = 0.10
    octave_score_margin: float = 0.05
    octave_score_ratio: float = 0.92
    octave_rel_tol: float = 0.04
    octave_bin_tol: float = 2.0
    octave_multiples: tuple = (2, 3)
    octave_apply_above_hz: float = 200.0

STATE_RANK = {"CLEAR": 0, "POSSIBLE": 1, "DETECTED": 2}

def clip01(v):
    return float(np.clip(v, 0.0, 1.0))


def prefer_lower_octave_candidate(scored, best, cfg, bin_hz):
    if best is None or not scored:
        return best
    preferred = best
    for _ in range(3):
        best_score = float(preferred["harmonic_score"])
        best_f0 = float(preferred["best_f0"])
        if best_f0 <= 0.0 or best_score <= 0.0:
            break
        if best_f0 <= cfg.octave_apply_above_hz:
            break
        nxt = preferred
        for k in cfg.octave_multiples:
            target = best_f0 / float(k)
            if target < cfg.f0_min:
                continue
            tol = max(cfg.octave_rel_tol * target, cfg.octave_bin_tol * bin_hz)
            for cand in scored:
                f0 = float(cand["best_f0"])
                if abs(f0 - target) > tol:
                    continue
                s = float(cand["harmonic_score"])
                close_enough = s >= best_score - cfg.octave_score_margin or s >= cfg.octave_score_ratio * best_score
                if not close_enough:
                    continue
                competitive_struct = (
                    int(cand["harmonic_hits"]) >= int(preferred["harmonic_hits"]) - 1
                    or float(cand["harmonic_consistency"]) >= float(preferred["harmonic_consistency"]) - 0.17
                )
                if not competitive_struct and s < best_score - 0.02:
                    continue
                if f0 < float(nxt["best_f0"]) - 1e-9:
                    nxt = cand
        if nxt is preferred:
            break
        preferred = nxt
    return preferred

def pcm_to_float(x):
    x = np.asarray(x)
    if np.issubdtype(x.dtype, np.floating):
        return x.astype(np.float64)
    if x.dtype == np.uint8:
        return (x.astype(np.float64) - 128.0) / 128.0
    info = np.iinfo(x.dtype)
    scale = max(abs(info.min), abs(info.max))
    return x.astype(np.float64) / float(scale)

def load_audio(path, target_sr=16000):
    sr, x = wavfile.read(str(path))
    x = pcm_to_float(x)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if sr != target_sr:
        g = math.gcd(int(sr), int(target_sr))
        x = resample_poly(x, target_sr // g, sr // g)
        sr = target_sr
    return sr, np.asarray(x, dtype=np.float64)

def track_stability(history, f0, confident):
    if not confident:
        return 0.20, history[-10:]
    h = (history + [float(f0)])[-24:]
    if len(h) < 3:
        return 0.50, h
    jumps = np.abs(np.diff(np.asarray(h)))
    median_jump = float(np.median(jumps))
    return clip01(1.0 - median_jump / 25.0), h

def analyze_frame(frame, cfg):
    if len(frame) != cfg.n_fft:
        raise ValueError(f"Expected {cfg.n_fft} samples, got {len(frame)}")

    frame = np.asarray(frame, dtype=np.float64)
    rms = float(np.sqrt(np.mean(frame * frame)))
    spectrum = np.fft.rfft(frame * np.hanning(cfg.n_fft))
    power = np.abs(spectrum) ** 2
    freqs = np.fft.rfftfreq(cfg.n_fft, d=1.0 / cfg.sample_rate)

    relevant = (freqs >= cfg.min_freq) & (freqs <= min(cfg.max_freq, cfg.sample_rate / 2))
    total_power = float(power[relevant].sum()) + 1e-18
    mechanical = (freqs >= 40.0) & (freqs <= 2000.0)
    mechanical_band_score = clip01(float(power[mechanical].sum()) / total_power)

    candidates = freqs[(freqs >= cfg.f0_min) & (freqs <= cfg.f0_max)]
    bin_hz = float(freqs[1] - freqs[0]) if len(freqs) > 1 else float(cfg.sample_rate) / float(cfg.n_fft)
    scored = []

    for f0 in candidates:
        harmonic_power = 0.0
        hits = 0
        count = 0
        contrast_values = []

        for k in range(1, cfg.n_harmonics + 1):
            target = float(k * f0)
            if target >= cfg.sample_rate / 2:
                break
            tol = max(8.0, 0.045 * target)
            hm = (freqs >= target - tol) & (freqs <= target + tol)
            bg = (
                ((freqs >= target - 3 * tol) & (freqs < target - 1.5 * tol))
                | ((freqs > target + 1.5 * tol) & (freqs <= target + 3 * tol))
            ) & relevant
            if not hm.any():
                continue

            h_power = float(power[hm].sum())
            h_fraction = h_power / total_power
            h_mean = float(power[hm].mean()) + 1e-18
            b_floor = float(np.median(power[bg])) + 1e-18 if bg.any() else total_power / max(1, int(relevant.sum()))
            contrast_db = 10.0 * math.log10(h_mean / b_floor)
            contrast_values.append(contrast_db)
            harmonic_power += h_power
            count += 1
            if contrast_db >= 6.0 and h_fraction >= 0.003:
                hits += 1

        if count == 0:
            continue

        energy_ratio = clip01(harmonic_power / total_power)
        consistency = hits / count
        contrast_db = float(np.median(contrast_values)) if contrast_values else 0.0
        contrast_norm = clip01((contrast_db - 1.0) / 19.0)
        coverage_gate = clip01((hits - 1) / 3.0)
        harmonic_score = clip01(coverage_gate * (
            0.35 * energy_ratio
            + 0.40 * consistency
            + 0.25 * contrast_norm
        ))

        scored.append({
            "best_f0": float(f0),
            "harmonic_score": harmonic_score,
            "harmonic_energy_ratio": energy_ratio,
            "harmonic_hits": int(hits),
            "harmonic_count": int(count),
            "harmonic_consistency": float(consistency),
            "harmonic_contrast_db": float(contrast_db),
            "harmonic_contrast_norm": float(contrast_norm),
        })

    best = None
    if scored:
        best = max(scored, key=lambda c: c["harmonic_score"])
        best = prefer_lower_octave_candidate(scored, best, cfg, bin_hz)

    if best is None:
        best = {
            "best_f0": 0.0,
            "harmonic_score": 0.0,
            "harmonic_energy_ratio": 0.0,
            "harmonic_hits": 0,
            "harmonic_count": 0,
            "harmonic_consistency": 0.0,
            "harmonic_contrast_db": 0.0,
            "harmonic_contrast_norm": 0.0,
        }

    best["rms"] = rms
    best["mechanical_band_score"] = mechanical_band_score
    return best

class Persistence:
    def __init__(self, cfg):
        self.cfg = cfg
        self.state = "CLEAR"
        self.smoothed = 0.0
        self.initialized = False
        self.high_time = 0.0
        self.low_time = 0.0

    def update(self, raw_score, dt):
        c = self.cfg
        s_in = clip01(raw_score)
        self.smoothed = c.smooth * s_in + (1 - c.smooth) * self.smoothed if self.initialized else s_in
        self.initialized = True
        s = self.smoothed

        if self.state == "CLEAR":
            self.low_time = 0.0
            if s >= c.possible:
                self.state = "POSSIBLE"
                self.high_time = dt if s >= c.detected else 0.0
            else:
                self.high_time = 0.0
        elif self.state == "POSSIBLE":
            if s >= c.detected:
                self.high_time += dt
                if self.high_time >= c.detected_seconds:
                    self.state = "DETECTED"
            elif s >= c.possible:
                self.high_time = 0.0
            else:
                self.state = "CLEAR"
                self.high_time = 0.0
        elif self.state == "DETECTED":
            if s < c.clear:
                self.low_time += dt
                if self.low_time >= c.clear_seconds:
                    self.state = "CLEAR"
                    self.high_time = 0.0
                    self.low_time = 0.0
            else:
                self.low_time = 0.0
        return self.state, float(self.smoothed)

def analyze_clip(samples, cfg=None):
    cfg = cfg or DetectorConfig()
    x = np.asarray(samples, dtype=np.float64)
    if len(x) < cfg.n_fft:
        x = np.pad(x, (0, cfg.n_fft - len(x)))

    history = []
    persistence = Persistence(cfg)
    rows = []
    dt = cfg.hop / cfg.sample_rate
    max_state = "CLEAR"

    for start in range(0, len(x) - cfg.n_fft + 1, cfg.hop):
        f = analyze_frame(x[start:start + cfg.n_fft], cfg)
        stability, history = track_stability(history, f["best_f0"], f["harmonic_score"] >= 0.25)

        raw = clip01(
            cfg.weight_harmonic * f["harmonic_score"]
            + cfg.weight_contrast * f["harmonic_contrast_norm"]
            + cfg.weight_consistency * f["harmonic_consistency"]
            + cfg.weight_track * stability
            + cfg.weight_band * f["mechanical_band_score"]
        )
        if f["rms"] < cfg.silence_rms:
            raw = 0.0

        state, smoothed = persistence.update(raw, dt)
        if STATE_RANK[state] > STATE_RANK[max_state]:
            max_state = state

        f.update({
            "track_stability": float(stability),
            "raw_score": float(raw),
            "smoothed_score": float(smoothed),
            "state": state,
            "time_s": float(start / cfg.sample_rate),
        })
        rows.append(f)

    scores = np.asarray([r["raw_score"] for r in rows], dtype=float)
    states = [r["state"] for r in rows]

    def med(key):
        vals = [float(r[key]) for r in rows if np.isfinite(float(r[key]))]
        return float(np.median(vals)) if vals else 0.0

    summary = {
        "frames": len(rows),
        "mean_score": float(scores.mean()) if len(scores) else 0.0,
        "p95_score": float(np.percentile(scores, 95)) if len(scores) else 0.0,
        "max_score": float(scores.max()) if len(scores) else 0.0,
        "detected_fraction": float(sum(s == "DETECTED" for s in states) / max(1, len(states))),
        "max_state": max_state,
        "median_best_f0": med("best_f0"),
        "median_harmonic_consistency": med("harmonic_consistency"),
        "median_harmonic_contrast_db": med("harmonic_contrast_db"),
        "median_track_stability": med("track_stability"),
    }
    return rows, summary

def analyze_wav(path, cfg=None):
    cfg = cfg or DetectorConfig()
    _, x = load_audio(path, cfg.sample_rate)
    return analyze_clip(x, cfg)
