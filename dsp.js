/* DroneEar v0.2a detector math. No DOM. Node and browser both load this. */
(function (root) {
  const EPS = 1e-12;

  function clip01(v) {
    return !isFinite(v) ? 0 : Math.min(1, Math.max(0, v));
  }

  function hann(n) {
    const w = new Float64Array(n);
    for (let i = 0; i < n; i++) w[i] = 0.5 * (1 - Math.cos((2 * Math.PI * i) / n));
    return w;
  }

  function fftRadix2(re, im) {
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) {
        let t = re[i]; re[i] = re[j]; re[j] = t;
        t = im[i]; im[i] = im[j]; im[j] = t;
      }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const ang = -2 * Math.PI / len;
      const wr = Math.cos(ang), wi = Math.sin(ang);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let j = 0; j < len / 2; j++) {
          const ur = re[i + j], ui = im[i + j];
          const vr = re[i + j + len / 2] * cr - im[i + j + len / 2] * ci;
          const vi = re[i + j + len / 2] * ci + im[i + j + len / 2] * cr;
          re[i + j] = ur + vr; im[i + j] = ui + vi;
          re[i + j + len / 2] = ur - vr; im[i + j + len / 2] = ui - vi;
          const ncr = cr * wr - ci * wi;
          ci = cr * wi + ci * wr;
          cr = ncr;
        }
      }
    }
  }

  function rfftMag(frame) {
    const n = frame.length;
    const re = new Float64Array(n), im = new Float64Array(n);
    for (let i = 0; i < n; i++) re[i] = frame[i];
    fftRadix2(re, im);
    const mag = new Float64Array(n / 2 + 1);
    for (let i = 0; i <= n / 2; i++) mag[i] = Math.hypot(re[i], im[i]);
    return mag;
  }

  function median(arr) {
    if (!arr.length) return 0;
    const s = arr.slice().sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : 0.5 * (s[m - 1] + s[m]);
  }

  function RingBuffer(size) {
    this.size = size;
    this.buf = new Float32Array(size);
    this.write = 0;
    this.filled = 0;
  }
  RingBuffer.prototype.push = function (samples) {
    for (let i = 0; i < samples.length; i++) {
      this.buf[this.write] = samples[i];
      this.write = (this.write + 1) % this.size;
      if (this.filled < this.size) this.filled++;
    }
    return this.filled >= this.size;
  };
  RingBuffer.prototype.snapshot = function () {
    const out = new Float64Array(this.size);
    const start = this.write;
    for (let i = 0; i < this.size; i++) out[i] = this.buf[(start + i) % this.size];
    return out;
  };
  RingBuffer.prototype.reset = function () {
    this.buf.fill(0);
    this.write = 0;
    this.filled = 0;
  };

  function bandStats(freqs, power, lo, hi) {
    let sum = 0, n = 0;
    for (let i = 0; i < power.length; i++) {
      if (freqs[i] >= lo && freqs[i] < hi) { sum += power[i]; n++; }
    }
    return { sum: sum, n: n, mean: n ? sum / n : 0 };
  }

  function regionMean(freqs, power, lo, hi) {
    return bandStats(freqs, power, lo, hi).mean;
  }

  function evaluateCandidate(freqs, power, f0, cfg, noiseFloor) {
    const nyquist = freqs[freqs.length - 1] || 0;
    let harmSum = 0, harmN = 0;
    let bgSum = 0, bgN = 0;
    let hits = 0, counted = 0;
    const targets = [];
    for (let k = 1; k <= cfg.nHarmonics; k++) {
      const target = k * f0;
      if (target >= nyquist - 1) break;
      counted++;
      const tol = Math.max(cfg.harmonicTolHz, cfg.harmonicTolFrac * target);
      const hMean = regionMean(freqs, power, target - tol, target + tol);
      const hStats = bandStats(freqs, power, target - tol, target + tol);
      harmSum += hStats.sum;
      harmN += hStats.n;
      const next = (k + 1) * f0;
      const gapLo = target + tol;
      const gapHi = Math.min(nyquist, next - Math.max(cfg.harmonicTolHz, cfg.harmonicTolFrac * next));
      if (gapHi > gapLo) {
        const g = bandStats(freqs, power, gapLo, gapHi);
        bgSum += g.sum;
        bgN += g.n;
      }
      targets.push(target);
    }
    const harmMean = harmN ? harmSum / harmN : 0;
    const bgMean = Math.max(bgN ? bgSum / bgN : 0, noiseFloor || 0);
    const contrastLin = harmMean / (bgMean + EPS);
    const contrastDb = 10 * Math.log10(contrastLin);
    const hitFloor = Math.max(bgMean * cfg.hitMargin, cfg.minHitPower);
    for (let k = 1; k <= counted; k++) {
      const target = k * f0;
      const tol = Math.max(cfg.harmonicTolHz, cfg.harmonicTolFrac * target);
      const hMean = regionMean(freqs, power, target - tol, target + tol);
      if (hMean > hitFloor) hits++;
    }
    const consistency = counted ? hits / counted : 0;
    const total = power.reduce((a, b) => a + b, 0) + EPS;
    const energyScore = clip01(harmSum / total);
    const contrast01 = clip01((contrastDb - 0) / 15) * clip01(consistency / 0.5);
    const harmonicScore = clip01(
      cfg.candW.energy * energyScore +
      cfg.candW.consistency * consistency +
      cfg.candW.contrast * contrast01
    );
    return {
      f0,
      harmonicHits: hits,
      harmonicCounted: counted,
      harmonicConsistency: consistency,
      harmonicContrast: contrast01,
      harmonicContrastDb: contrastDb,
      harmonicEnergy: harmSum,
      energyScore,
      harmonicScore,
      targets,
    };
  }

  // Octave / harmonic-collapse preference (mirrors Python reference_detector).
  // When best f0 is ~2x or ~3x a competitive lower candidate, prefer lower f0.
  const OCTAVE_DEFAULTS = {
    octaveScoreMargin: 0.05,
    octaveScoreRatio: 0.92,
    octaveRelTol: 0.04,
    octaveBinTol: 2.0,
    octaveMultiples: [2, 3],
    octaveApplyAboveHz: 200.0,
  };

  function preferLowerOctaveCandidate(scored, best, cfg, binHz) {
    if (!best || !scored.length) return best;
    const margin = cfg.octaveScoreMargin != null ? cfg.octaveScoreMargin : OCTAVE_DEFAULTS.octaveScoreMargin;
    const ratio = cfg.octaveScoreRatio != null ? cfg.octaveScoreRatio : OCTAVE_DEFAULTS.octaveScoreRatio;
    const relTol = cfg.octaveRelTol != null ? cfg.octaveRelTol : OCTAVE_DEFAULTS.octaveRelTol;
    const binTol = cfg.octaveBinTol != null ? cfg.octaveBinTol : OCTAVE_DEFAULTS.octaveBinTol;
    const multiples = cfg.octaveMultiples || OCTAVE_DEFAULTS.octaveMultiples;
    const applyAbove = cfg.octaveApplyAboveHz != null ? cfg.octaveApplyAboveHz : OCTAVE_DEFAULTS.octaveApplyAboveHz;
    const f0Min = cfg.f0 ? cfg.f0[0] : 60;
    let preferred = best;
    for (let guard = 0; guard < 3; guard++) {
      const bestScore = preferred.harmonicScore;
      const bestF0 = preferred.f0;
      if (!(bestF0 > 0) || !(bestScore > 0)) break;
      if (bestF0 <= applyAbove) break;
      let nxt = preferred;
      for (let mi = 0; mi < multiples.length; mi++) {
        const k = multiples[mi];
        const target = bestF0 / k;
        if (target < f0Min) continue;
        const tol = Math.max(relTol * target, binTol * binHz);
        for (let i = 0; i < scored.length; i++) {
          const cand = scored[i];
          if (Math.abs(cand.f0 - target) > tol) continue;
          const s = cand.harmonicScore;
          const closeEnough = s >= bestScore - margin || s >= ratio * bestScore;
          if (!closeEnough) continue;
          const competitiveStruct =
            cand.harmonicHits >= preferred.harmonicHits - 1 ||
            cand.harmonicConsistency >= preferred.harmonicConsistency - 0.17;
          if (!competitiveStruct && s < bestScore - 0.02) continue;
          if (cand.f0 < nxt.f0 - 1e-9) nxt = cand;
        }
      }
      if (nxt === preferred) break;
      preferred = nxt;
    }
    return preferred;
  }

  function searchLattice(freqs, power, cfg) {
    const lo = cfg.f0[0], hi = cfg.f0[1];
    const df = freqs[1] - freqs[0] || 1;
    const step = Math.max(df, cfg.f0StepHz || df);
    const above = [];
    for (let i = 0; i < power.length; i++) if (freqs[i] >= lo) above.push(power[i]);
    const noiseFloor = median(above);
    const scored = [];
    let best = null;
    for (let f0 = lo; f0 <= hi + 1e-9; f0 += step) {
      const cand = evaluateCandidate(freqs, power, f0, cfg, noiseFloor);
      scored.push(cand);
      if (!best || cand.harmonicScore > best.harmonicScore) best = cand;
    }
    if (best) best = preferLowerOctaveCandidate(scored, best, cfg, df);
    return best || {
      f0: 0, harmonicHits: 0, harmonicCounted: 0, harmonicConsistency: 0,
      harmonicContrast: 0, harmonicContrastDb: 0, harmonicEnergy: 0,
      energyScore: 0, harmonicScore: 0, targets: [],
    };
  }

  function F0Tracker(cfg) {
    this.cfg = cfg;
    this.items = [];
  }
  F0Tracker.prototype.reset = function () { this.items = []; };
  F0Tracker.prototype.update = function (now, f0, harmonicScore) {
    const keep = this.cfg.trackSeconds;
    if (harmonicScore < this.cfg.trackMinScore) {
      this.items = this.items.filter((it) => now - it.t <= keep);
      return this.stability();
    }
    this.items.push({ t: now, f0: f0, s: harmonicScore });
    this.items = this.items.filter((it) => now - it.t <= keep);
    return this.stability();
  };
  F0Tracker.prototype.stability = function () {
    const items = this.items;
    if (items.length < 4) return items.length ? 0.2 : 0;
    const f0s = items.map((it) => it.f0);
    const med = median(f0s);
    let mad = 0;
    for (const f of f0s) mad += Math.abs(f - med);
    mad /= f0s.length;
    const rel = mad / (med + 1);
    const spread = clip01(1 - rel / 0.25);
    let jumpPen = 0;
    for (let i = 1; i < items.length; i++) {
      const a = items[i - 1].f0, b = items[i].f0;
      const lim = Math.max(25, 0.2 * Math.max(a, b));
      if (Math.abs(b - a) > lim) jumpPen++;
    }
    const jumpScore = clip01(1 - jumpPen / Math.max(1, items.length - 1));
    return clip01(0.65 * spread + 0.35 * jumpScore);
  };

  function mechanicalBandScore(lowRatio, midRatio, highRatio) {
    const mech = clip01(lowRatio + midRatio);
    return clip01(mech * (1 - 0.65 * highRatio));
  }

  function scoreFrame(parts, cfg, rms) {
    if (rms < cfg.silenceRms) return 0;
    const w = cfg.scoreW;
    const raw =
      w.harmonic * parts.harmonicScore +
      w.contrast * parts.harmonicContrast +
      w.consistency * parts.harmonicConsistency +
      w.track * parts.trackStability +
      w.band * parts.bandScore;
    return clip01(raw);
  }

  const persistDefaults = function () {
    return { state: "CLEAR", sm: 0, init: false, high: 0, low: 0 };
  };

  function persistUpdate(persist, score, dt, cfg) {
    const sIn = clip01(score);
    dt = Math.max(0, dt);
    persist.sm = persist.init ? cfg.smooth * sIn + (1 - cfg.smooth) * persist.sm : sIn;
    persist.init = true;
    const s = persist.sm;
    if (persist.state === "CLEAR") {
      persist.low = 0;
      if (s >= cfg.possible) {
        persist.state = "POSSIBLE";
        persist.high = s >= cfg.detected ? persist.high + dt : 0;
      } else persist.high = 0;
    } else if (persist.state === "POSSIBLE") {
      if (s >= cfg.detected) {
        persist.high += dt; persist.low = 0;
        if (persist.high >= cfg.detectedS) { persist.state = "DETECTED"; persist.low = 0; }
      } else if (s >= cfg.possible) {
        persist.high = 0; persist.low = 0;
      } else {
        persist.high = 0; persist.state = "CLEAR"; persist.low = 0;
      }
    } else if (persist.state === "DETECTED") {
      if (s < cfg.clear) {
        persist.low += dt;
        if (persist.low >= cfg.clearS) { persist.state = "CLEAR"; persist.high = 0; persist.low = 0; }
      } else persist.low = 0;
    }
    return persist;
  }

  function analyzeFrame(samples, sr, cfg, win) {
    const n = cfg.fftSize;
    const frame = new Float64Array(n);
    for (let i = 0; i < n; i++) frame[i] = samples[i] * win[i];
    let rms = 0;
    for (let i = 0; i < samples.length; i++) rms += samples[i] * samples[i];
    rms = Math.sqrt(rms / Math.max(1, samples.length));
    const mag = rfftMag(frame);
    const power = new Float64Array(mag.length);
    const freqs = new Float64Array(mag.length);
    for (let i = 0; i < mag.length; i++) {
      freqs[i] = i * sr / n;
      power[i] = mag[i] * mag[i];
      if (freqs[i] < cfg.highpassHz) power[i] = 0;
    }
    const low = bandStats(freqs, power, cfg.bands.low[0], cfg.bands.low[1]);
    const mid = bandStats(freqs, power, cfg.bands.mid[0], cfg.bands.mid[1]);
    const high = bandStats(freqs, power, cfg.bands.high[0], cfg.bands.high[1]);
    const tot = low.sum + mid.sum + high.sum + EPS;
    const lattice = searchLattice(freqs, power, cfg);
    return {
      rms, mag, power, freqs,
      bandLowRatio: low.sum / tot,
      bandMidRatio: mid.sum / tot,
      bandHighRatio: high.sum / tot,
      bandLowMean: low.mean,
      bandMidMean: mid.mean,
      bandHighMean: high.mean,
      lattice,
      df: sr / n,
    };
  }

  const api = {
    EPS, clip01, hann, rfftMag, median, RingBuffer,
    bandStats, evaluateCandidate, preferLowerOctaveCandidate, searchLattice, F0Tracker,
    mechanicalBandScore, scoreFrame, persistDefaults, persistUpdate, analyzeFrame,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.DroneEarDSP = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
