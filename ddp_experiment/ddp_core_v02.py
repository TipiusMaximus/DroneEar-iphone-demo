from __future__ import annotations

from itertools import product

import numpy as np

from ddp_experiment.ddp_core import compute_ddp_score, structure_metrics, auc_pairwise


def _delay_source_and_target_gradient(source, target, delay):
    source = np.asarray(source, dtype=float)
    target = np.asarray(target, dtype=float)
    n = min(len(source), len(target))
    source = source[:n]
    target = target[:n]
    delayed = np.zeros(n, dtype=float)
    gradient = np.zeros(n, dtype=float)
    diff = np.zeros(n, dtype=float)
    if n > 1:
        diff[1:] = np.diff(target)
    if delay == 0:
        delayed[:] = source
        gradient[:] = diff
    elif delay < n:
        delayed[delay:] = source[:-delay]
        gradient[delay:] = diff[:-delay]
    return delayed, gradient


def compute_cross_ddp_score(source, target, *, delay, gain, polarity_rule, threshold=0.0):
    """Experimental cross-feature DDP extension.

    This is not claimed to be universal_ddp's original formula. It preserves
    the delayed-source term and lets another feature's delayed gradient provide
    the feedback term:

        score = polarity(delayed_source) *
                (delayed_source + gain * delayed_target_gradient)

    `gain=0` is the mandatory ablation baseline.
    """
    delayed, target_gradient = _delay_source_and_target_gradient(source, target, int(delay))
    if polarity_rule == "fixed_positive":
        polarity = np.ones(len(delayed), dtype=float)
    elif polarity_rule == "fixed_negative":
        polarity = -np.ones(len(delayed), dtype=float)
    elif polarity_rule == "threshold_switch":
        polarity = np.where(delayed >= threshold, 1.0, -1.0)
    else:
        raise ValueError(f"Unsupported polarity rule: {polarity_rule}")
    return np.nan_to_num(polarity * (delayed + float(gain) * target_gradient))


DEFAULT_CROSS_FEATURE_PAIRS = (
    ("f0_delta", "harmonic_contrast_db"),
    ("amplitude_envelope", "sideband_ratio"),
    ("sideband_ratio", "harmonic_score"),
    ("modulation_depth", "sideband_ratio"),
    ("spectral_flux", "harmonic_contrast_db"),
    ("high_frequency_share", "harmonic_score"),
    ("low_frequency_share", "harmonic_score"),
    ("band_40_120_ratio", "band_500_1000_ratio"),
    ("band_120_250_ratio", "band_1000_2000_ratio"),
)


def sweep_feature_series_v02(feature_series, *, delays=(1, 2, 4, 8, 16), gains=(0.0, 0.5, 1.0), polarity_rules=("fixed_positive", "threshold_switch"), include_same_feature=True, cross_pairs=DEFAULT_CROSS_FEATURE_PAIRS):
    rows = []

    if include_same_feature:
        for feature, signal in feature_series.items():
            x = np.asarray(signal, dtype=float)
            threshold = float(np.median(x)) if len(x) else 0.0
            for delay, gain, polarity_rule in product(delays, gains, polarity_rules):
                ddp = compute_ddp_score(
                    x, delay=int(delay), gain=float(gain),
                    polarity_rule=polarity_rule, threshold=threshold,
                )
                rows.append({
                    "feature": feature,
                    "source_feature": feature,
                    "target_feature": feature,
                    "ddp_mode": "same_feature",
                    "delay": int(delay),
                    "gain": float(gain),
                    "polarity_rule": polarity_rule,
                    **structure_metrics(x, ddp),
                })

    for source_name, target_name in cross_pairs:
        if source_name not in feature_series or target_name not in feature_series:
            continue
        source = np.asarray(feature_series[source_name], dtype=float)
        target = np.asarray(feature_series[target_name], dtype=float)
        n = min(len(source), len(target))
        source = source[:n]
        target = target[:n]
        threshold = float(np.median(source)) if n else 0.0
        feature_name = f"{source_name}->{target_name}"
        for delay, gain, polarity_rule in product(delays, gains, polarity_rules):
            ddp = compute_cross_ddp_score(
                source, target,
                delay=int(delay), gain=float(gain),
                polarity_rule=polarity_rule, threshold=threshold,
            )
            rows.append({
                "feature": feature_name,
                "source_feature": source_name,
                "target_feature": target_name,
                "ddp_mode": "cross_feature",
                "delay": int(delay),
                "gain": float(gain),
                "polarity_rule": polarity_rule,
                **structure_metrics(source, ddp),
            })
    return rows


