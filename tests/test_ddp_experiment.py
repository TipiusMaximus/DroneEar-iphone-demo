import numpy as np

from benchmark.reference_detector import analyze_clip
from ddp_experiment.audio_adapter import rows_to_feature_series, robust_zscore
from ddp_experiment.ddp_core import (
    compute_ddp_score,
    rank_parameter_rows,
    sweep_feature_series,
)
from ddp_experiment.motifs import build_motifs


def test_compute_ddp_score_matches_feedback_proxy():
    x = np.asarray([0.0, 1.0, 3.0, 6.0, 10.0])
    got = compute_ddp_score(
        x,
        delay=1,
        gain=0.5,
        polarity_rule="fixed_positive",
    )
    expected = np.asarray([0.0, 0.0, 1.5, 4.0, 7.5])
    assert np.allclose(got, expected)


def test_robust_zscore_handles_constant_series():
    assert np.allclose(robust_zscore(np.ones(10)), 0.0)


def test_detector_rows_can_be_adapted_to_ddp_features():
    sr = 16000
    t = np.arange(6 * sr) / sr
    signal = sum(
        (1.0 / k) * np.sin(2 * np.pi * 90.0 * k * t)
        for k in range(1, 7)
    )
    signal = 0.3 * signal / np.max(np.abs(signal))
    rows, _ = analyze_clip(signal)
    features = rows_to_feature_series(rows)
    assert "harmonic_score" in features
    assert "best_f0" in features
    assert "f0_delta" in features
    assert len(features["harmonic_score"]) == len(rows)
    swept = sweep_feature_series(features, delays=(1, 2), gains=(0.0, 0.5))
    assert swept
    assert all(0.0 <= row["structure_score"] <= 1.0 for row in swept)


def test_parameter_island_becomes_robust_consensus():
    rows = []
    for label, base in [
        ("drone", 0.85),
        ("drone_like_synthetic", 0.80),
        ("no_drone", 0.20),
        ("no_drone", 0.25),
    ]:
        for delay in (1, 2, 4):
            for gain in (0.0, 0.5, 1.0):
                rows.append(
                    {
                        "label": label,
                        "feature": "harmonic_score",
                        "delay": delay,
                        "gain": gain,
                        "polarity_rule": "fixed_positive",
                        "structure_score": base,
                    }
                )
    ranked = rank_parameter_rows(rows)
    assert ranked
    assert ranked[0]["robustness_flag"] == "robust"
    assert ranked[0]["consensus_flag"] == "consensus_strong"
    assert ranked[0]["auc"] == 1.0


def test_motif_aggregation_finds_strong_family_on_production_delay_grid():
    rankings = []
    # The production motif bucket logic needs enough D values for a family to
    # contain multiple rows. The previous 3-delay test created singleton
    # short/mid/long families and could never become motif_strong.
    for delay in (1, 2, 4, 8, 16):
        for gain in (0.0, 0.5, 1.0):
            rankings.append(
                {
                    "feature": "f0_delta",
                    "delay": delay,
                    "gain": gain,
                    "polarity_rule": "threshold_switch",
                    "consensus_score": 0.8,
                    "robustness_score": 0.75,
                    "consensus_flag": "consensus_strong",
                }
            )
    motifs = build_motifs(rankings)
    assert motifs
    assert any(row["motif_flag"] == "motif_strong" for row in motifs)
