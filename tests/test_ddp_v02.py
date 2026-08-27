import numpy as np

from benchmark.reference_detector import DetectorConfig, analyze_clip
from ddp_experiment.ddp_core import compute_ddp_score
from ddp_experiment.ddp_core_v02 import compute_cross_ddp_score, rank_parameter_rows_v02
from ddp_experiment.distance_simulation import simulate_distance
from ddp_experiment.spectral_features import spectral_feature_rows


def test_research_frequency_search_is_broadened():
    cfg = DetectorConfig()
    assert cfg.f0_min == 40.0
    assert cfg.f0_max == 800.0


def test_cross_ddp_gain_zero_is_delayed_source_ablation():
    source = np.asarray([0.0, 1.0, 3.0, 6.0, 10.0])
    target = np.asarray([10.0, 5.0, 9.0, 2.0, 7.0])
    same = compute_ddp_score(
        source, delay=1, gain=0.0,
        polarity_rule="fixed_positive", threshold=0.0,
    )
    cross = compute_cross_ddp_score(
        source, target, delay=1, gain=0.0,
        polarity_rule="fixed_positive", threshold=0.0,
    )
    assert np.allclose(cross, same)


def test_cross_ddp_gain_can_add_target_gradient_information():
    source = np.asarray([0.0, 1.0, 3.0, 6.0, 10.0])
    target = np.asarray([0.0, 2.0, -2.0, 4.0, -4.0])
    zero = compute_cross_ddp_score(source, target, delay=1, gain=0.0, polarity_rule="fixed_positive")
    active = compute_cross_ddp_score(source, target, delay=1, gain=1.0, polarity_rule="fixed_positive")
    assert not np.allclose(active, zero)


def test_v02_isolated_parameter_is_not_auto_robust():
    rows = [
        {"label":"drone", "feature":"x", "source_feature":"x", "target_feature":"x", "ddp_mode":"same_feature", "delay":1, "gain":0.0, "polarity_rule":"fixed_positive", "structure_score":0.9},
        {"label":"no_drone", "feature":"x", "source_feature":"x", "target_feature":"x", "ddp_mode":"same_feature", "delay":1, "gain":0.0, "polarity_rule":"fixed_positive", "structure_score":0.1},
    ]
    ranked = rank_parameter_rows_v02(rows)
    assert len(ranked) == 1
    assert ranked[0]["auc"] == 1.0
    assert ranked[0]["neighbor_count"] == 0
    assert ranked[0]["robustness_flag"] == "isolated"
    assert ranked[0]["consensus_flag"] == "consensus_weak"


def test_distance_degradation_reduces_level_and_high_frequency_share():
    cfg = DetectorConfig()
    sr = cfg.sample_rate
    t = np.arange(6 * sr) / sr
    source = 0.18 * np.sin(2 * np.pi * 180.0 * t) + 0.12 * np.sin(2 * np.pi * 5000.0 * t)
    far = simulate_distance(
        source, sr,
        attenuation_db=24.0,
        lowpass_hz=1800.0,
        noise_level=0.0,
        comb_gain=0.0,
        slow_fade_depth=0.0,
    )

    near_rows, _ = analyze_clip(source, cfg)
    far_rows, _ = analyze_clip(far, cfg)
    near_spec = spectral_feature_rows(source, near_rows, cfg)
    far_spec = spectral_feature_rows(far, far_rows, cfg)

    near_level = np.median([r["amplitude_envelope"] for r in near_spec])
    far_level = np.median([r["amplitude_envelope"] for r in far_spec])
    near_high = np.median([r["high_frequency_share"] for r in near_spec])
    far_high = np.median([r["high_frequency_share"] for r in far_spec])

    assert far_level < near_level
    assert far_high < near_high


def test_spectral_feature_rows_expose_distance_and_modulation_features():
    cfg = DetectorConfig()
    sr = cfg.sample_rate
    t = np.arange(2 * sr) / sr
    x = (0.2 + 0.08 * np.sin(2 * np.pi * 4.0 * t)) * np.sin(2 * np.pi * 140.0 * t)
    detector_rows, _ = analyze_clip(x, cfg)
    spectral = spectral_feature_rows(x, detector_rows, cfg)
    assert spectral
    required = {
        "sideband_ratio", "modulation_depth", "spectral_flux",
        "low_frequency_share", "high_frequency_share",
        "band_40_120_ratio", "band_120_250_ratio", "band_4000_8000_ratio",
    }
    assert required.issubset(spectral[0])
