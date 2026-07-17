"""Plotly figure builders for the dashboard.

Each function takes already-computed data (from ``telemetry_analysis`` / ``preprocessing``) and
returns a ``plotly.graph_objects.Figure``. Keeping plotting separate from analysis makes both
testable and lets the same figures be exported to static images for the README.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Consistent, colour-blind-friendly two-driver palette.
COLOR_A = "#1f77b4"
COLOR_B = "#d62728"
_LAYOUT = dict(template="plotly_white", margin=dict(l=60, r=20, t=50, b=45), height=340)


def _fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title, **_LAYOUT)
    return fig


def channel_trace(cmp: pd.DataFrame, channel: str, name_a: str, name_b: str) -> go.Figure:
    """Overlay a telemetry channel (Speed/Throttle/Brake/nGear) for two laps vs. distance."""
    fig = _fig(f"{channel} vs distance")
    fig.add_scatter(x=cmp["Distance"], y=cmp["A"], name=name_a, line=dict(color=COLOR_A))
    fig.add_scatter(x=cmp["Distance"], y=cmp["B"], name=name_b, line=dict(color=COLOR_B))
    fig.update_xaxes(title="Distance (m)")
    fig.update_yaxes(title=channel)
    return fig


def delta_time_trace(delta: pd.DataFrame, name_a: str, name_b: str) -> go.Figure:
    """Cumulative delta time between two laps (positive = B behind A)."""
    fig = _fig(f"Delta time: {name_b} relative to {name_a}")
    fig.add_scatter(x=delta["Distance"], y=delta["DeltaTime"], line=dict(color=COLOR_B))
    fig.add_hline(y=0, line=dict(color="grey", dash="dash"))
    fig.update_xaxes(title="Distance (m)")
    fig.update_yaxes(title=f"Δt (s)  +ve = {name_b} slower")
    return fig


def laptime_comparison(laps_a: pd.DataFrame, laps_b: pd.DataFrame, name_a: str, name_b: str) -> go.Figure:
    """Lap time vs lap number for two drivers (green laps)."""
    fig = _fig("Lap time by lap")
    fig.add_scatter(x=laps_a["LapNumber"], y=laps_a["LapTimeSeconds"], mode="lines+markers",
                    name=name_a, line=dict(color=COLOR_A))
    fig.add_scatter(x=laps_b["LapNumber"], y=laps_b["LapTimeSeconds"], mode="lines+markers",
                    name=name_b, line=dict(color=COLOR_B))
    fig.update_xaxes(title="Lap number")
    fig.update_yaxes(title="Lap time (s)")
    return fig


def sector_delta_bar(sd: pd.DataFrame, name_a: str, name_b: str) -> go.Figure:
    """Bar chart of per-sector time delta (B minus A)."""
    fig = _fig(f"Sector deltas: {name_b} minus {name_a}")
    colors = [COLOR_B if v > 0 else COLOR_A for v in sd["Delta"].fillna(0)]
    fig.add_bar(x=sd["Sector"], y=sd["Delta"], marker_color=colors)
    fig.add_hline(y=0, line=dict(color="grey"))
    fig.update_yaxes(title="Δt (s)")
    return fig


def track_position_map(pos: pd.DataFrame, speed: pd.Series | None = None, title: str = "Track position") -> go.Figure:
    """Plot the X/Y track map, optionally coloured by speed."""
    fig = _fig(title)
    if speed is not None and len(speed) == len(pos):
        fig.add_scatter(x=pos["X"], y=pos["Y"], mode="markers",
                        marker=dict(size=4, color=speed, colorscale="Turbo", colorbar=dict(title="km/h")))
    else:
        fig.add_scatter(x=pos["X"], y=pos["Y"], mode="lines", line=dict(color=COLOR_A))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(height=460)
    return fig


def degradation_bar(degradation: list[dict]) -> go.Figure:
    """Bar chart of tyre-degradation slope (s/lap) per compound."""
    fig = _fig("Tyre degradation (s lost per lap of tyre life)")
    comp = [d["compound"] for d in degradation]
    slope = [d["slope_s_per_lap"] for d in degradation]
    fig.add_bar(x=comp, y=slope, marker_color="#2ca02c")
    fig.update_yaxes(title="s / lap")
    return fig


def weather_summary_table(weather: pd.DataFrame) -> pd.DataFrame:
    """Aggregate weather into a small summary table for display."""
    if weather is None or weather.empty:
        return pd.DataFrame()
    # Keep the Value column a single (string) dtype so it serializes cleanly for display.
    return pd.DataFrame(
        {
            "Metric": ["Air temp (°C)", "Track temp (°C)", "Humidity (%)", "Wind (m/s)", "Rainfall"],
            "Value": [
                f"{weather['AirTemp'].mean():.1f}",
                f"{weather['TrackTemp'].mean():.1f}",
                f"{weather['Humidity'].mean():.1f}",
                f"{weather['WindSpeed'].mean():.1f}",
                "Yes" if bool(weather["Rainfall"].any()) else "No",
            ],
        }
    )
