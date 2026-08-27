from pathlib import Path
import csv, subprocess, sys

def test_synthetic_manifest_builds(tmp_path):
    root = Path(__file__).resolve().parents[1]
    manifest = tmp_path/"manifest.csv"
    subprocess.run([
        sys.executable, str(root/"tools"/"build_benchmark.py"),
        "--profile","synthetic",
        "--synthetic-root",str(root/"example_data"/"synthetic"),
        "--manifest",str(manifest),
        "--bench-root",str(tmp_path/"bench"),
        "--raw-root",str(tmp_path/"raw"),
    ], cwd=root, check=True)
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    assert len(rows) >= 5
    assert any(r["category"]=="synthetic_harmonic" for r in rows)
    assert any(r["category"]=="white_noise" for r in rows)
