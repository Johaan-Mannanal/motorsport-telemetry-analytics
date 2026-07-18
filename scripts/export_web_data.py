#!/usr/bin/env python3
"""Export the bundled sample sessions as JSON for the static web dashboard (web/).

Reads the parquet files in data/sample/ (no network needed) and writes one JSON file per
session to web/public/data/, plus an index. The web app consumes these directly, so the
hosted dashboard needs no Python backend.

Run from the repo root:  python scripts/export_web_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src import data_loader as dl
from src import modeling as mdl
from src import preprocessing as pp
from src import sample_data as sd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "web" / "public" / "data"


def _round_records(df: pd.DataFrame, spec: dict[str, int]) -> list[dict]:
    """DataFrame -> list of dicts with per-column rounding to keep JSON small."""
    out = df[list(spec)].copy()
    for col, nd in spec.items():
        out[col] = out[col].astype(float).round(nd)
    return out.to_dict("records")


def export_session(slug: str) -> dict:
    sess = sd.load_sample(slug)
    laps_all = dl.session_laps(sess)
    drivers = dl.session_drivers(sess)

    per_driver = {}
    for drv in drivers:
        raw = dl.driver_laps(sess, drv)
        clean = pp.clean_laps(raw)
        if clean.empty:
            continue
        fastest = dl.fastest_lap_row(sess, drv)
        tel = dl.fastest_car_telemetry(sess, drv)
        pos = dl.fastest_position(sess, drv)
        stints = pp.stint_summary(clean)
        team = None
        if "Team" in raw.columns and raw["Team"].notna().any():
            team = str(raw["Team"].dropna().iloc[0])

        sectors = {}
        if fastest is not None:
            for i in (1, 2, 3):
                v = fastest.get(f"Sector{i}Time")
                sec = pd.to_timedelta(v).total_seconds() if pd.notna(v) else None
                sectors[f"s{i}"] = round(sec, 3) if sec is not None else None

        per_driver[drv] = {
            "team": team,
            "laps": _round_records(clean.assign(sec=clean["LapTimeSeconds"]),
                                   {"LapNumber": 0, "sec": 3}),
            "compounds": clean["Compound"].astype(str).tolist() if "Compound" in clean.columns else [],
            "fastest": {
                "sec": round(float(fastest["LapTime"].total_seconds()), 3) if fastest is not None else None,
                "lap": int(fastest["LapNumber"]) if fastest is not None else None,
                "compound": str(fastest.get("Compound")) if fastest is not None else None,
                "sectors": sectors,
            },
            "telemetry": _round_records(tel, {"Distance": 1, "Speed": 1, "Throttle": 1,
                                              "Brake": 0, "nGear": 0}),
            "position": _round_records(pos, {"X": 0, "Y": 0, "Speed": 1}),
            "stints": stints.astype({"Stint": int, "Laps": int, "StartLap": int, "EndLap": int})
                            .to_dict("records"),
        }

    weather = None
    wx = dl.session_weather(sess)
    if wx is not None and not wx.empty:
        weather = {
            "airTemp": round(float(wx["AirTemp"].mean()), 1),
            "trackTemp": round(float(wx["TrackTemp"].mean()), 1),
            "humidity": round(float(wx["Humidity"].mean()), 1),
            "windSpeed": round(float(wx["WindSpeed"].mean()), 1),
            "rain": bool(wx["Rainfall"].any()),
        }

    try:
        model = mdl.evaluate_laptime_model(laps_all).to_dict()
        model.pop("features", None)
    except ValueError:
        model = None

    payload = {
        "label": sess.label,
        "event": sess.event_name,
        "drivers": per_driver,
        "weather": weather,
        "model": model,
    }
    out = OUT / f"{slug}.json"
    out.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"  {slug}: {len(per_driver)} drivers, {out.stat().st_size // 1024} KB")
    return {"slug": slug, "label": sess.label}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = [export_session(s["slug"]) for s in sd.list_samples()]
    (OUT / "index.json").write_text(json.dumps(index))
    print(f"wrote {len(index)} sessions to web/public/data/")


if __name__ == "__main__":
    main()
