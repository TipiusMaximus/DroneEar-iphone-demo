# DroneEar v0.2a — Detection Upgrade Specification

**Status:** Implemented on the iPhone Safari demo.  
**Scope:** Improve the existing browser/iPhone demo detector without introducing ML.  
**Primary goal:** Make the current DSP detector materially more reliable and diagnosable before collecting training data or adding a learned model.

---

See the remainder of this specification in the same-named file in the private planning repo once copied, or in the original v0.2a zip. The implemented demo matches this spec:

- 4096-sample rolling FFT (no zero-padding as history)
- power spectrum for scoring
- ignore bins below 60 Hz (no per-frame IIR high-pass)
- harmonic-lattice search 60–400 Hz, up to 6 harmonics
- temporal f0 tracking (~1.5 s)
- explainable weighted score, not a probability
- CLEAR / POSSIBLE / DETECTED persistence (v0.1 thresholds)
- debug panel + lattice markers
- no raw audio recording, no ML, no labeling buttons

Full numbered sections 1–25 are in `Drone_listener_mvp_demo` `docs/DRONEEAR_V0.2A_SPEC.md` after that copy lands.
