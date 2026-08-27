# Benchmark Metrics

`results.csv` sisältää rivin per klippi.

## Tunnisteet

```text
file
label
source
category
distance_m
```

## Detector-metriikat

```text
frames
mean_score
p95_score
max_score
detected_fraction
max_state
median_best_f0
median_harmonic_consistency
median_harmonic_contrast_db
median_track_stability
```

## Mitä etsitään

Drone-positive:
- `DETECTED` on hyvä merkki;
- `CLEAR` on false negative -ehdokas.

No-drone:
- `CLEAR` on hyvä;
- `DETECTED` on erityisen kiinnostava false positive.

Älä katso vain scorea. Katso samalla:
- consistency;
- contrast;
- track stability;
- best f0.

Jos esimerkiksi moottori saa korkean arvon kaikissa näissä, tarvitsemme uuden erottelevan feature-tyypin emmekä vain eri thresholdia.
