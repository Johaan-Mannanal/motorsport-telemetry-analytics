"""Motorsport Telemetry Analytics Streamlit dashboard.

Compare two drivers' fastest laps from a Formula 1 session: speed/throttle/brake/gear traces,
delta time, sector deltas, a track-position map, tyre strategy, weather, and a transparent
tyre-degradation / lap-time model. Drivers are drawn in their real F1 team colours.

The hosted demo uses bundled sample sessions (the F1 data service blocks many cloud hosts);
running locally you can also load any live session (2018+) via FastF1.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import logging
import warnings

warnings.filterwarnings("ignore")
logging.getLogger("fastf1").setLevel(logging.ERROR)

import pandas as pd
import streamlit as st

from src import data_loader as dl
from src import modeling as mdl
from src import preprocessing as pp
from src import sample_data as sd
from src import telemetry_analysis as ta
from src import theme
from src import visualizations as viz

st.set_page_config(page_title="Motorsport Telemetry Analytics", layout="wide", page_icon="🏁")
st.markdown(theme.CSS, unsafe_allow_html=True)

SESSION_CODES = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3",
                 "Qualifying": "Q", "Sprint": "S", "Race": "R"}
CHART = {"width": "stretch", "config": {"displayModeBar": False}}


@st.cache_resource(show_spinner=False)
def _sample(slug: str):
    return sd.load_sample(slug)


@st.cache_resource(show_spinner=True)
def _live(year: int, event: str, code: str):
    return dl.load_session(year, event, code)


def choose_session():
    st.sidebar.markdown("### Session")
    samples = sd.list_samples()
    labels = [s["label"] for s in samples]
    pick = st.sidebar.selectbox("Example session", labels, index=0, label_visibility="collapsed")
    slug = samples[labels.index(pick)]["slug"]
    with st.sidebar.expander("Or load a live session (local only)"):
        st.caption("Needs the F1 data service, which is blocked on the hosted demo. Works locally.")
        use_live = st.checkbox("Use a live session instead")
        year = st.selectbox("Season", list(range(2024, 2017, -1)), index=1)
        event = st.text_input("Race (e.g. Monza, Silverstone)", "Monza")
        code = SESSION_CODES[st.selectbox("Session", list(SESSION_CODES), index=5)]
    if use_live:
        try:
            return _live(year, event, code)
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Live load failed: {exc}")
            st.sidebar.info("Using the selected example session.")
    return _sample(slug)


def driver_team(laps: pd.DataFrame, driver: str) -> str | None:
    rows = laps[laps["Driver"] == driver]
    if rows.empty or "Team" not in rows.columns:
        return None
    teams = rows["Team"].dropna()
    return str(teams.iloc[0]) if len(teams) else None


def main() -> None:
    session = choose_session()
    label = getattr(session, "label", None) or getattr(session, "event_name", "F1 session")
    st.markdown(theme.hero(
        "Telemetry Analytics",
        "Two-driver lap analysis from Formula 1 telemetry: fastest-lap comparison, delta time, "
        "sectors, tyres and a transparent pace model.",
    ), unsafe_allow_html=True)

    drivers = dl.session_drivers(session)
    if len(drivers) < 2:
        st.warning("This session has fewer than two drivers with lap data.")
        st.stop()

    laps_all = dl.session_laps(session)
    c1, c2 = st.sidebar.columns(2)
    drv_a = c1.selectbox("Driver A", drivers, index=0)
    drv_b = c2.selectbox("Driver B", drivers, index=min(1, len(drivers) - 1))

    team_a, team_b = driver_team(laps_all, drv_a), driver_team(laps_all, drv_b)
    color_a, color_b = theme.driver_colors(team_a, team_b)

    st.markdown(f"**{label}**")
    st.markdown(theme.matchup(drv_a, team_a, color_a, drv_b, team_b, color_b), unsafe_allow_html=True)

    laps_a = pp.clean_laps(dl.driver_laps(session, drv_a))
    laps_b = pp.clean_laps(dl.driver_laps(session, drv_b))
    row_a, row_b = dl.fastest_lap_row(session, drv_a), dl.fastest_lap_row(session, drv_b)
    sa, sb = ta.fastest_lap_summary(laps_a, drv_a), ta.fastest_lap_summary(laps_b, drv_b)

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{drv_a} fastest lap", f"{sa['lap_time_s']:.3f}s" if sa["lap_time_s"] else "n/a")
    m2.metric(f"{drv_b} fastest lap", f"{sb['lap_time_s']:.3f}s" if sb["lap_time_s"] else "n/a")
    if sa["lap_time_s"] and sb["lap_time_s"]:
        gap = sb["lap_time_s"] - sa["lap_time_s"]
        m3.metric("Gap (B − A)", f"{gap:+.3f}s", delta=f"{drv_a if gap > 0 else drv_b} faster",
                  delta_color="off")

    tabs = st.tabs(["Lap pace", "Telemetry", "Track & sectors", "Tyres & weather", "Pace model"])

    with tabs[0]:
        st.plotly_chart(viz.laptime_comparison(laps_a, laps_b, drv_a, drv_b, color_a, color_b), **CHART)
        st.caption("Lap time by lap number, all timed laps; pit stops and safety cars appear as spikes.")

    with tabs[1]:
        st.caption("Each driver's fastest lap, aligned on a shared distance axis.")
        try:
            tel_a = dl.fastest_car_telemetry(session, drv_a)
            tel_b = dl.fastest_car_telemetry(session, drv_b)
            st.plotly_chart(viz.delta_time_trace(ta.delta_time(tel_a, tel_b), drv_a, drv_b, color_b), **CHART)
            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(viz.channel_trace(ta.channel_comparison(tel_a, tel_b, "Speed"), "Speed", drv_a, drv_b, color_a, color_b), **CHART)
                st.plotly_chart(viz.channel_trace(ta.channel_comparison(tel_a, tel_b, "Brake"), "Brake", drv_a, drv_b, color_a, color_b), **CHART)
            with g2:
                st.plotly_chart(viz.channel_trace(ta.channel_comparison(tel_a, tel_b, "Throttle"), "Throttle", drv_a, drv_b, color_a, color_b), **CHART)
                st.plotly_chart(viz.channel_trace(ta.channel_comparison(tel_a, tel_b, "nGear"), "nGear", drv_a, drv_b, color_a, color_b), **CHART)
        except Exception as exc:  # noqa: BLE001
            st.info(f"Telemetry unavailable for this pairing: {exc}")

    with tabs[2]:
        t1, t2 = st.columns([3, 2])
        with t1:
            try:
                pos_a = dl.fastest_position(session, drv_a)
                st.plotly_chart(viz.track_position_map(pos_a, pos_a.get("Speed"), f"{drv_a} fastest lap speed"), **CHART)
            except Exception as exc:  # noqa: BLE001
                st.info(f"Track map unavailable: {exc}")
        with t2:
            if row_a is not None and row_b is not None:
                st.plotly_chart(viz.sector_delta_bar(ta.sector_deltas(row_a, row_b), drv_a, drv_b, color_a, color_b), **CHART)

    with tabs[3]:
        cA, cB = st.columns(2)
        cA.markdown(f"**{drv_a} stints**"); cA.dataframe(pp.stint_summary(laps_a), width="stretch", hide_index=True)
        cB.markdown(f"**{drv_b} stints**"); cB.dataframe(pp.stint_summary(laps_b), width="stretch", hide_index=True)
        wx = viz.weather_summary_table(dl.session_weather(session))
        if not wx.empty:
            st.markdown("**Weather (session average)**")
            st.dataframe(wx, width="stretch", hide_index=True)

    with tabs[4]:
        st.markdown("#### Tyre degradation & lap-time model")
        st.caption("A transparent baseline comparison on this session's green laps, not a "
                   "race-strategy oracle. Methodology and limitations below.")
        try:
            res = mdl.evaluate_laptime_model(laps_all).to_dict()
            k1, k2, k3 = st.columns(3)
            k1.metric("Baseline MAE", f"{res['baseline_mae']:.3f}s")
            k2.metric("Model MAE", f"{res['model_mae']:.3f}s")
            k3.metric("Improvement", f"{res['improvement_mae_pct']:.0f}%")
            if res["degradation"]:
                st.plotly_chart(viz.degradation_bar(res["degradation"]), **CHART)
                st.dataframe(pd.DataFrame(res["degradation"]), width="stretch", hide_index=True)
            with st.expander("Methodology & limitations"):
                st.write(f"Train laps: {res['n_train']} · Test laps: {res['n_test']} · "
                         f"{len(res['features'])} features")
                for n in res["notes"]:
                    st.write(f"- {n}")
        except ValueError as exc:
            st.info(f"Not enough green laps in this session to fit the model: {exc}")

    st.markdown("<br><span style='color:#9aa7b4;font-size:.8rem'>Public F1 data via FastF1. "
                "Unofficial; not affiliated with Formula 1.</span>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
