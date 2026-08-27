const D = require("./dsp.js");
const assert = (c, m) => { if (!c) { throw new Error(m); } };

const CFG = {
  fftSize: 4096,
  highpassHz: 60,
  possible: 0.55,
  detected: 0.72,
  detectedS: 2.0,
  clear: 0.45,
  clearS: 3.0,
  smooth: 0.35,
  nHarmonics: 6,
  f0: [60, 400],
  f0StepHz: 0,
  harmonicTolHz: 8,
  harmonicTolFrac: 0.04,
  hitMargin: 2.5,
  minHitPower: 1e-18,
  silenceRms: 8e-4,
  trackSeconds: 1.5,
  trackMinScore: 0.22,
  bands: { low: [60, 250], mid: [250, 2000], high: [2000, 8000] },
  candW: { energy: 0.35, consistency: 0.40, contrast: 0.25 },
  scoreW: { harmonic: 0.40, contrast: 0.20, consistency: 0.15, track: 0.15, band: 0.10 },
};

const SR = 16000;
const N = CFG.fftSize;
const WIN = D.hann(N);

function tone(sr, n, freqs, amps) {
  const x = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let v = 0;
    for (let k = 0; k < freqs.length; k++) v += (amps[k] || 1) * Math.sin(2 * Math.PI * freqs[k] * t);
    x[i] = v;
  }
  let s = 0;
  for (let i = 0; i < n; i++) s += x[i] * x[i];
  const rms = Math.sqrt(s / n) || 1;
  for (let i = 0; i < n; i++) x[i] *= 0.2 / rms;
  return x;
}

function scoreOf(samples) {
  const spec = D.analyzeFrame(samples, SR, CFG, WIN);
  const L = spec.lattice;
  const band = D.mechanicalBandScore(spec.bandLowRatio, spec.bandMidRatio, spec.bandHighRatio);
  const raw = D.scoreFrame({
    harmonicScore: L.harmonicScore,
    harmonicContrast: L.harmonicContrast,
    harmonicConsistency: L.harmonicConsistency,
    trackStability: 0.8,
    bandScore: band,
  }, CFG, spec.rms);
  return { spec, L, raw };
}

const harmFreqs = [90, 180, 270, 360, 450, 540];
const harm = tone(SR, N, harmFreqs, [1, 0.7, 0.5, 0.4, 0.3, 0.25]);
const h = scoreOf(harm);
assert(Math.abs(h.L.f0 - 90) < 8, "bestF0 should be near 90, got " + h.L.f0);
assert(h.L.harmonicConsistency >= 0.66, "harmonic consistency too low: " + h.L.harmonicConsistency);
assert(h.raw >= 0 && h.raw <= 1, "score not 0..1: " + h.raw);
assert(h.raw > 0.4, "harmonic stack should score decently, got " + h.raw);

const sine = tone(SR, N, [90], [1]);
const s = scoreOf(sine);
assert(s.L.harmonicConsistency < h.L.harmonicConsistency, "single sine should be less consistent than stack");
assert(s.raw < h.raw, "single sine should score lower than stack");

const silent = new Float64Array(N);
const z = scoreOf(silent);
assert(z.raw === 0, "silence should gate to 0, got " + z.raw);

const persist = D.persistDefaults();
D.persistUpdate(persist, 0.1, 0.1, CFG);
assert(persist.state === "CLEAR", "low score stays CLEAR");
for (let i = 0; i < 20; i++) D.persistUpdate(persist, 0.6, 0.1, CFG);
assert(persist.state === "POSSIBLE", "0.6 should become POSSIBLE, got " + persist.state + " sm=" + persist.sm);
for (let i = 0; i < 25; i++) D.persistUpdate(persist, 0.8, 0.1, CFG);
assert(persist.state === "DETECTED", "high score for 2s should DETECTED, got " + persist.state);

const ring = new D.RingBuffer(N);
assert(!ring.push(new Float32Array(1024)), "not full after 1024");
assert(!ring.push(new Float32Array(1024)), "not full after 2048");
assert(!ring.push(new Float32Array(1024)), "not full after 3072");
assert(ring.push(new Float32Array(1024)), "full after 4096");
const snap = ring.snapshot();
assert(snap.length === 4096, "snapshot is 4096");

const tr = new D.F0Tracker(CFG);
let st = 0;
for (let t = 0; t < 1.2; t += 0.064) st = tr.update(t, 86 + t * 4, 0.7);
assert(st > 0.5, "slow drift should stay stable, got " + st);
const tr2 = new D.F0Tracker(CFG);
const jumps = [86, 212, 74, 355, 91];
jumps.forEach((f, i) => tr2.update(i * 0.1, f, 0.7));
assert(tr2.stability() < st, "random jumps should be less stable");

console.log("ok", {
  bestF0: h.L.f0,
  hits: h.L.harmonicHits + "/" + h.L.harmonicCounted,
  consH: h.L.harmonicConsistency.toFixed(2),
  consSine: s.L.harmonicConsistency.toFixed(2),
  scoreH: h.raw.toFixed(2),
  scoreSine: s.raw.toFixed(2),
  driftStab: st.toFixed(2),
  jumpStab: tr2.stability().toFixed(2),
});
