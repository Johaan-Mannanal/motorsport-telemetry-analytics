"""Load Formula 1 session data via FastF1, with local caching.

All data is public F1 timing/telemetry fetched by FastF1 and cached locally. This module is a
thin, typed wrapper that centralizes cache setup and the handful of loads the app needs.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd

import fastf1

_cache_enabled = False


def _default_cache_dir() -> Path:
    """Pick a writable cache directory.

    Uses ``FASTF1_CACHE_DIR`` if set, otherwise a temp dir. The repository directory can be
    read-only on hosted platforms (e.g. Streamlit Cloud), so we do not default to it.
    """
    env = os.getenv("FASTF1_CACHE_DIR")
    if env:
        return Path(env)
    return Path(tempfile.gettempdir()) / "fastf1_cache"


def enable_cache(cache_dir: Optional[str | Path] = None) -> Optional[Path]:
    """Enable FastF1's on-disk cache (idempotent, best-effort).

    The cache only speeds things up; if the target directory is not writable the function
    degrades gracefully and FastF1 fetches without a cache.

    Returns
    -------
    Path or None
        The enabled cache directory, or ``None`` if caching could not be enabled.
    """
    global _cache_enabled
    path = Path(cache_dir) if cache_dir else _default_cache_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not _cache_enabled:
            fastf1.Cache.enable_cache(str(path))
            _cache_enabled = True
        return path
    except Exception:
        return None


def get_event_schedule(year: int) -> pd.DataFrame:
    """Return the event schedule for a season (round, event name, country, dates)."""
    enable_cache()
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule


def list_events(year: int) -> list[str]:
    """Return a list of event names for a season, in round order."""
    schedule = get_event_schedule(year)
    return [str(name) for name in schedule["EventName"].tolist()]


def _laps_loaded(sess) -> bool:
    """True if the session actually has lap data (FastF1 can 'load' but fetch nothing)."""
    try:
        laps = sess.laps
    except Exception:
        return False
    return laps is not None and len(laps) > 0


def load_session(year: int, event: str, session: str, retries: int = 1) -> "fastf1.core.Session":
    """Load a fully-populated FastF1 session (laps, telemetry, weather, results).

    Parameters
    ----------
    year:
        Season, e.g. ``2023``.
    event:
        Event name or round number understood by FastF1 (e.g. ``"Monza"``).
    session:
        Session code: ``"FP1"``, ``"FP2"``, ``"FP3"``, ``"Q"``, ``"S"`` (sprint), ``"R"``.
    retries:
        Number of times to retry if the data fetch returns no laps (transient upstream failures).

    Returns
    -------
    fastf1.core.Session
        A loaded session, guaranteed to contain lap data.

    Raises
    ------
    ValueError
        If the year is out of range, the session cannot be identified, or no lap data could be
        loaded after retrying (e.g. the upstream F1 data service is unreachable or rate-limited).
    """
    if year < 2018 or year > 2100:
        raise ValueError(f"year {year} is outside the supported range (FastF1 telemetry from 2018).")
    enable_cache()
    try:
        sess = fastf1.get_session(year, event, session)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the app
        raise ValueError(f"Could not find session '{session}' for {event} {year}: {exc}") from exc

    last_exc: Optional[Exception] = None
    for _ in range(max(1, retries + 1)):
        try:
            sess.load(laps=True, telemetry=True, weather=True, messages=False)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
        if _laps_loaded(sess):
            return sess

    raise ValueError(
        f"No lap data could be loaded for {event} {year} {session}. The F1 data service may be "
        f"temporarily unreachable or rate-limited from this host. Try again shortly or pick "
        f"another session." + (f" ({last_exc})" if last_exc else "")
    )


def get_drivers(session) -> list[str]:
    """Return the driver abbreviations present in a loaded session (e.g. ['VER', 'HAM'])."""
    laps = session.laps
    if laps is None or laps.empty:
        return []
    return sorted(laps["Driver"].dropna().unique().tolist())


# --- Unified accessors -------------------------------------------------------------------
# These work for both a live FastF1 Session and a bundled offline SampleSession, so the app
# never has to branch on the data source.

def _is_sample(session) -> bool:
    """True for a bundled offline session, False for a live FastF1 session.

    Uses duck typing rather than ``isinstance``: on Streamlit Cloud the module watcher can reload
    ``src`` modules, so a cached SampleSession instance may be an instance of an older copy of the
    class and ``isinstance`` would wrongly return False. A live FastF1 session's ``.laps`` is a
    FastF1 ``Laps`` object (has ``pick_drivers``); a sample session's is a plain DataFrame.
    """
    return not hasattr(session.laps, "pick_drivers")


def session_drivers(session) -> list[str]:
    """Driver abbreviations in the session."""
    if _is_sample(session):
        return session.drivers
    return get_drivers(session)


def session_laps(session) -> pd.DataFrame:
    """All laps in the session (both backends expose ``.laps``)."""
    return session.laps


def session_weather(session) -> Optional[pd.DataFrame]:
    """Weather data for the session, or ``None``."""
    if _is_sample(session):
        return session.weather
    return getattr(session, "weather_data", None)


def fastest_car_telemetry(session, driver: str) -> pd.DataFrame:
    """Car telemetry (Distance, Speed, Throttle, Brake, nGear) for a driver's fastest lap."""
    if _is_sample(session):
        return session.fastest_car_telemetry(driver)
    return session.laps.pick_drivers(driver).pick_fastest().get_car_data().add_distance()


def fastest_position(session, driver: str) -> pd.DataFrame:
    """Track position (X, Y, Speed) for a driver's fastest lap."""
    if _is_sample(session):
        return session.fastest_position(driver)
    tel = session.laps.pick_drivers(driver).pick_fastest().get_telemetry()
    return tel[["X", "Y", "Speed"]].reset_index(drop=True)


def fastest_lap_row(session, driver: str):
    """The fastest lap (a pandas Series) for a driver, or ``None``."""
    if _is_sample(session):
        return session.fastest_lap_row(driver)
    laps = session.laps.pick_drivers(driver).dropna(subset=["LapTime"])
    return None if laps.empty else laps.pick_fastest()


def driver_laps(session, driver: str) -> pd.DataFrame:
    """Return all laps for a single driver as a plain DataFrame."""
    laps = session.laps
    if _is_sample(session):
        return laps[laps["Driver"] == driver].reset_index(drop=True)
    return laps.pick_drivers(driver).reset_index(drop=True)
