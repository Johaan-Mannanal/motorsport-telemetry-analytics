#!/usr/bin/env python3
"""Generate README assets and verified results from a real F1 session.

Exports the actual dashboard figures (Plotly -> PNG) and writes verified model metrics.
Run from the repo root:  python scripts/generate_assets.py [--year 2023 --event Monza]
Requires network on first run (FastF1 downloads + caches the session).
"""
from __future__ import annotations

import argparse
import json
import logging
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)

import pandas as pd

from src import data_loader as dl
from src import modeling as mdl
from src import preprocessing as pp
from src import telemetry_analysis as ta
from src import visualizations as viz

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets"
RESULTS = REPO / "results"


def main(year: int, event: str, drv_a: str, drv_b: str) -> None:
    ASSETS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    session = dl.load_session(year, event, "R")
    laps = session.laps
    tag = f"{event}{year}".replace(" ", "")

    la, lb = pp.clean_laps(laps.pick_drivers(drv_a)), pp.clean_laps(laps.pick_drivers(drv_b))
    fa, fb = laps.pick_drivers(drv_a).pick_fastest(), laps.pick_drivers(drv_b).pick_fastest()
    tel_a, tel_b = fa.get_car_data().add_distance(), fb.get_car_data().add_distance()

    # Figures (the same ones the dashboard renders)
    figs = {
        "laptime_comparison": viz.laptime_comparison(la, lb, drv_a, drv_b),
        "delta_time": viz.delta_time_trace(ta.delta_time(tel_a, tel_b), drv_a, drv_b),
        "speed_trace": viz.channel_trace(ta.channel_comparison(tel_a, tel_b, "Speed"), "Speed", drv_a, drv_b),
        "track_map": viz.track_position_map(fa.get_telemetry(), fa.get_telemetry().get("Speed"),
                                            f"{drv_a} fastest lap — speed"),
        "sector_deltas": viz.sector_delta_bar(ta.sector_deltas(fa, fb), drv_a, drv_b),
    }

    res = mdl.evaluate_laptime_model(laps).to_dict()
    if res["degradation"]:
        figs["degradation"] = viz.degradation_bar(res["degradation"])

    for name, fig in figs.items():
        out = ASSETS / f"{name}.png"
        fig.write_image(str(out), scale=2, width=900, height=380)
        print("wrote", out.relative_to(REPO))

    # Verified results
    res["session"] = f"{session.event['EventName']} {year} — Race"
    res["drivers_charted"] = [drv_a, drv_b]
    (RESULTS / "model_metrics.json").write_text(json.dumps(res, indent=2))
    pd.DataFrame(res["degradation"]).to_csv(RESULTS / "tyre_degradation.csv", index=False)
    print("wrote results/model_metrics.json and results/tyre_degradation.csv")
    print(f"\nBaseline MAE {res['baseline_mae']}s -> Model MAE {res['model_mae']}s "
          f"({res['improvement_mae_pct']}% better)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=2023)
    p.add_argument("--event", default="Monza")
    p.add_argument("--driver-a", default="VER")
    p.add_argument("--driver-b", default="LEC")
    a = p.parse_args()
    main(a.year, a.event, a.driver_a, a.driver_b)
