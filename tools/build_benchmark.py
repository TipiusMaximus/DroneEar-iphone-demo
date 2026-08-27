from pathlib import Path
import argparse, csv, hashlib, io, math, shutil, urllib.request, zipfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ZENODO_SMALL = [
    ("DroneNoise1meter.WAV",
     "https://zenodo.org/records/7329733/files/DroneNoise1meter.WAV?download=1",
     "9ef4719065f1a5fcb973d4ee604204e2", "drone", "1", "drone_noise"),
    ("DroneNoise10meter.wav",
     "https://zenodo.org/records/7329733/files/DroneNoise10meter.wav?download=1",
     "837201f716beb629de2d8fa7603a1788", "drone", "10", "drone_noise"),
    ("DroneNoise30meter.wav",
     "https://zenodo.org/records/7329733/files/DroneNoise30meter.wav?download=1",
     "12a9bbffa61a64603d022c46a7b77c37", "drone", "30", "drone_noise"),
    ("Noisefloor.wav",
     "https://zenodo.org/records/7329733/files/Noisefloor.wav?download=1",
     "0fb217d72252ff604a24495e163ac9d7", "no_drone", "", "noise_floor"),
]

ESC50_URL = "https://github.com/karolpiczak/ESC-50/archive/master.zip"
ESC50_CATEGORIES = [
    "helicopter", "engine", "chainsaw", "vacuum_cleaner",
    "washing_machine", "airplane", "wind", "insects"
]

def md5(path):
    h = hashlib.md5()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def download(url, dest, expected_md5=None):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (expected_md5 is None or md5(dest) == expected_md5):
        print(f"[skip] {dest.name}")
        return
    if dest.exists():
        dest.unlink()

    print(f"[download] {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "DroneEarBenchmark/0.1"})
    with urllib.request.urlopen(req) as r, tmp.open("wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1024*1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done/1024/1024:.1f}/{total/1024/1024:.1f} MB", end="")
        if total:
            print()
    tmp.replace(dest)

    if expected_md5 and md5(dest) != expected_md5:
        raise RuntimeError(f"MD5 mismatch for {dest}")

def pcm_to_float(x):
    if np.issubdtype(x.dtype, np.floating):
        return x.astype(np.float64)
    if x.dtype == np.uint8:
        return (x.astype(np.float64)-128.0)/128.0
    info = np.iinfo(x.dtype)
    return x.astype(np.float64) / float(max(abs(info.min), abs(info.max)))

def normalize_wav(src, out_dir, meta, target_sr=16000, clip_s=5.0, max_clips=4):
    sr, x = wavfile.read(str(src))
    x = pcm_to_float(x)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if sr != target_sr:
        g = math.gcd(int(sr), int(target_sr))
        x = resample_poly(x, target_sr//g, sr//g)

    clip_n = int(target_sr*clip_s)
    if len(x) < target_sr:
        return []

    rows = []
    for idx, start in enumerate(range(0, len(x), clip_n)):
        if idx >= max_clips:
            break
        clip = x[start:start+clip_n]
        if len(clip) < clip_n:
            if len(clip) < target_sr:
                break
            clip = np.pad(clip, (0, clip_n-len(clip)))

        clip = np.clip(clip, -0.999, 0.999)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{Path(src).stem}__{idx:02d}.wav"
        wavfile.write(out_path, target_sr, (clip*32767).astype(np.int16))

        row = dict(meta)
        row["file"] = str(out_path.as_posix())
        row["clip_index"] = idx
        rows.append(row)
    return rows

def add_synthetic(synth_root):
    mapping = {
        "harmonic_90.wav": ("drone_like_synthetic", "synthetic_harmonic"),
        "harmonic_sweep_80_110.wav": ("drone_like_synthetic", "synthetic_harmonic_sweep"),
        "single_sine_90.wav": ("no_drone", "single_sine"),
        "white_noise.wav": ("no_drone", "white_noise"),
        "am_noise.wav": ("no_drone", "am_noise"),
    }
    rows = []
    for name, (label, category) in mapping.items():
        p = Path(synth_root)/name
        if p.exists():
            rows.append({
                "file": str(p.as_posix()), "label": label, "source": "synthetic",
                "category": category, "distance_m": "", "clip_index": 0,
                "notes": "Generated control; not real drone audio."
            })
    return rows

def add_small_real(raw_root, bench_root):
    rows = []
    for name, url, checksum, label, distance, category in ZENODO_SMALL:
        raw = Path(raw_root)/"zenodo_7329733"/name
        download(url, raw, checksum)
        rows += normalize_wav(
            raw,
            Path(bench_root)/"zenodo_7329733",
            {
                "label": label, "source": "zenodo_7329733", "category": category,
                "distance_m": distance,
                "notes": "Research recording; not iPhone range calibration."
            },
        )
    return rows

def extract_esc50_subset(zip_path, raw_root, max_per_category=5):
    out = Path(raw_root)/"esc50_selected"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        meta_name = next(n for n in names if n.endswith("/meta/esc50.csv"))
        records = list(csv.DictReader(io.StringIO(z.read(meta_name).decode("utf-8"))))
        counts = {c:0 for c in ESC50_CATEGORIES}
        chosen = []
        for row in records:
            cat = row["category"]
            if cat in counts and counts[cat] < max_per_category:
                chosen.append(row)
                counts[cat] += 1
        for row in chosen:
            member = next(n for n in names if n.endswith("/audio/"+row["filename"]))
            dest = out/row["filename"]
            if not dest.exists():
                with z.open(member) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    return chosen, out

def add_esc50(raw_root, bench_root):
    zip_path = Path(raw_root)/"ESC-50-master.zip"
    download(ESC50_URL, zip_path)
    chosen, extracted = extract_esc50_subset(zip_path, raw_root)
    rows = []
    for row in chosen:
        rows += normalize_wav(
            extracted/row["filename"],
            Path(bench_root)/"esc50",
            {
                "label":"no_drone", "source":"ESC-50", "category":row["category"],
                "distance_m":"",
                "notes":"ESC-50 negative class; CC BY-NC dataset, see source license."
            },
            max_clips=1,
        )
    return rows

def write_manifest(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file","label","source","category","distance_m","clip_index","notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k:row.get(k,"") for k in fields})
    print(f"[manifest] {path} ({len(rows)} clips)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["synthetic","small-real"], default="synthetic")
    ap.add_argument("--include-esc50", action="store_true")
    ap.add_argument("--raw-root", default="data/raw")
    ap.add_argument("--bench-root", default="data/benchmark")
    ap.add_argument("--synthetic-root", default="example_data/synthetic")
    ap.add_argument("--manifest", default="data/benchmark/manifest.csv")
    args = ap.parse_args()

    rows = add_synthetic(args.synthetic_root)
    if args.profile == "small-real":
        rows += add_small_real(args.raw_root, args.bench_root)
    if args.include_esc50:
        print("[warning] ESC-50 download is about 600 MB")
        rows += add_esc50(args.raw_root, args.bench_root)
    write_manifest(rows, args.manifest)

if __name__ == "__main__":
    main()
