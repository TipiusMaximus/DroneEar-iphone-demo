from __future__ import annotations

import numpy as np


def _bucket(value, ordered_values, labels):
    if not ordered_values:
        return labels[1]
    index = ordered_values.index(value)
    if len(ordered_values) <= 1:
        return labels[1]
    ratio = index / max(len(ordered_values) - 1, 1)
    if ratio < 1 / 3:
        return labels[0]
    if ratio < 2 / 3:
        return labels[1]
    return labels[2]


def build_motifs(rankings):
    """Aggregate nearby winning parameter sets into lightweight motif families.

    This mirrors the universal_ddp motif idea without importing that repository.
    The output is deliberately descriptive: it identifies repeatable families
    worth testing, not a production classifier.
    """
    if not rankings:
        return []

    delays = sorted({row["delay"] for row in rankings})
    gains = sorted({row["gain"] for row in rankings})
    groups = {}

    for row in rankings:
        delay_bucket = _bucket(row["delay"], delays, ["short_delay", "mid_delay", "long_delay"])
        gain_bucket = _bucket(row["gain"], gains, ["low_gain", "mid_gain", "high_gain"])
        key = (row["feature"], row["polarity_rule"], delay_bucket, gain_bucket)
        groups.setdefault(key, []).append(row)

    motifs = []
    for (feature, polarity_rule, delay_bucket, gain_bucket), rows in groups.items():
        consensus = np.asarray([float(row["consensus_score"]) for row in rows])
        robust = np.asarray([float(row["robustness_score"]) for row in rows])
        strong = sum(row["consensus_flag"] == "consensus_strong" for row in rows)
        motif_score = float(
            0.45 * np.median(consensus)
            + 0.30 * np.mean(consensus)
            + 0.15 * np.median(robust)
            + 0.10 * (strong / len(rows))
        )
        motifs.append(
            {
                "motif_family": f"{feature} / {polarity_rule} / {delay_bucket} / {gain_bucket}",
                "feature": feature,
                "polarity_rule": polarity_rule,
                "delay_bucket": delay_bucket,
                "gain_bucket": gain_bucket,
                "row_count": len(rows),
                "strong_count": int(strong),
                "median_consensus": float(np.median(consensus)),
                "mean_consensus": float(np.mean(consensus)),
                "median_robustness": float(np.median(robust)),
                "motif_score": motif_score,
                "motif_flag": (
                    "motif_strong" if strong >= 2 and motif_score >= 0.55
                    else "motif_emerging" if strong >= 1 or motif_score >= 0.35
                    else "motif_weak"
                ),
            }
        )

    return sorted(motifs, key=lambda row: row["motif_score"], reverse=True)
