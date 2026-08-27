# DroneEar v0.2a — Field Test Log Template

Use one section per test.

---

## Test ID

```text
DATE-TIME:
PHONE:
BROWSER:
LOCATION:
ENVIRONMENT:
WIND:
SOURCE:
DISTANCE:
```

### Detector readings

```text
BEST F0:
HARMONIC HITS:
HARMONIC CONSISTENCY:
HARMONIC CONTRAST:
HARMONIC SCORE:
TRACK STABILITY:
PEAK RAW SCORE:
PEAK SMOOTHED SCORE:
MAX STATE:
```

### Result

```text
EXPECTED:
OBSERVED:

TRUE POSITIVE:
TRUE NEGATIVE:
FALSE POSITIVE:
FALSE NEGATIVE:
```

### Notes

```text
What did it sound like?
Was the phone stationary?
Was the source moving?
Did f0 move smoothly?
What seemed to raise the score?
```

---

## Suggested first test set

Run at least:

```text
quiet room
speech
single sine
synthetic harmonic signal
music
fan
vacuum cleaner
drill
car
motorcycle
outdoor wind
real drone hover
real drone approach
real drone depart
```

Do not tune the detector after every single test.

Collect a batch first, then compare patterns.
