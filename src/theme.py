"""Visual theme: F1 team colours, a dark Plotly template, and app CSS.

Kept in one place so the dashboard and the exported README assets share one look.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# Dashboard palette (dark, high-contrast).
BG = "#0d1117"
PANEL = "#161b22"
GRID = "#2a323d"
INK = "#e6edf3"
MUTED = "#9aa7b4"
ACCENT = "#ff1801"  # F1 red

# F1 team colours, matched by a substring of the team name (covers 2023–2024 naming).
TEAM_COLORS = {
    "red bull": "#3671C6",
    "ferrari": "#E8002D",
    "mercedes": "#27F4D2",
    "mclaren": "#FF8000",
    "aston martin": "#229971",
    "alpine": "#2293D1",
    "williams": "#64C4FF",
    "rb": "#6692FF",
    "alphatauri": "#6692FF",
    "racing bulls": "#6692FF",
    "sauber": "#52E252",
    "kick": "#52E252",
    "alfa romeo": "#C92D4B",
    "haas": "#B6BABD",
}
_FALLBACK = ["#ff1801", "#00d2ff"]


def team_color(team: str | None, index: int = 0) -> str:
    """Return a hex colour for a team name, falling back to a bright default."""
    if team:
        t = str(team).lower()
        for key, col in TEAM_COLORS.items():
            if key in t:
                return col
    return _FALLBACK[index % len(_FALLBACK)]


def driver_colors(team_a: str | None, team_b: str | None) -> tuple[str, str]:
    """Two distinct colours for a driver pairing.

    Uses each driver's team colour; if they share a team (or colour), the second is nudged so the
    two traces stay distinguishable.
    """
    ca = team_color(team_a, 0)
    cb = team_color(team_b, 1)
    if ca.lower() == cb.lower():
        cb = "#00d2ff" if ca.lower() != "#00d2ff" else "#ffb000"
    return ca, cb


def register_template() -> str:
    """Register and return the name of a dark Plotly template matching the app."""
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, family="Inter, system-ui, sans-serif", size=13),
        title=dict(font=dict(color=INK, size=16)),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=56, r=20, t=48, b=44),
    )
    pio.templates["f1dark"] = tmpl
    return "f1dark"


# App CSS: web fonts, hidden Streamlit chrome, hero header, cards, driver chips.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap');

:root { --accent:#ff1801; --panel:#161b22; --ink:#e6edf3; --muted:#9aa7b4; --grid:#2a323d; }

.stApp { background:
    radial-gradient(1200px 600px at 100% -10%, rgba(255,24,1,0.08), transparent 60%),
    #0d1117; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
h1, h2, h3, .mt-display { font-family: 'Rajdhani', sans-serif; letter-spacing: .5px; }

/* Hero */
.mt-hero { padding: 6px 0 2px; border-bottom: 1px solid var(--grid); margin-bottom: 6px; }
.mt-hero h1 { font-size: 2.15rem; font-weight: 700; margin: 0; line-height: 1.05;
    text-transform: uppercase; }
.mt-hero .bar { height: 4px; width: 96px; margin-top: 8px; border-radius: 3px;
    background: linear-gradient(90deg, var(--accent), #ff6a3d); }
.mt-hero p { color: var(--muted); margin: 8px 0 0; font-size: .92rem; }

/* Driver matchup chips */
.mt-matchup { display:flex; align-items:center; gap:14px; margin: 4px 0 22px; flex-wrap: wrap; }
.mt-chip { display:flex; align-items:center; gap:11px; background: var(--panel);
    border:1px solid var(--grid); border-radius:12px; padding:10px 18px; min-width:150px; }
.mt-chip .dot { width:12px; height:12px; border-radius:50%; flex:0 0 auto; }
.mt-chip-txt { display:flex; flex-direction:column; gap:2px; line-height:1.1; }
.mt-chip .abbr { font-family:'Rajdhani',sans-serif; font-weight:700; font-size:1.25rem;
    letter-spacing:1px; }
.mt-chip .team { color: var(--muted); font-size:.78rem; }
.mt-vs { font-family:'Rajdhani',sans-serif; font-weight:700; color: var(--muted);
    font-size:1.05rem; padding:0 2px; }

/* Metric cards */
[data-testid="stMetric"] { background: var(--panel); border:1px solid var(--grid);
    border-radius:12px; padding:12px 16px; }
[data-testid="stMetricValue"] { font-family:'JetBrains Mono', monospace; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { font-family:'Rajdhani',sans-serif; font-weight:600;
    letter-spacing:.5px; text-transform:uppercase; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0b0f14; border-right:1px solid var(--grid); }

.block-container { padding-top: 2.2rem; max-width: 1200px; }
</style>
"""


def hero(title: str, subtitle: str) -> str:
    """Return HTML for the hero header block."""
    return (
        f'<div class="mt-hero"><h1>{title}</h1><div class="bar"></div>'
        f'<p>{subtitle}</p></div>'
    )


def matchup(abbr_a: str, team_a: str | None, color_a: str,
            abbr_b: str, team_b: str | None, color_b: str) -> str:
    """Return HTML for the two-driver matchup chips."""
    def chip(abbr, team, color):
        return (f'<div class="mt-chip"><span class="dot" style="background:{color}"></span>'
                f'<span class="mt-chip-txt"><span class="abbr">{abbr}</span>'
                f'<span class="team">{team or ""}</span></span></div>')
    return (f'<div class="mt-matchup">{chip(abbr_a, team_a, color_a)}'
            f'<span class="mt-vs">VS</span>{chip(abbr_b, team_b, color_b)}</div>')
