"""Cleaning and normalization helpers for F1 lap and telemetry data.

These functions operate on plain pandas DataFrames so they are easy to unit-test without a
network connection.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Laps slower than this multiple of the frame's pooled median lap time are treated as
# non-representative (in/out laps, safety car, traffic) for pace analysis.
OUTLIER_LAP_FACTOR = 1.07


def to_seconds(series) -> pd.Series:
    """Convert a pandas timedelta column/index (or NaT) to float seconds.

    Accepts a Series, list, or TimedeltaIndex and preserves the index when given a Series.
    """
    s = series if isinstance(series, pd.Series) else pd.Series(series)
    return pd.to_timedelta(s).dt.total_seconds()


def clean_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy copy of a laps DataFrame with numeric time columns.

    Adds ``LapTimeSeconds`` and per-sector second columns, drops laps with no lap time, and
    coerces tyre-life to numeric. Does not remove outliers (see :func:`representative_laps`).
    """
    if laps.empty:
        return laps.copy()
    df = laps.copy()
    df["LapTimeSeconds"] = to_seconds(df["LapTime"])
    for i in (1, 2, 3):
        col = f"Sector{i}Time"
        if col in df.columns:
            df[f"Sector{i}Seconds"] = to_seconds(df[col])
    if "TyreLife" in df.columns:
        df["TyreLife"] = pd.to_numeric(df["TyreLife"], errors="coerce")
    df = df.dropna(subset=["LapTimeSeconds"]).reset_index(drop=True)
    return df


def representative_laps(laps: pd.DataFrame, factor: float = OUTLIER_LAP_FACTOR) -> pd.DataFrame:
    """Filter to 'green' representative laps for pace analysis.

    Removes laps whose time exceeds ``factor`` times the median lap time (a common heuristic for
    excluding in/out laps, safety-car and traffic-affected laps). Also drops laps flagged as
    inaccurate by FastF1 when that column is available.

    Parameters
    ----------
    laps:
        Cleaned laps (must contain ``LapTimeSeconds``).
    factor:
        Multiplier of the median lap time above which laps are discarded.
    """
    df = clean_laps(laps) if "LapTimeSeconds" not in laps.columns else laps.copy()
    if df.empty:
        return df
    if "IsAccurate" in df.columns:
        df = df[df["IsAccurate"].fillna(False)]
    if df.empty:
        return df
    median = df["LapTimeSeconds"].median()
    return df[df["LapTimeSeconds"] <= median * factor].reset_index(drop=True)


def align_telemetry_on_distance(tel: pd.DataFrame) -> pd.DataFrame:
    """Ensure a telemetry frame has a monotonic ``Distance`` index for overlaying two laps.

    FastF1 telemetry already includes a ``Distance`` channel; this drops duplicates and sorts so
    two drivers' laps can be compared on the same distance axis.
    """
    if "Distance" not in tel.columns:
        raise ValueError("telemetry frame has no 'Distance' column; call add_distance() upstream.")
    return (
        tel.dropna(subset=["Distance"])
        .drop_duplicates(subset="Distance")
        .sort_values("Distance")
        .reset_index(drop=True)
    )


def stint_summary(laps: pd.DataFrame) -> pd.DataFrame:
    """Summarize each stint: compound, lap count, and tyre-life range.

    Useful for the tyre-strategy view. Expects cleaned laps with ``Stint`` and ``Compound``.
    """
    df = clean_laps(laps)
    if df.empty or "Stint" not in df.columns:
        return pd.DataFrame(columns=["Stint", "Compound", "Laps", "StartLap", "EndLap"])
    out = (
        df.groupby("Stint")
        .agg(
            Compound=("Compound", "first"),
            Laps=("LapNumber", "count"),
            StartLap=("LapNumber", "min"),
            EndLap=("LapNumber", "max"),
        )
        .reset_index()
    )
    return out
