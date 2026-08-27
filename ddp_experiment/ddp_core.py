from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np


@dataclass(frozen=True)
class DDPParams:
    delay: int
    gain: float
    polarity_rule: str

    @property
    def key(self) -> str:
        gain = str(self.gain).replace(".", "p")
        return f"d{self.delay}_g{gain}_{self.polarity_rule}"


def compute_ddp_score(
    signal,
    *,
    delay: int,
    gain: float,
    polarity_rule: str,
    threshold: float = 0.0,
):
    """NumPy port of the universal_ddp feedback proxy.

    Formula intentionally mirrors universal_ddp/core/ddp_engine.py:

        delayed = signal(t-D)
        gradient = diff(signal)(t-D)
        score = polarity * (delayed + gain * gradient)

    This branch keeps a local minimal port so DroneEar does not depend on the
    separate private universal_ddp repository at runtime.
    """
    x = np.asarray(signal, dtype=float)
    if x.ndim != 1:
        raise ValueError("signal must be one-dimensional")
    if delay < 0:
        raise ValueError("delay must be >= 0")

    n = len(x)
    delayed = np.zeros(n, dtype=float)
    gradient = np.zeros(n, dtype=float)
    diff = np.zeros(n, dtype=float)
    if n > 1:
        diff[1:] = np.diff(x)

    if delay == 0:
        delayed[:] = x
        gradient[:] = diff
    elif delay < n:
        delayed[delay:] = x[:-delay]
        gradient[delay:] = diff[:-delay]

    if polarity_rule == "fixed_positive":
        polarity = np.ones(n, dtype=float)
    elif polarity_rule == "fixed_negative":
        polarity = -np.ones(n, dtype=float)
    elif polarity_rule == "threshold_switch":
        polarity = np.where(delayed >= threshold, 1.0, -1.0)
    else:
        raise ValueError(f"Unsupported polarity rule: {polarity_rule}")

    return np.nan_to_num(polarity * (delayed + gain * gradient))


def structure_metrics(signal, ddp_score):
    """Compress one DDP score series into scale-aware temporal structure metrics."""
    x = np.asarray(signal, dtype=float)
    s = np.asarray(ddp_score, dtype=float)
    if len(s) == 0:
        return {
            "median_abs": 0.0,
            "q90_abs": 0.0,
            "sign_persistence": 0.0,
            "smoothness": 0.0,
            "structure_score": 0.0,
        }

    abs_s = np.abs(s)
    median_abs = float(np.median(abs_s))
    q90_abs = float(np.percentile(abs_s, 90))

    nonzero = np.flatnonzero(np.abs(s) > 1e-12)
    sign_persistence = 0.0
    if len(nonzero) >= 2:
        signs = np.sign(s[nonzero])
        sign_persistence = float(np.mean(signs[1:] == signs[:-1]))

    diff_median = float(np.median(np.abs(np.diff(s)))) if len(s) > 1 else 0.0
    smoothness = float(1.0 / (1.0 + diff_median / (median_abs + 1e-12)))

    centered = x - np.median(x) if len(x) else x
    feature_scale = float(np.median(np.abs(centered))) + 1e-12
    amplitude = float(q90_abs / (q90_abs + feature_scale))

    structure_score = float(
        np.clip(
            0.45 * sign_persistence
            + 0.35 * smoothness
            + 0.20 * amplitude,
            0.0,
            1.0,
        )
    )
    return {
        "median_abs": median_abs,
        "q90_abs": q90_abs,
        "sign_persistence": sign_persistence,
        "smoothness": smoothness,
        "structure_score": structure_score,
    }


def sweep_feature_series(
    feature_series: dict[str, np.ndarray],
    *,
    delays=(1, 2, 4, 8, 16),
    gains=(0.0, 0.5, 1.0),
    polarity_rules=("fixed_positive", "threshold_switch"),
):
    """Run a compact DDP parameter sweep over detector-feature time series."""
    rows = []
    for feature, signal in feature_series.items():
        x = np.asarray(signal, dtype=float)
        threshold = float(np.median(x)) if len(x) else 0.0
        for delay, gain, polarity_rule in product(delays, gains, polarity_rules):
            ddp = compute_ddp_score(
                x,
                delay=int(delay),
                gain=float(gain),
                polarity_rule=polarity_rule,
                threshold=threshold,
            )
            metrics = structure_metrics(x, ddp)
            rows.append(
                {
                    "feature": feature,
                    "delay": int(delay),
                    "gain": float(gain),
                    "polarity_rule": polarity_rule,
                    **metrics,
                }
            )
    return rows


