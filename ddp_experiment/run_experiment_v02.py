from __future__ import annotations

from pathlib import Path
import argparse
import csv

from ddp_experiment.audio_adapter import wav_to_ddp_features
from ddp_experiment.ddp_core_v02 import sweep_feature_series_v02, rank_parameter_rows_v02
from ddp_experiment.motifs import build_motifs


CLIP_FIELDS = [
    "file", "label", "source", "category", "distance_m",
    "feature", "source_feature", "target_feature", "ddp_mode",
    "delay", "delay_ms", "gain", "polarity_rule",
    "median_abs", "q90_abs", "sign_persistence", "smoothness", "structure_score",
]

RANKING_FIELDS = [
    "feature", "source_feature", "target_feature", "ddp_mode",
    "delay", "delay_ms", "gain", "polarity_rule",
    "positive_clips", "negative_clips", "positive_median", "negative_median",
    "auc", "separation_score", "neighbor_count", "neighbor_median_separation",
    "robustness_score", "robustness_flag", "repeat_good_neighbor_share",
    "consensus_score", "consensus_flag",
]

MOTIF_FIELDS = [
    "motif_family", "feature", "polarity_rule", "delay_bucket", "gain_bucket",
    "row_count", "strong_count", "median_consensus", "mean_consensus",
    "median_robustness", "motif_score", "motif_flag",
]


def _write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _filtered_manifest(manifest, *, exclude_synthetic=False):
    if not exclude_synthetic:
        return manifest
    return [
        row for row in manifest
        if row.get("source") != "synthetic"
        and row.get("label") != "drone_like_synthetic"
    ]


def run_manifest(manifest_path, output_dir, *, exclude_synthetic=False, normalized=True, cross_only=False):
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    manifest = _filtered_manifest(manifest, exclude_synthetic=exclude_synthetic)

    all_rows = []
    skipped = []
    hop_ms = 64.0  # verified from current reference DetectorConfig: 1024/16000 s

    for index, item in enumerate(manifest, 1):
        path = Path(item["file"])
        print(f"[{index}/{len(manifest)}] {path}")
        if not path.exists():
            skipped.append(str(path))
            print("  [skip] file not found")
            continue

        feature_series, _ = wav_to_ddp_features(path, normalized=normalized)
        swept = sweep_feature_series_v02(
            feature_series,
            include_same_feature=not cross_only,
        )
        if cross_only:
            swept = [row for row in swept if row.get("ddp_mode") == "cross_feature"]

        for row in swept:
            row.update({
                "file": item["file"],
                "label": item["label"],
                "source": item["source"],
                "category": item["category"],
                "distance_m": item.get("distance_m", ""),
                "delay_ms": float(row["delay"]) * hop_ms,
            })
        all_rows.extend(swept)

    rankings = rank_parameter_rows_v02(all_rows)
    for row in rankings:
        row["delay_ms"] = float(row["delay"]) * hop_ms
    motifs = build_motifs(rankings)

    _write_csv(output_dir / "ddp_v02_clip_signatures.csv", all_rows, CLIP_FIELDS)
    _write_csv(output_dir / "ddp_v02_parameter_rankings.csv", rankings, RANKING_FIELDS)
    _write_csv(output_dir / "ddp_v02_motifs.csv", motifs, MOTIF_FIELDS)

    report = output_dir / "DDP_V02_EXPERIMENT_REPORT.md"
    with report.open("w", encoding="utf-8") as handle:
        handle.write("# DroneEar × DDP v0.2 experiment\n\n")
        handle.write(f"Processed manifest clips: **{len(manifest) - len(skipped)}** / {len(manifest)}\n\n")
        handle.write(f"Normalized within clip: **{normalized}**\n\n")
        handle.write(f"Synthetic excluded: **{exclude_synthetic}**\n\n")
        handle.write(f"Cross-only mode: **{cross_only}**\n\n")
        handle.write(f"Signature rows: **{len(all_rows)}**\n\n")
        handle.write(f"Ranked parameter sets: **{len(rankings)}**\n\n")
        handle.write(f"Motif families: **{len(motifs)}**\n\n")

        handle.write("## Top parameter sets\n\n")
        handle.write("| mode | source | target | D | ms | gain | rule | AUC | separation | robust | consensus | flag |\n")
        handle.write("|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|\n")
        for row in rankings[:30]:
            handle.write(
                f"| {row.get('ddp_mode','')} | {row.get('source_feature','')} | {row.get('target_feature','')} | "
                f"{row['delay']} | {row['delay_ms']:.0f} | {row['gain']:.2f} | {row['polarity_rule']} | "
                f"{row['auc']:.3f} | {row['separation_score']:.3f} | {row['robustness_score']:.3f} | "
                f"{row['consensus_score']:.3f} | {row['consensus_flag']} |\n"
            )

        handle.write("\n## Cross-feature ablation rule\n\n")
        handle.write(
            "Every cross-feature pair includes **g=0**. If g>0 does not beat or behave more robustly "
            "than g=0 on held-out hard negatives, the target-feature gradient is not adding evidence.\n\n"
        )
        handle.write("## Distance interpretation\n\n")
        handle.write(
            "Distance-aware features include narrow band ratios, high/low frequency share, spectral flux, "
            "sideband ratio, envelope movement and modulation depth. Synthetic distance variants are stress "
            "tests only; they are not an atmospheric propagation model or an iPhone range calibration.\n\n"
        )
        handle.write("## Methodological guardrails\n\n")
        handle.write("- Use `--exclude-synthetic` for real-only ranking.\n")
        handle.write("- Treat adjacent clips from one source recording as dependent evidence.\n")
        handle.write("- Do not report in-sample AUC as field performance.\n")
        handle.write("- Prefer hard-negative evaluation with parameters chosen before evaluation.\n")
        handle.write("- Do not port a rule to Safari until it beats the base detector and g=0 ablation.\n")

    print(f"[report] {report}")
    return {"clip_rows": all_rows, "rankings": rankings, "motifs": motifs, "skipped": skipped, "report": report}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/benchmark/manifest.csv")
    parser.add_argument("--output", default="outputs/ddp_v02")
    parser.add_argument("--exclude-synthetic", action="store_true")
    parser.add_argument("--no-normalize", action="store_true")
    parser.add_argument("--cross-only", action="store_true")
    args = parser.parse_args()
    run_manifest(
        args.manifest,
        args.output,
        exclude_synthetic=args.exclude_synthetic,
        normalized=not args.no_normalize,
        cross_only=args.cross_only,
    )


if __name__ == "__main__":
    main()
