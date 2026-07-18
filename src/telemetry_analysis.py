"""Lap- and telemetry-level comparisons between two drivers or two laps.

Pure-pandas transforms on FastF1 telemetry frames. The functions here compute the numbers the
dashboard plots (delta time, sector deltas, corner speeds) so they can be tested independently
of the UI.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .preprocessing import align_telemetry_on_distance, to_seconds


def interpolate_channel(tel: pd.DataFrame, channel: str, distance_grid: np.ndarray) -> np.ndarray:
    """Interpolate a telemetry ``channel`` onto a common ``distance_grid`` (metres)."""
    tel = align_telemetry_on_distance(tel)
    if channel not in tel.columns:
        raise ValueError(f"channel '{channel}' not in telemetry columns {list(tel.columns)}")
    return np.interp(distance_grid, tel["Distance"].to_numpy(), tel[channel].to_numpy())


def common_distance_grid(tel_a: pd.DataFrame, tel_b: pd.DataFrame, n: int = 500) -> np.ndarray:
    """Build a shared distance axis spanning the overlap of two telemetry laps."""
    a = align_telemetry_on_distance(tel_a)
    b = align_telemetry_on_distance(tel_b)
    lo = max(a["Distance"].min(), b["Distance"].min())
    hi = min(a["Distance"].max(), b["Distance"].max())
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        raise ValueError("telemetry laps do not overlap on distance")
    return np.linspace(lo, hi, n)


def delta_time(tel_ref: pd.DataFrame, tel_cmp: pd.DataFrame, n: int = 500) -> pd.DataFrame:
    """Cumulative time gained/lost by ``cmp`` relative to ``ref`` along the lap.

    Positive values mean the comparison lap is *slower* (behind) at that point. Computed by
    integrating the speed difference over distance, a standard approximation of the FastF1
    'delta time' between two laps.

    Returns
    -------
    pandas.DataFrame
        Columns ``Distance`` (m) and ``DeltaTime`` (s).
    """
    grid = common_distance_grid(tel_ref, tel_cmp, n)
    v_ref = interpolate_channel(tel_ref, "Speed", grid) / 3.6  # km/h -> m/s
    v_cmp = interpolate_channel(tel_cmp, "Speed", grid) / 3.6
    v_ref = np.clip(v_ref, 1e-3, None)
    v_cmp = np.clip(v_cmp, 1e-3, None)
    dt_ref = np.gradient(grid) / v_ref
    dt_cmp = np.gradient(grid) / v_cmp
    delta = np.cumsum(dt_cmp - dt_ref)
    delta -= delta[0]  # anchor the trace at zero at the first shared point
    return pd.DataFrame({"Distance": grid, "DeltaTime": delta})


def channel_comparison(tel_a: pd.DataFrame, tel_b: pd.DataFrame, channel: str, n: int = 500) -> pd.DataFrame:
    """Two laps' values for a channel (Speed/Throttle/Brake/nGear) on a shared distance axis."""
    grid = common_distance_grid(tel_a, tel_b, n)
    return pd.DataFrame(
        {
            "Distance": grid,
            "A": interpolate_channel(tel_a, channel, grid),
            "B": interpolate_channel(tel_b, channel, grid),
        }
    )


def sector_deltas(lap_a: pd.Series, lap_b: pd.Series) -> pd.DataFrame:
    """Per-sector time difference (B minus A) for two laps, in seconds.

    Positive means driver B was slower in that sector.
    """
    rows = []
    for i in (1, 2, 3):
        col = f"Sector{i}Time"
        a = to_seconds(pd.Series([lap_a.get(col)])).iloc[0]
        b = to_seconds(pd.Series([lap_b.get(col)])).iloc[0]
        rows.append({"Sector": f"S{i}", "A": a, "B": b, "Delta": (b - a) if pd.notna(a) and pd.notna(b) else np.nan})
    return pd.DataFrame(rows)


def fastest_lap_summary(laps: pd.DataFrame, driver: str) -> dict:
    """Return a compact summary of a driver's fastest lap in a session."""
    from .preprocessing import clean_laps

    if hasattr(laps, "pick_drivers"):
        laps = laps.pick_drivers(driver)
    else:
        laps = laps[laps["Driver"] == driver] if "Driver" in laps.columns else laps
    df = clean_laps(laps)
    if df.empty:
        return {"driver": driver, "lap_time_s": None}
    fastest = df.loc[df["LapTimeSeconds"].idxmin()]
    return {
        "driver": driver,
        "lap_time_s": round(float(fastest["LapTimeSeconds"]), 3),
        "lap_number": int(fastest["LapNumber"]),
        "compound": fastest.get("Compound"),
        "tyre_life": None if pd.isna(fastest.get("TyreLife")) else float(fastest.get("TyreLife")),
    }
