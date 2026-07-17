"""Load bundled offline sample sessions.

The hosted demo cannot reach the F1 data service (it blocks many cloud hosts), so a few sessions
are pre-exported to compact parquet files by ``scripts/build_sample_data.py``. This module reads
them into a lightweight :class:`SampleSession` that exposes just what the dashboard needs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "sample"


@dataclass
class SampleSession:
    """A pre-loaded, offline F1 session backed by bundled parquet files."""

    label: str
    event_name: str
    laps: pd.DataFrame
    _telemetry: pd.DataFrame
    _position: pd.DataFrame
    weather: Optional[pd.DataFrame]

    @property
    def drivers(self) -> list[str]:
        return sorted(self.laps["Driver"].dropna().unique().tolist())

    def fastest_lap_row(self, driver: str) -> Optional[pd.Series]:
        laps = self.laps[self.laps["Driver"] == driver].dropna(subset=["LapTime"])
        if laps.empty:
            return None
        return laps.loc[laps["LapTime"].idxmin()]

    def fastest_car_telemetry(self, driver: str) -> pd.DataFrame:
        """Car telemetry (Distance, Speed, Throttle, Brake, nGear) for the driver's fastest lap."""
        return self._telemetry[self._telemetry["Driver"] == driver].drop(columns="Driver").reset_index(drop=True)

    def fastest_position(self, driver: str) -> pd.DataFrame:
        """Track position (X, Y, Speed) for the driver's fastest lap."""
        return self._position[self._position["Driver"] == driver].drop(columns="Driver").reset_index(drop=True)


def list_samples() -> list[dict]:
    """Return the available sample sessions (``label`` and ``slug``)."""
    index = SAMPLE_DIR / "index.json"
    if not index.exists():
        return []
    return json.loads(index.read_text())


def load_sample(slug: str) -> SampleSession:
    """Load a bundled sample session by slug."""
    d = SAMPLE_DIR / slug
    if not d.exists():
        raise FileNotFoundError(f"sample session '{slug}' not found in {SAMPLE_DIR}")
    meta = json.loads((d / "meta.json").read_text())
    weather_path = d / "weather.parquet"
    return SampleSession(
        label=meta["label"],
        event_name=meta["event"],
        laps=pd.read_parquet(d / "laps.parquet"),
        _telemetry=pd.read_parquet(d / "telemetry.parquet"),
        _position=pd.read_parquet(d / "position.parquet"),
        weather=pd.read_parquet(weather_path) if weather_path.exists() else None,
    )
