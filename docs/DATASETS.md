# Dataset Sources

## Zenodo 7329733 — oletuksen oikea testi

https://zenodo.org/records/7329733

Automaation käyttämät tiedostot:

```text
DroneNoise1meter.WAV
DroneNoise10meter.wav
DroneNoise30meter.wav
Noisefloor.wav
```

Suorat URL:t:

```text
https://zenodo.org/records/7329733/files/DroneNoise1meter.WAV?download=1
https://zenodo.org/records/7329733/files/DroneNoise10meter.wav?download=1
https://zenodo.org/records/7329733/files/DroneNoise30meter.wav?download=1
https://zenodo.org/records/7329733/files/Noisefloor.wav?download=1
```

MD5:

```text
DroneNoise1meter.WAV   9ef4719065f1a5fcb973d4ee604204e2
DroneNoise10meter.wav  837201f716beb629de2d8fa7603a1788
DroneNoise30meter.wav  12a9bbffa61a64603d022c46a7b77c37
Noisefloor.wav         0fb217d72252ff604a24495e163ac9d7
```

Caveat: tutkimusasetelman tallenne ei vastaa iPhone-mikrofonia, joten tästä ei päätellä iPhonen kantamaa.

## Zenodo 13754746 — valinnainen 10/50 m auralisaatio

https://zenodo.org/records/13754746

Sisältää mm.:
- 10 m / 50 m
- flyby
- takeoff
- landing
- small / large drone
- background variants

Ensimmäinen automaatio ei pura tätä, koska aineisto on 7z+MP3 ja se toisi ylimääräisiä decoder-riippuvuuksia.

## ESC-50 — valinnaiset negatiiviset

https://github.com/karolpiczak/ESC-50

Download:

https://github.com/karolpiczak/ESC-50/archive/master.zip

Koko noin 600 MB. Projektin README ilmoittaa lisenssiksi CC BY-NC.

Valitut luokat:

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

## DDL — iso myöhempi aineisto

https://zenodo.org/records/6459183

```text
MLSP_2022_Real_Data.zip
≈ 12.6 GB
```

URL:

```text
https://zenodo.org/records/6459183/files/MLSP_2022_Real_Data.zip?download=1
```

Datasetin filename-metadata sisältää julkaisun mukaan muun muassa:
- sample class;
- bearing;
- range 1 m tarkkuudella;
- altitude;
- real/synthetic marker.

Luokat:

```text
MINI = DJI Mini2
PRO4 = DJI Phantom Pro 4
XXXX = no drone
```

## Redistribution

Älä committoi ladattua kolmannen osapuolen raakadataa DroneEar-repoon.

Pidä runtime-data `.gitignore`:ssa ja committoi vain:
- skriptit;
- lähde-URL:t;
- checksummat;
- omat synteettiset fixturet;
- pienet tulosraportit.

Tarkista alkuperäisen datasetin lisenssi ennen raakafailien uudelleenjakelua.
