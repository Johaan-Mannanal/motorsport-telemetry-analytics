# Data

This project does **not** ship any race data. All data is public Formula 1 timing and
telemetry pulled on demand via [FastF1](https://github.com/theOehrly/Fast-F1), which sources
from the official F1 live-timing service and the Ergast/Jolpica archive.

## How it works
- On first use of a given session, FastF1 downloads the data and stores it in a local cache
  directory (default `data/cache/`, configurable via `FASTF1_CACHE_DIR` in `.env`).
- The cache is **git-ignored** and regenerated automatically: nothing needs to be committed.
- Subsequent loads of the same session read from the cache and are fast/offline.

## What a session provides
- **Laps**: lap times, sector times, lap number, stint, compound, tyre life, track status.
- **Car telemetry**: speed, throttle, brake, gear (`nGear`), RPM, DRS, sampled along the lap
  with a `Distance` channel.
- **Position telemetry**: X/Y track coordinates (for the track-position map).
- **Weather**: air/track temperature, humidity, wind, rainfall.
- **Results**: finishing order, grid, points.

## Attribution & terms
Data © Formula 1 and providers, accessed via FastF1. This project is unofficial and not
affiliated with Formula 1. Use is for education and personal analysis; respect FastF1's and the
data providers' terms of use. FastF1 is licensed under the MIT License.
