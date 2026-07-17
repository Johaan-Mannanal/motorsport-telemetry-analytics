# Motorsport Telemetry Analytics

An interactive dashboard for analyzing Formula 1 telemetry and race performance. Pick a season,
race, session, and two drivers, and compare their laps: speed/throttle/brake/gear traces, delta
time, sector deltas, a track-position map, tyre strategy, weather, and a transparent
tyre-degradation / lap-time model. Built on public data via
[FastF1](https://github.com/theOehrly/Fast-F1).

![Speed trace: VER vs LEC, 2023 Italian GP](assets/speed_trace.png)
*Speed vs distance around Monza — Verstappen vs Leclerc, fastest race laps (real FastF1 data).*

> **Live demo:** *coming soon* (deployable free on Streamlit Community Cloud — see
> [Deploy](#deploy)). Until then, it runs locally in two commands.

## Why this exists
Take real time-series sensor data, turn it into analysis that explains *where* and *why* one
driver is faster, and present it so an engineer can make a decision. The techniques (aligning
telemetry on a common axis, filtering representative laps, estimating degradation) transfer
directly to any vehicle-telemetry or sensor problem.

## Features
- **Selectors:** season → race → session (Practice/Qualifying/Sprint/Race) → two drivers → laps.
- **Lap comparison:** lap time by lap number; fastest-lap gap.
- **Telemetry overlay (fastest or chosen laps):** delta time, speed, throttle, brake, gear —
  all on a shared distance axis.
- **Track & sectors:** X/Y track map coloured by speed; per-sector time deltas.
- **Tyres & weather:** per-driver stint/compound/tyre-age summary; session weather.
- **Model tab:** tyre-degradation estimate and a lap-time model vs. a naive baseline, with
  methodology and limitations shown in-app.

## Screenshots
| Delta time | Sector deltas | Track map (speed) |
|---|---|---|
| ![](assets/delta_time.png) | ![](assets/sector_deltas.png) | ![](assets/track_map.png) |

## Architecture
```
app.py                     Streamlit UI: selectors, tabs, wiring
src/
  data_loader.py           FastF1 session loading + local cache (typed wrapper)
  preprocessing.py         clean laps, filter green/representative laps, stint summary
  telemetry_analysis.py    delta time, channel overlays, sector deltas (pure pandas)
  modeling.py              tyre degradation + lap-time model vs baseline
  visualizations.py        Plotly figure builders (also used to export assets)
tests/                     network-free unit tests (preprocessing + modeling)
scripts/generate_assets.py re-generate README charts + verified results from a real session
results/                   verified metrics (model_metrics.json, tyre_degradation.csv)
```
Analysis is kept separate from plotting and from the UI, so every number is unit-tested and the
same figures power both the app and this README.

## Technologies
Python · FastF1 · pandas · NumPy · scikit-learn · Plotly · Streamlit · pytest
(kaleido is used only to export the static chart images.)

## Setup
```bash
git clone https://github.com/Johaan-Mannanal/motorsport-telemetry-analytics
cd motorsport-telemetry-analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional; sets the FastF1 cache dir

streamlit run app.py          # launch the dashboard
pytest -q                     # run tests (no network needed)
```
The first time you open a session, FastF1 downloads and caches it locally (a few seconds);
after that it loads from `data/cache/` (git-ignored).

## Data source
Public F1 timing and telemetry via **FastF1** (official live-timing + Ergast/Jolpica archive),
covering 2018–present. See [`data/README.md`](data/README.md). Unofficial; not affiliated with
Formula 1.

## Modeling approach
A deliberately **transparent** data-science component, not a strategy oracle:
1. **Tyre degradation** — per compound, fit lap time vs. tyre age on green laps; the slope is
   "seconds lost per lap of tyre life."
2. **Lap-time model** — linear regression on tyre age, lap number (a fuel-burn proxy), one-hot
   compound, and one-hot driver — compared against a **baseline** that predicts the mean lap time.
   Evaluated on a held-out 25% split (seed 42), reporting MAE and RMSE.

## Verified results
Reproduce with `python scripts/generate_assets.py` (writes [`results/model_metrics.json`](results/model_metrics.json)).
Reference session: **2023 Italian Grand Prix (Monza) — Race**, 878 green laps (658 train / 220 test).

| Model | MAE (s) | RMSE (s) |
|-------|---------|----------|
| Baseline (predict mean lap time) | 0.591 | 0.745 |
| **Lap-time model** (linear regression) | **0.293** | **0.407** |

The model roughly **halves the baseline error** (≈50% lower MAE). Tyre degradation at Monza (a
low-degradation circuit) came out to ~**0.025 s per lap of tyre life** for both HARD and MEDIUM —
with **low R² (0.04–0.07)**, which is honest: at Monza, tyre age alone explains little of the
lap-to-lap variation (fuel, traffic, and driver pace dominate). Higher-degradation circuits show
steeper, cleaner slopes.

## Limitations
- **Single-session** models; coefficients are correlational, not causal.
- The lap-time model includes **driver identity**, so it partly memorizes per-driver pace — it is
  **not** a generalizable cross-race predictor.
- Green-lap filtering is a heuristic; weather, track evolution, and fuel mass are only crudely
  proxied. A random lap split can leak within-stint correlation, so treat the gain as indicative.
- This is an analysis tool, **not** a replacement for a race engineer's judgment.

## Deploy
The app is Streamlit-ready. To publish a free live demo: push to GitHub, then create an app on
[Streamlit Community Cloud](https://streamlit.io/cloud) pointing at `app.py`. (I'll add the live
link here once deployed.)

## Future plans
- Cache warming / preselected sessions for an instant demo.
- Add one more analysis view (e.g., driver-consistency distribution).
- Optional: evaluate the lap-time model **across** races with driver identity removed, to test
  genuine generalization.

## License
MIT — see [LICENSE](LICENSE). FastF1 and F1 data belong to their respective owners.
