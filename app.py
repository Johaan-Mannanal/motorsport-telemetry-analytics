"""Motorsport Telemetry Analytics — Streamlit dashboard.

Compare two drivers' laps from any F1 session (2018+) using public FastF1 data: lap-time and
speed/throttle/brake/gear traces, delta time, sector deltas, a track-position map, tyre
strategy, weather, and a transparent tyre-degradation / lap-time model.

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
from src import telemetry_analysis as ta
from src import visualizations as viz

st.set_page_config(page_title="Motorsport Telemetry Analytics", layout="wide", page_icon="🏎️")

SESSION_CODES = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3",
                 "Qualifying": "Q", "Sprint": "S", "Race": "R"}


@st.cache_data(show_spinner=False)
def _events(year: int) -> list[str]:
    return dl.list_events(year)


@st.cache_resource(show_spinner=True)
def _session(year: int, event: str, code: str):
    return dl.load_session(year, event, code)


def sidebar():
    st.sidebar.header("Session")
    year = st.sidebar.selectbox("Season", list(range(2024, 2017, -1)), index=1)
    try:
        events = _events(year)
    except Exception as exc:  # noqa: BLE001
        st.sidebar.error(f"Could not load {year} schedule: {exc}")
        st.stop()
    event = st.sidebar.selectbox("Race", events, index=min(len(events) - 1, 14))
    session_label = st.sidebar.selectbox("Session", list(SESSION_CODES), index=5)
    return year, event, SESSION_CODES[session_label]


def main() -> None:
    st.title("Motorsport Telemetry Analytics")
    st.caption(
        "Interactive Formula 1 telemetry and race-performance analysis. Public data via FastF1. "
        "Unofficial; not affiliated with Formula 1."
    )

    year, event, code = sidebar()
    with st.spinner(f"Loading {event} {year} {code} … (first load downloads & caches data)"):
        try:
            session = _session(year, event, code)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load session: {exc}")
            st.stop()

    laps_all = session.laps
    drivers = dl.get_drivers(session)
    if len(drivers) < 2:
        st.warning("This session has fewer than two drivers with lap data.")
        st.stop()

    c1, c2 = st.sidebar.columns(2)
    drv_a = c1.selectbox("Driver A", drivers, index=0)
    drv_b = c2.selectbox("Driver B", drivers, index=1)

    laps_a_raw = laps_all.pick_drivers(drv_a)
    laps_b_raw = laps_all.pick_drivers(drv_b)
    laps_a = pp.clean_laps(laps_a_raw)
    laps_b = pp.clean_laps(laps_b_raw)

    # --- Fastest-lap summary row ---
    sa = ta.fastest_lap_summary(laps_all, drv_a)
    sb = ta.fastest_lap_summary(laps_all, drv_b)
    m1, m2, m3 = st.columns(3)
    m1.metric(f"{drv_a} fastest lap (s)", sa["lap_time_s"])
    m2.metric(f"{drv_b} fastest lap (s)", sb["lap_time_s"])
    if sa["lap_time_s"] and sb["lap_time_s"]:
        m3.metric("Gap (B − A)", f"{sb['lap_time_s'] - sa['lap_time_s']:+.3f}")

    # --- Lap selection for telemetry overlay ---
    st.sidebar.subheader("Laps to overlay")
    lap_a = _pick_lap(st.sidebar, laps_a_raw, drv_a, "A")
    lap_b = _pick_lap(st.sidebar, laps_b_raw, drv_b, "B")

    tabs = st.tabs(["Lap comparison", "Telemetry", "Track & sectors", "Tyres & weather", "Model"])

    with tabs[0]:
        st.plotly_chart(viz.laptime_comparison(laps_a, laps_b, drv_a, drv_b), use_container_width=True)

    with tabs[1]:
        if lap_a is not None and lap_b is not None:
            tel_a = lap_a.get_car_data().add_distance()
            tel_b = lap_b.get_car_data().add_distance()
            st.plotly_chart(viz.delta_time_trace(ta.delta_time(tel_a, tel_b), drv_a, drv_b),
                            use_container_width=True)
            for ch in ("Speed", "Throttle", "Brake", "nGear"):
                st.plotly_chart(viz.channel_trace(ta.channel_comparison(tel_a, tel_b, ch), ch, drv_a, drv_b),
                                use_container_width=True)
        else:
            st.info("Select a lap for each driver in the sidebar.")

    with tabs[2]:
        if lap_a is not None:
            tel_a = lap_a.get_telemetry()
            st.plotly_chart(viz.track_position_map(tel_a, tel_a.get("Speed"), f"{drv_a} — lap {int(lap_a['LapNumber'])}"),
                            use_container_width=True)
        sd = ta.sector_deltas(lap_a, lap_b) if (lap_a is not None and lap_b is not None) else pd.DataFrame()
        if not sd.empty:
            st.plotly_chart(viz.sector_delta_bar(sd, drv_a, drv_b), use_container_width=True)

    with tabs[3]:
        colA, colB = st.columns(2)
        colA.subheader(f"{drv_a} stints"); colA.dataframe(pp.stint_summary(laps_a), use_container_width=True)
        colB.subheader(f"{drv_b} stints"); colB.dataframe(pp.stint_summary(laps_b), use_container_width=True)
        wx = viz.weather_summary_table(session.weather_data)
        if not wx.empty:
            st.subheader("Weather (session average)")
            st.dataframe(wx, use_container_width=True, hide_index=True)

    with tabs[4]:
        st.subheader("Tyre-degradation & lap-time model")
        st.caption("Transparent baseline comparison — not a race-strategy oracle. Trained on this "
                   "session's green laps for both drivers combined + the field.")
        try:
            res = mdl.evaluate_laptime_model(laps_all).to_dict()
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Baseline MAE (s)", res["baseline_mae"])
            mc2.metric("Model MAE (s)", res["model_mae"])
            mc3.metric("MAE improvement", f"{res['improvement_mae_pct']}%")
            if res["degradation"]:
                st.plotly_chart(viz.degradation_bar(res["degradation"]), use_container_width=True)
                st.dataframe(pd.DataFrame(res["degradation"]), use_container_width=True, hide_index=True)
            with st.expander("Methodology & limitations"):
                st.write(f"Features: {', '.join(res['features'][:6])} … ({len(res['features'])} total)")
                st.write(f"Train laps: {res['n_train']} · Test laps: {res['n_test']}")
                for n in res["notes"]:
                    st.write(f"- {n}")
        except ValueError as exc:
            st.info(f"Not enough green laps in this session to fit the model: {exc}")


def _pick_lap(container, laps, driver: str, key: str):
    """Sidebar lap picker on a FastF1 Laps object; defaults to the driver's fastest lap."""
    laps = laps.dropna(subset=["LapTime"])
    if laps.empty:
        return None
    options = ["Fastest"] + [f"Lap {int(n)}" for n in laps["LapNumber"]]
    choice = container.selectbox(f"{driver} lap", options, key=f"lap_{key}")
    if choice == "Fastest":
        return laps.pick_fastest()
    lap_no = int(choice.split()[1])
    sub = laps[laps["LapNumber"] == lap_no]
    return sub.iloc[0] if len(sub) else laps.pick_fastest()


if __name__ == "__main__":
    main()
