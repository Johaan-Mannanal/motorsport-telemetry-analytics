"""Load Formula 1 session data via FastF1, with local caching.

All data is public F1 timing/telemetry fetched by FastF1 and cached locally. This module is a
thin, typed wrapper that centralizes cache setup and the handful of loads the app needs.
"""
from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Optional

import pandas as pd

import fastf1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = REPO_ROOT / "data" / "cache"

_cache_enabled = False


def enable_cache(cache_dir: Optional[str | Path] = None) -> Path:
    """Enable FastF1's on-disk cache (idempotent).

    Parameters
    ----------
    cache_dir:
        Directory for the cache. Defaults to ``FASTF1_CACHE_DIR`` env var or ``data/cache``.

    Returns
    -------
    Path
        The cache directory that was enabled.
    """
    global _cache_enabled
    path = Path(cache_dir or os.getenv("FASTF1_CACHE_DIR") or DEFAULT_CACHE)
    path.mkdir(parents=True, exist_ok=True)
    if not _cache_enabled:
        fastf1.Cache.enable_cache(str(path))
        _cache_enabled = True
    return path


def get_event_schedule(year: int) -> pd.DataFrame:
    """Return the event schedule for a season (round, event name, country, dates)."""
    enable_cache()
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule


def list_events(year: int) -> list[str]:
    """Return a list of event names for a season, in round order."""
    schedule = get_event_schedule(year)
    return [str(name) for name in schedule["EventName"].tolist()]


@functools.lru_cache(maxsize=32)
def load_session(year: int, event: str, session: str) -> "fastf1.core.Session":
    """Load a fully-populated FastF1 session (laps, telemetry, weather, results).

    Parameters
    ----------
    year:
        Season, e.g. ``2023``.
    event:
        Event name or round number understood by FastF1 (e.g. ``"Monza"``).
    session:
        Session code: ``"FP1"``, ``"FP2"``, ``"FP3"``, ``"Q"``, ``"S"`` (sprint), ``"R"``.

    Returns
    -------
    fastf1.core.Session
        A loaded session object.

    Raises
    ------
    ValueError
        If the year is implausible or the session cannot be identified.
    """
    if year < 2018 or year > 2100:
        raise ValueError(f"year {year} is outside the supported range (FastF1 telemetry from 2018).")
    enable_cache()
    try:
        sess = fastf1.get_session(year, event, session)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the app
        raise ValueError(f"Could not find session '{session}' for {event} {year}: {exc}") from exc
    sess.load(laps=True, telemetry=True, weather=True, messages=False)
    return sess


def get_drivers(session) -> list[str]:
    """Return the driver abbreviations present in a loaded session (e.g. ['VER', 'HAM'])."""
    laps = session.laps
    if laps is None or laps.empty:
        return []
    return sorted(laps["Driver"].dropna().unique().tolist())


def driver_laps(session, driver: str) -> pd.DataFrame:
    """Return all laps for a single driver as a plain DataFrame."""
    return session.laps.pick_drivers(driver).reset_index(drop=True)
