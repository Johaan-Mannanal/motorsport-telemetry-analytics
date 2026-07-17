#!/usr/bin/env python3
"""Export compact offline sample sessions so the hosted demo works without the F1 API.

FastF1's upstream data service blocks many cloud hosts (e.g., Streamlit Cloud), so the deployed
app cannot fetch live. This script pre-loads a few sessions locally (where FastF1 works) and
writes a small set of parquet files the app can read offline.

Run locally (needs network on first run):  python scripts/build_sample_data.py
"""
from __future__ import annotations

import json
import logging
import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
logging.disable(logging.INFO)

import pandas as pd

from src import data_loader as dl

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "sample"

# (year, event, session code, friendly label). Variety of tracks and one qualifying session.
SESSIONS = [
    (2023, "Italian Grand Prix", "R", "2023 Italian GP (Monza) - Race"),
    (2023, "Bahrain Grand Prix", "R", "2023 Bahrain GP - Race"),
    (2023, "Monaco Grand Prix", "Q", "2023 Monaco GP - Qualifying"),
]

LAP_COLS = [
    "Driver", "DriverNumber", "Team", "LapNumber", "LapTime", "Stint", "Compound", "TyreLife",
    "Sector1Time", "Sector2Time", "Sector3Time", "Position", "IsAccurate",
]
CAR_COLS = ["Distance", "Speed", "Throttle", "Brake", "nGear"]


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def export_session(year, event, code, label) -> dict:
    session = dl.load_session(year, event, code)
    laps = session.laps
    slug = slugify(label)
    d = OUT / slug
    d.mkdir(parents=True, exist_ok=True)

    laps[[c for c in LAP_COLS if c in laps.columns]].to_parquet(d / "laps.parquet", index=False)

    tel_rows, pos_rows = [], []
    for drv in sorted(laps["Driver"].dropna().unique()):
        try:
            fl = laps.pick_drivers(drv).pick_fastest()
            if fl is None or pd.isna(fl["LapTime"]):
                continue
            car = fl.get_car_data().add_distance()[CAR_COLS].copy()
            car.insert(0, "Driver", drv)
            tel_rows.append(car)
            tel = fl.get_telemetry()
            pos = tel[["X", "Y", "Speed"]].copy()
            pos.insert(0, "Driver", drv)
            pos_rows.append(pos)
        except Exception:
            continue
    pd.concat(tel_rows, ignore_index=True).to_parquet(d / "telemetry.parquet", index=False)
    pd.concat(pos_rows, ignore_index=True).to_parquet(d / "position.parquet", index=False)

    wx = session.weather_data
    if wx is not None and not wx.empty:
        wx[["AirTemp", "TrackTemp", "Humidity", "WindSpeed", "Rainfall"]].to_parquet(
            d / "weather.parquet", index=False)

    (d / "meta.json").write_text(json.dumps(
        {"label": label, "event": str(session.event["EventName"]), "year": year, "session": code}, indent=2))
    n_drivers = len(tel_rows)
    print(f"  {label}: {len(laps)} laps, {n_drivers} drivers with telemetry -> data/sample/{slug}/")
    return {"slug": slug, "label": label}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = [export_session(*s) for s in SESSIONS]
    (OUT / "index.json").write_text(json.dumps(index, indent=2))
    print(f"\nWrote {len(index)} sample sessions to {OUT}")


if __name__ == "__main__":
    main()
