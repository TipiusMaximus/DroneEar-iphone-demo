from __future__ import annotations

from pathlib import Path
import argparse
import csv

from ddp_experiment.audio_adapter import wav_to_ddp_features
from ddp_experiment.ddp_core import sweep_feature_series, rank_parameter_rows
from ddp_experiment.motifs import build_motifs


CLIP_FIELDS = [
    "file", "label", "source", "category", "distance_m",
    "feature", "delay", "gain", "polarity_rule",
    "median_abs", "q90_abs", "sign_persistence", "smoothness",
    "structure_score",
]

RANKING_FIELDS = [
    "feature", "delay", "gain", "polarity_rule",
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


def run_manifest(manifest_path, output_dir):
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    manifest = list(csv.DictReader(manifest_path.open(encoding="utf-8")))

    all_rows = []
    skipped = []

    for index, item in enumerate(manifest, 1):
        path = Path(item["file"])
        print(f"[{index}/{len(manifest)}] {path}")
        if not path.exists():
            skipped.append(str(path))
            print("  [skip] file not found")
            continue

        feature_series, _ = wav_to_ddp_features(path, normalized=True)
        swept = sweep_feature_series(feature_series)
        for row in swept:
            row.update(
                {
                    "file": item["file"],
                    "label": item["label"],
                    "source": item["source"],
                    "category": item["category"],
                    "distance_m": item.get("distance_m", ""),
                }
            )
        all_rows.extend(swept)

    rankings = rank_parameter_rows(all_rows)
    motifs = build_motifs(rankings)

    _write_csv(output_dir / "ddp_clip_signatures.csv", all_rows, CLIP_FIELDS)
    _write_csv(output_dir / "ddp_parameter_rankings.csv", rankings, RANKING_FIELDS)
    _write_csv(output_dir / "ddp_motifs.csv", motifs, MOTIF_FIELDS)

    report = output_dir / "DDP_EXPERIMENT_REPORT.md"
    with report.open("w", encoding="utf-8") as handle:
        handle.write("# DroneEar × DDP experiment\n\n")
        handle.write(f"Processed manifest clips: **{len(manifest) - len(skipped)}** / {len(manifest)}\n\n")
        handle.write(f"DDP clip-signature rows: **{len(all_rows)}**\n\n")
        handle.write(f"Ranked parameter sets: **{len(rankings)}**\n\n")
        handle.write(f"Motif families: **{len(motifs)}**\n\n")
        if skipped:
            handle.write("## Skipped files\n\n")
            for path in skipped:
                handle.write(f"- `{path}`\n")
            handle.write("\n")

        handle.write("## Top parameter sets\n\n")
        handle.write("| feature | D | gain | rule | AUC | separation | robust | consensus | flag |\n")
        handle.write("|---|---:|---:|---|---:|---:|---:|---:|---|\n")
        for row in rankings[:20]:
            handle.write(
                f"| {row['feature']} | {row['delay']} | {row['gain']:.2f} | "
                f"{row['polarity_rule']} | {row['auc']:.3f} | "
                f"{row['separation_score']:.3f} | {row['robustness_score']:.3f} | "
                f"{row['consensus_score']:.3f} | {row['consensus_flag']} |\n"
            )

        handle.write("\n## Top motifs\n\n")
        handle.write("| motif | score | strong rows | flag |\n")
        handle.write("|---|---:|---:|---|\n")
        for row in motifs[:20]:
            handle.write(
                f"| {row['motif_family']} | {row['motif_score']:.3f} | "
                f"{row['strong_count']} | {row['motif_flag']} |\n"
            )

        handle.write("\n## Interpretation rule\n\n")
        handle.write(
            "A useful candidate should rank well **and** remain strong in neighboring "
            "delay/gain settings. A lone high AUC with fragile/weak consensus is treated "
            "as an outlier, not a discovery.\n\n"
        )
        handle.write(
            "This experiment is feature discovery. Scores are not calibrated probabilities "
            "and should not be copied to the iPhone runtime until they survive real drone "
            "and hard-negative benchmark data.\n"
        )

    print(f"[report] {report}")
    return {
        "clip_rows": all_rows,
        "rankings": rankings,
        "motifs": motifs,
        "skipped": skipped,
        "report": report,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/benchmark/manifest.csv")
    parser.add_argument("--output", default="outputs/ddp_experiment")
    args = parser.parse_args()
    run_manifest(args.manifest, args.output)


if __name__ == "__main__":
    main()
