# DroneEar v0.2a — Detection Upgrade Specification

**Status:** Planned  
**Scope:** Improve the existing browser/iPhone demo detector without introducing ML.  
**Primary goal:** Make the current DSP detector materially more reliable and diagnosable before collecting training data or adding a learned model.

---

## 1. Why v0.2a exists

The current demo already has:

- microphone input;
- FFT-based analysis;
- harmonic feature extraction;
- a heuristic `drone_score`;
- `CLEAR / POSSIBLE / DETECTED` persistence logic;
- live visualization.

The main weakness is not the overall architecture. The main weakness is that the detector currently works from short analysis frames and combines several broad heuristics without enough temporal and spectral structure.

V0.2A_FULL_CONTENT_PLACEHOLDER