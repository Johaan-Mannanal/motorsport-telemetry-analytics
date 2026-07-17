"""Plotly figure builders for the dashboard.

Each function takes already-computed data (from ``telemetry_analysis`` / ``preprocessing``) and
returns a dark-themed ``plotly.graph_objects.Figure``. Two-driver charts accept the drivers'
colours (their F1 team colours) so the dashboard reads like a broadcast graphic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import theme

_TEMPLATE = theme.register_template()
_A = "#ff1801"
_B = "#00d2ff"
_LAYOUT = dict(template=_TEMPLATE, height=340)


def _fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title, **_LAYOUT)
    return fig


def channel_trace(cmp: pd.DataFrame, channel: str, name_a: str, name_b: str,
                  color_a: str = _A, color_b: str = _B) -> go.Figure:
    """Overlay a telemetry channel (Speed/Throttle/Brake/nGear) for two laps vs. distance."""
    fig = _fig(f"{channel} vs distance")
    fig.add_scatter(x=cmp["Distance"], y=cmp["A"], name=name_a, line=dict(color=color_a, width=2))
    fig.add_scatter(x=cmp["Distance"], y=cmp["B"], name=name_b, line=dict(color=color_b, width=2))
    fig.update_xaxes(title="Distance (m)")
    fig.update_yaxes(title=channel)
    return fig


def delta_time_trace(delta: pd.DataFrame, name_a: str, name_b: str,
                     color_b: str = _B) -> go.Figure:
    """Cumulative delta time between two laps (positive = B behind A)."""
    fig = _fig(f"Delta time: {name_b} relative to {name_a}")
    fig.add_scatter(x=delta["Distance"], y=delta["DeltaTime"], line=dict(color=color_b, width=2),
                    fill="tozeroy", fillcolor="rgba(0,210,255,0.10)")
    fig.add_hline(y=0, line=dict(color=theme.MUTED, dash="dash"))
    fig.update_xaxes(title="Distance (m)")
    fig.update_yaxes(title=f"Δt (s)  +ve = {name_b} slower")
    return fig


def laptime_comparison(laps_a: pd.DataFrame, laps_b: pd.DataFrame, name_a: str, name_b: str,
                       color_a: str = _A, color_b: str = _B) -> go.Figure:
    """Lap time vs lap number for two drivers (green laps)."""
    fig = _fig("Lap time by lap")
    fig.add_scatter(x=laps_a["LapNumber"], y=laps_a["LapTimeSeconds"], mode="lines+markers",
                    name=name_a, line=dict(color=color_a, width=2), marker=dict(size=5))
    fig.add_scatter(x=laps_b["LapNumber"], y=laps_b["LapTimeSeconds"], mode="lines+markers",
                    name=name_b, line=dict(color=color_b, width=2), marker=dict(size=5))
    fig.update_xaxes(title="Lap number")
    fig.update_yaxes(title="Lap time (s)")
    return fig


def sector_delta_bar(sd: pd.DataFrame, name_a: str, name_b: str,
                     color_a: str = _A, color_b: str = _B) -> go.Figure:
    """Bar chart of per-sector time delta (B minus A)."""
    fig = _fig(f"Sector deltas: {name_b} minus {name_a}")
    colors = [color_b if v > 0 else color_a for v in sd["Delta"].fillna(0)]
    fig.add_bar(x=sd["Sector"], y=sd["Delta"], marker_color=colors,
                text=[f"{v:+.3f}" for v in sd["Delta"]], textposition="outside")
    fig.add_hline(y=0, line=dict(color=theme.MUTED))
    fig.update_yaxes(title="Δt (s)")
    return fig


def track_position_map(pos: pd.DataFrame, speed: pd.Series | None = None,
                       title: str = "Track position") -> go.Figure:
    """Plot the X/Y track map, optionally coloured by speed."""
    fig = _fig(title)
    if speed is not None and len(speed) == len(pos):
        fig.add_scatter(x=pos["X"], y=pos["Y"], mode="markers",
                        marker=dict(size=5, color=speed, colorscale="Turbo",
                                    colorbar=dict(title="km/h")))
    else:
        fig.add_scatter(x=pos["X"], y=pos["Y"], mode="lines", line=dict(color=_A))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(height=470)
    return fig


def degradation_bar(degradation: list[dict]) -> go.Figure:
    """Bar chart of tyre-degradation slope (s/lap) per compound."""
    fig = _fig("Tyre degradation (s lost per lap of tyre life)")
    comp = [d["compound"] for d in degradation]
    slope = [d["slope_s_per_lap"] for d in degradation]
    palette = {"SOFT": "#ff2d55", "MEDIUM": "#ffd60a", "HARD": "#e6edf3",
               "INTERMEDIATE": "#30d158", "WET": "#0a84ff"}
    colors = [palette.get(str(c).upper(), "#9aa7b4") for c in comp]
    fig.add_bar(x=comp, y=slope, marker_color=colors,
                text=[f"{s:.3f}" for s in slope], textposition="outside")
    fig.update_yaxes(title="s / lap")
    return fig


def weather_summary_table(weather: pd.DataFrame) -> pd.DataFrame:
    """Aggregate weather into a small summary table for display."""
    if weather is None or weather.empty:
        return pd.DataFrame()
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