def auc_pairwise(positives, negatives):
    """Small dependency-free AUC equivalent using pairwise ranking."""
    p = np.asarray(list(positives), dtype=float)
    n = np.asarray(list(negatives), dtype=float)
    if len(p) == 0 or len(n) == 0:
        return float("nan")
    wins = 0.0
    total = 0
    for a in p:
        for b in n:
            total += 1
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
    return wins / total


def rank_parameter_rows(rows):
    """Rank DDP parameter sets by drone-vs-negative repeatable separation.

    Positive labels are `drone` and `drone_like_synthetic`; `no_drone` is the
    negative class. Ranking is intentionally research-only and must not be
    interpreted as a calibrated detector probability.
    """
    groups = {}
    for row in rows:
        label = row["label"]
        if label not in {"drone", "drone_like_synthetic", "no_drone"}:
            continue
        key = (
            row["feature"],
            int(row["delay"]),
            float(row["gain"]),
            row["polarity_rule"],
        )
        groups.setdefault(key, []).append(row)

    ranked = []
    for (feature, delay, gain, polarity_rule), values in groups.items():
        positive = [
            float(v["structure_score"])
            for v in values
            if v["label"] in {"drone", "drone_like_synthetic"}
        ]
        negative = [
            float(v["structure_score"])
            for v in values
            if v["label"] == "no_drone"
        ]
        if not positive or not negative:
            continue

        auc = auc_pairwise(positive, negative)
        ranked.append(
            {
                "feature": feature,
                "delay": delay,
                "gain": gain,
                "polarity_rule": polarity_rule,
                "positive_clips": len(positive),
                "negative_clips": len(negative),
                "positive_median": float(np.median(positive)),
                "negative_median": float(np.median(negative)),
                "auc": float(auc),
                "separation_score": float(2.0 * auc - 1.0),
            }
        )

    _add_robustness(ranked)
    _add_consensus(ranked)
    return sorted(
        ranked,
        key=lambda r: (
            r["consensus_score"],
            r["robustness_score"],
            r["separation_score"],
        ),
        reverse=True,
    )


def _neighbor_rows(group, center, delay_positions, gain_positions):
    return [
        row
        for row in group
        if row is not center
        and abs(delay_positions[row["delay"]] - delay_positions[center["delay"]]) <= 1
        and abs(gain_positions[row["gain"]] - gain_positions[center["gain"]]) <= 1
    ]


def _add_robustness(rows):
    """Mirror universal_ddp's main idea: reward a local parameter-space island."""
    groups = {}
    for row in rows:
        groups.setdefault((row["feature"], row["polarity_rule"]), []).append(row)

    for group in groups.values():
        delays = sorted({row["delay"] for row in group})
        gains = sorted({row["gain"] for row in group})
        delay_positions = {value: i for i, value in enumerate(delays)}
        gain_positions = {value: i for i, value in enumerate(gains)}

        for row in group:
            neighbors = _neighbor_rows(group, row, delay_positions, gain_positions)
            neighbor_median = (
                float(np.median([n["separation_score"] for n in neighbors]))
                if neighbors
                else float(row["separation_score"])
            )
            row["neighbor_count"] = len(neighbors)
            row["neighbor_median_separation"] = neighbor_median
            row["robustness_score"] = (
                0.5 * float(row["separation_score"]) + 0.5 * neighbor_median
            )
            row["robustness_flag"] = (
                "robust"
                if float(row["separation_score"]) >= 0.4 and neighbor_median >= 0.3
                else "fragile"
            )


def _add_consensus(rows):
    """Reward repeatability across nearby delay/gain parameter choices."""
    groups = {}
    for row in rows:
        groups.setdefault((row["feature"], row["polarity_rule"]), []).append(row)

    for group in groups.values():
        delays = sorted({row["delay"] for row in group})
        gains = sorted({row["gain"] for row in group})
        delay_positions = {value: i for i, value in enumerate(delays)}
        gain_positions = {value: i for i, value in enumerate(gains)}

        for row in group:
            neighbors = _neighbor_rows(group, row, delay_positions, gain_positions)
            good = [n for n in neighbors if float(n["separation_score"]) >= 0.3]
            share = len(good) / len(neighbors) if neighbors else 0.0
            row["repeat_good_neighbor_share"] = float(share)
            row["consensus_score"] = (
                0.75 * float(row["robustness_score"]) + 0.25 * float(share)
            )
            row["consensus_flag"] = (
                "consensus_strong"
                if row["robustness_flag"] == "robust" and share >= 0.4
                else "consensus_moderate"
                if row["robustness_flag"] == "robust" or share >= 0.3
                else "consensus_weak"
            )
