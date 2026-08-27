# Codex Prompt — Integrate Automated Benchmark into DroneEar

Repository:

```text
TipiusMaximus/DroneEar-iphone-demo
```

Goal:

Integrate this automated benchmark package into the existing repository and use it to evaluate the current v0.2a detector with minimal manual work.

Do not create a parallel repository.

## Preflight

1. inspect repository tree;
2. inspect current `index.html`;
3. inspect DSP/scoring code;
4. inspect README;
5. inspect git status;
6. preserve GitHub Pages behavior.

## Add tooling

Integrate:

```text
benchmark/
tools/
tests/
docs/
```

Add runtime paths to `.gitignore`:

```text
.venv/
data/raw/
data/benchmark/
outputs/
*.part
```

Do not ignore intentionally committed synthetic fixtures.

## First test — offline

Run:

```text
python tools/run_all.py --profile synthetic
```

Required:
1. 90 Hz harmonic lattice recovers f0 near 90 Hz.
2. Harmonic signal scores materially above single sine.
3. Harmonic signal scores materially above white noise.
4. Scores remain 0..1.
5. Harmonic signal reaches DETECTED.
6. Single sine does not reach DETECTED.
7. White noise does not reach DETECTED.

Do not change thresholds merely to force tests green unless there is a real bug.

## Small real benchmark

Run:

```text
python tools/run_all.py --profile small-real
```

This should automatically:
- download 1/10/30 m drone recordings;
- download noise floor;
- verify MD5;
- convert to mono 16 kHz;
- create deterministic 5 s clips;
- run detector;
- write CSV and Markdown summary.

Do not peak-normalize individual clips.

## Browser parity

The Python detector is a reference implementation, not proof that browser JS is identical.

Compare:
- FFT size;
- hop;
- f0 search;
- harmonic tolerance;
- harmonic hit threshold;
- contrast;
- score weights;
- persistence.

Document drift.

If practical, move browser detector math into a DOM-independent JS module used by both the page and JS tests, while keeping static GitHub Pages deployment.

## Optional ESC-50

Only after small-real works:

```text
python tools/run_all.py --profile small-real --include-esc50
```

Do not download ESC-50 during the first pass.

## DDL

Do not download 12.6 GB DDL during the first pass.

Keep it documented for the next stage.

## Report

For near/mid/far/noise-floor report:
- p95;
- max score;
- state;
- f0;
- harmonic consistency;
- harmonic contrast;
- track stability.

If ESC-50 is run, list every negative clip that reaches DETECTED.

## No overclaiming

Do not call score a probability.

Do not infer reliable iPhone detection range from research recordings alone.

## Definition of done

Continue until:
- offline tests pass;
- small-real downloader is wired;
- manifest is generated;
- CSV/summary generation works;
- docs are updated;
- GitHub Pages still works.

Final response:
1. files changed;
2. exact tests/results;
3. real benchmark results if networking allowed;
4. browser/reference drift;
5. exact Windows command;
6. next smallest detector change;
7. commit recommendation.
