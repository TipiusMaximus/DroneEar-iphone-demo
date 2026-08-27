# Benchmark Plan

## Tavoite

Tehdään toistettava testi, jossa jokainen detector-versio voidaan ajaa samalla aineistolla.

## Vaihe 0 — offline sanity check

Generoi:

- `harmonic_90.wav`
- `harmonic_sweep_80_110.wav`
- `single_sine_90.wav`
- `white_noise.wav`
- `am_noise.wav`

Odotus:

```text
harmonic_90:
  best f0 ≈ 90 Hz
  korkea harmonic consistency
  korkea score
  DETECTED

single_sine_90:
  best f0 voi olla ≈ 90 Hz
  mutta harmonisia osumia on vähän
  ei DETECTED

white_noise:
  matala harmonic score
  CLEAR
```

Tämä testaa algoritmin rakennetta, ei oikean dronen tunnistustarkkuutta.

## Vaihe 1 — pieni oikea benchmark

Ladataan automaattisesti:

```text
DroneNoise1meter.WAV
DroneNoise10meter.wav
DroneNoise30meter.wav
Noisefloor.wav
```

Jokaisesta tehdään enintään muutama 5 s klippi.

Ääntä ei peak-normalisoida klippikohtaisesti.

## Vaihe 2 — vaikeat negatiiviset

Valinnainen ESC-50:

```text
helicopter
engine
chainsaw
vacuum_cleaner
washing_machine
airplane
wind
insects
```

Tavoite on löytää se, mikä huijaa heuristiikkaa.

## Vaihe 3 — DDL

Vasta myöhemmin:

```text
12.6 GB real data
DJI Mini 2
DJI Phantom 4 Pro
no-drone
bearing
range 1 m increments
altitude
```

Tällä voidaan myöhemmin laskea score/detection rate etäisyyden funktiona.

## Kehitysrytmi

```text
run benchmark
→ save results
→ compare
→ muuta yksi detector-asia
→ run benchmark uudelleen
```
