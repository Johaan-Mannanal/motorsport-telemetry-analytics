"""Motorsport Telemetry Analytics — Streamlit dashboard.

Compare two drivers' fastest laps from a Formula 1 session: speed/throttle/brake/gear traces,
delta time, sector deltas, a track-position map, tyre strategy, weather, and a transparent
tyre-degradation / lap-time model.

The hosted demo uses a few bundled sample sessions because the F1 data service blocks many cloud
hosts. Running locally, you can also load any live session (2018+) via FastF1.

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
from src import visualizations as viz

st.set_page_config(page_title="Motorsport Telemetry Analytics", layout="wide", page_icon="🏁")

SESSION_CODES = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3",
                 "Qualifying": "Q", "Sprint": "S", "Race": "R"}


@st.cache_resource(show_spinner=False)
def _sample(slug: str):
    return sd.load_sample(slug)


@st.cache_resource(show_spinner=True)
def _live(year: int, event: str, code: str):
    return dl.load_session(year, event, code)


def choose_session():
    """Sidebar session picker. Bundled samples by default; live loading is opt-in."""
    st.sidebar.header("Session")
    samples = sd.list_samples()
    labels = [s["label"] for s in samples]
    pick = st.sidebar.selectbox("Example session", labels, index=0)
    slug = samples[labels.index(pick)]["slug"]

    with st.sidebar.expander("Or load a live session (local only)"):
        st.caption("Requires network access to the F1 data service, which is blocked on the "
                   "hosted demo. Works when you run the app locally.")
        use_live = st.checkbox("Use a live session instead")
        year = st.selectbox("Season", list(range(2024, 2017, -1)), index=1)
        event = st.text_input("Race (e.g. Monza, Silverstone)", "Monza")
        code = SESSION_CODES[st.selectbox("Session", list(SESSION_CODES), index=5)]

    if use_live:
        try:
            return _live(year, event, code)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not load live session: {exc}")
            st.info("Falling back to the selected example session.")
    return _sample(slug)


def main() -> None:
    st.title("Motorsport Telemetry Analytics")
    st.caption("Interactive Formula 1 telemetry and race-performance analysis. Public data via "
               "FastF1. Unofficial; not affiliated with Formula 1.")

    session = choose_session()
    event_name = getattr(session, "event_name", None) or "Session"
    drivers = dl.session_drivers(session)
    if len(drivers) < 2:
        st.warning("This session has fewer than two drivers with lap data.")
        st.stop()

    st.subheader(getattr(session, "label", event_name))
    c1, c2 = st.sidebar.columns(2)
    drv_a = c1.selectbox("Driver A", drivers, index=0)
    drv_b = c2.selectbox("Driver B", drivers, index=min(1, len(drivers) - 1))

    laps_all = dl.session_laps(session)
    laps_a = pp.clean_laps(dl.driver_laps(session, drv_a))
    laps_b = pp.clean_laps(dl.driver_laps(session, drv_b))
    row_a = dl.fastest_lap_row(session, drv_a)
    row_b = dl.fastest_lap_row(session, drv_b)

    # Fastest-lap summary
    m1, m2, m3 = st.columns(3)
    ta_a = ta.fastest_lap_summary(laps_a, drv_a)
    ta_b = ta.fastest_lap_summary(laps_b, drv_b)
    m1.metric(f"{drv_a} fastest lap (s)", ta_a["lap_time_s"])
    m2.metric(f"{drv_b} fastest lap (s)", ta_b["lap_time_s"])
    if ta_a["lap_time_s"] and ta_b["lap_time_s"]:
        m3.metric("Gap (B − A)", f"{ta_b['lap_time_s'] - ta_a['lap_time_s']:+.3f}")

    tabs = st.tabs(["Lap comparison", "Telemetry", "Track & sectors", "Tyres & weather", "Model"])

    with tabs[0]:
        st.plotly_chart(viz.laptime_comparison(laps_a, laps_b, drv_a, drv_b), use_container_width=True)
        st.caption("Lap time by lap number (green representative laps).")

    with tabs[1]:
        st.caption("Comparing each driver's fastest lap on a shared distance axis.")
        try:
            tel_a = dl.fastest_car_telemetry(session, drv_a)
            tel_b = dl.fastest_car_telemetry(session, drv_b)
            st.plotly_chart(viz.delta_time_trace(ta.delta_time(tel_a, tel_b), drv_a, drv_b),
                            use_container_width=True)
            for ch in ("Speed", "Throttle", "Brake", "nGear"):
                st.plotly_chart(viz.channel_trace(ta.channel_comparison(tel_a, tel_b, ch), ch, drv_a, drv_b),
                                use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.info(f"Telemetry unavailable for this pairing: {exc}")

    with tabs[2]:
        try:
            pos_a = dl.fastest_position(session, drv_a)
            st.plotly_chart(viz.track_position_map(pos_a, pos_a.get("Speed"), f"{drv_a} fastest lap — speed"),
                            use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.info(f"Track map unavailable: {exc}")
        if row_a is not None and row_b is not None:
            st.plotly_chart(viz.sector_delta_bar(ta.sector_deltas(row_a, row_b), drv_a, drv_b),
                            use_container_width=True)

    with tabs[3]:
        cA, cB = st.columns(2)
        cA.subheader(f"{drv_a} stints"); cA.dataframe(pp.stint_summary(laps_a), use_container_width=True, hide_index=True)
        cB.subheader(f"{drv_b} stints"); cB.dataframe(pp.stint_summary(laps_b), use_container_width=True, hide_index=True)
        wx = viz.weather_summary_table(dl.session_weather(session))
        if not wx.empty:
            st.subheader("Weather (session average)")
            st.dataframe(wx, use_container_width=True, hide_index=True)

    with tabs[4]:
        st.subheader("Tyre-degradation & lap-time model")
        st.caption("A transparent baseline comparison on this session's green laps, not a "
                   "race-strategy oracle. See methodology and limitations below.")
        try:
            res = mdl.evaluate_laptime_model(laps_all).to_dict()
            k1, k2, k3 = st.columns(3)
            k1.metric("Baseline MAE (s)", res["baseline_mae"])
            k2.metric("Model MAE (s)", res["model_mae"])
            k3.metric("MAE improvement", f"{res['improvement_mae_pct']}%")
            if res["degradation"]:
                st.plotly_chart(viz.degradation_bar(res["degradation"]), use_container_width=True)
                st.dataframe(pd.DataFrame(res["degradation"]), use_container_width=True, hide_index=True)
            with st.expander("Methodology & limitations"):
                st.write(f"Train laps: {res['n_train']} · Test laps: {res['n_test']} · "
                         f"{len(res['features'])} features")
                for n in res["notes"]:
                    st.write(f"- {n}")
        except ValueError as exc:
            st.info(f"Not enough green laps in this session to fit the model: {exc}")


if __name__ == "__main__":
    main()