def rank_parameter_rows_v02(rows):
    groups = {}
    for row in rows:
        if row.get("label") not in {"drone", "drone_like_synthetic", "no_drone"}:
            continue
        key = (row["feature"], int(row["delay"]), float(row["gain"]), row["polarity_rule"])
        groups.setdefault(key, []).append(row)

    ranked = []
    for (feature, delay, gain, rule), values in groups.items():
        positive = [float(v["structure_score"]) for v in values if v["label"] in {"drone", "drone_like_synthetic"}]
        negative = [float(v["structure_score"]) for v in values if v["label"] == "no_drone"]
        if not positive or not negative:
            continue
        auc = auc_pairwise(positive, negative)
        first = values[0]
        ranked.append({
            "feature": feature,
            "source_feature": first.get("source_feature", feature),
            "target_feature": first.get("target_feature", feature),
            "ddp_mode": first.get("ddp_mode", "same_feature"),
            "delay": delay,
            "gain": gain,
            "polarity_rule": rule,
            "positive_clips": len(positive),
            "negative_clips": len(negative),
            "positive_median": float(np.median(positive)),
            "negative_median": float(np.median(negative)),
            "auc": float(auc),
            "separation_score": float(2.0 * auc - 1.0),
        })

    _add_robustness_v02(ranked)
    _add_consensus_v02(ranked)
    return sorted(
        ranked,
        key=lambda r: (r["consensus_score"], r["robustness_score"], r["separation_score"]),
        reverse=True,
    )


def _neighbor_rows(group, center, delay_positions, gain_positions):
    return [
        row for row in group
        if row is not center
        and abs(delay_positions[row["delay"]] - delay_positions[center["delay"]]) <= 1
        and abs(gain_positions[row["gain"]] - gain_positions[center["gain"]]) <= 1
    ]


def _add_robustness_v02(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["feature"], row["polarity_rule"]), []).append(row)

    for group in groups.values():
        delays = sorted({r["delay"] for r in group})
        gains = sorted({r["gain"] for r in group})
        dpos = {v: i for i, v in enumerate(delays)}
        gpos = {v: i for i, v in enumerate(gains)}
        for row in group:
            neighbors = _neighbor_rows(group, row, dpos, gpos)
            row["neighbor_count"] = len(neighbors)
            if not neighbors:
                row["neighbor_median_separation"] = float("nan")
                row["robustness_score"] = float(row["separation_score"])
                row["robustness_flag"] = "isolated"
                continue
            median = float(np.median([n["separation_score"] for n in neighbors]))
            row["neighbor_median_separation"] = median
            row["robustness_score"] = 0.5 * float(row["separation_score"]) + 0.5 * median
            row["robustness_flag"] = "robust" if float(row["separation_score"]) >= 0.4 and median >= 0.3 else "fragile"


def _add_consensus_v02(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["feature"], row["polarity_rule"]), []).append(row)

    for group in groups.values():
        delays = sorted({r["delay"] for r in group})
        gains = sorted({r["gain"] for r in group})
        dpos = {v: i for i, v in enumerate(delays)}
        gpos = {v: i for i, v in enumerate(gains)}
        for row in group:
            neighbors = _neighbor_rows(group, row, dpos, gpos)
            good = [n for n in neighbors if float(n["separation_score"]) >= 0.3]
            share = len(good) / len(neighbors) if neighbors else 0.0
            row["repeat_good_neighbor_share"] = float(share)
            row["consensus_score"] = 0.75 * float(row["robustness_score"]) + 0.25 * float(share)
            row["consensus_flag"] = (
                "consensus_strong"
                if row["robustness_flag"] == "robust" and share >= 0.4
                else "consensus_moderate"
                if row["robustness_flag"] == "robust" or share >= 0.3
                else "consensus_weak"
            )
