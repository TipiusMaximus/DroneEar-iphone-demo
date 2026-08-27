from pathlib import Path
import argparse, csv, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.reference_detector import analyze_wav, DetectorConfig

FIELDS = [
    "file","label","source","category","distance_m","frames","mean_score",
    "p95_score","max_score","detected_fraction","max_state","median_best_f0",
    "median_harmonic_consistency","median_harmonic_contrast_db",
    "median_track_stability"
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/benchmark/manifest.csv")
    ap.add_argument("--out", default="outputs/latest")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    cfg = DetectorConfig()
    results = []

    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['file']}")
        _, summary = analyze_wav(row["file"], cfg)
        results.append({
            "file":row["file"], "label":row["label"], "source":row["source"],
            "category":row["category"], "distance_m":row["distance_m"], **summary
        })

    with (out/"results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in results:
            w.writerow({k:r.get(k,"") for k in FIELDS})

    false_pos = [r for r in results if r["label"]=="no_drone" and r["max_state"]=="DETECTED"]
    missed = [r for r in results if r["label"]=="drone" and r["max_state"]!="DETECTED"]

    with (out/"summary.md").open("w", encoding="utf-8") as f:
        f.write("# DroneEar benchmark summary\n\n")
        f.write(f"Clips: **{len(results)}**\n\n")
        f.write(f"False-positive DETECTED negatives: **{len(false_pos)}**\n\n")
        f.write(f"Real drone clips not DETECTED: **{len(missed)}**\n\n")
        f.write("| category | distance | label | p95 | max | state | f0 | consistency | contrast dB | track |\n")
        f.write("|---|---:|---|---:|---:|---|---:|---:|---:|---:|\n")
        for r in results:
            f.write(
                f"| {r['category']} | {r['distance_m']} | {r['label']} | "
                f"{r['p95_score']:.3f} | {r['max_score']:.3f} | {r['max_state']} | "
                f"{r['median_best_f0']:.1f} | {r['median_harmonic_consistency']:.2f} | "
                f"{r['median_harmonic_contrast_db']:.1f} | {r['median_track_stability']:.2f} |\n"
            )
        if false_pos:
            f.write("\n## False positives\n\n")
            for r in false_pos:
                f.write(f"- `{r['file']}` — {r['category']}, p95={r['p95_score']:.3f}\n")
        if missed:
            f.write("\n## Missed real drone clips\n\n")
            for r in missed:
                f.write(f"- `{r['file']}` — {r['distance_m']} m, p95={r['p95_score']:.3f}\n")

    print(f"[results] {out/'results.csv'}")
    print(f"[summary] {out/'summary.md'}")

if __name__ == "__main__":
    main()
