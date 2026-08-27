import argparse, subprocess, sys

def run(cmd):
    print("\n>", " ".join(map(str,cmd)))
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["synthetic","small-real"], default="synthetic")
    ap.add_argument("--include-esc50", action="store_true")
    args = ap.parse_args()
    py = sys.executable

    run([py, "tools/generate_synthetic.py"])
    run([py, "-m", "pytest", "-q"])

    build = [py, "tools/build_benchmark.py", "--profile", args.profile]
    if args.include_esc50:
        build.append("--include-esc50")
    run(build)

    out = "outputs/synthetic" if args.profile=="synthetic" else "outputs/small_real"
    if args.include_esc50:
        out += "_esc50"
    run([py, "tools/run_benchmark.py", "--out", out])

    print("\nDONE")
    print(f"Open: {out}/summary.md")
    print(f"CSV:  {out}/results.csv")

if __name__ == "__main__":
    main()
