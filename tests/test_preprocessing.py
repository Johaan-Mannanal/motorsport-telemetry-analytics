"""Network-free tests for preprocessing helpers, using synthetic lap frames."""
import numpy as np
import pandas as pd
import pytest

from src import preprocessing as pp


def _synthetic_laps(n=30, base=90.0):
    rng = np.random.default_rng(0)
    times = base + rng.normal(0, 0.3, n)
    times[0] += 20  # out-lap style outlier
    return pd.DataFrame(
        {
            "LapTime": pd.to_timedelta(times, unit="s"),
            "LapNumber": np.arange(1, n + 1),
            "Sector1Time": pd.to_timedelta(times * 0.3, unit="s"),
            "Sector2Time": pd.to_timedelta(times * 0.4, unit="s"),
            "Sector3Time": pd.to_timedelta(times * 0.3, unit="s"),
            "Compound": ["MEDIUM"] * n,
            "TyreLife": np.arange(1, n + 1).astype(float),
            "Stint": [1] * n,
            "IsAccurate": [True] * n,
        }
    )


def test_to_seconds():
    s = pp.to_seconds(pd.to_timedelta([60.0, 90.5], unit="s"))
    assert s.tolist() == [60.0, 90.5]


def test_clean_laps_adds_numeric_and_drops_na():
    laps = _synthetic_laps()
    laps.loc[5, "LapTime"] = pd.NaT
    out = pp.clean_laps(laps)
    assert "LapTimeSeconds" in out.columns
    assert "Sector1Seconds" in out.columns
    assert out["LapTimeSeconds"].isna().sum() == 0
    assert len(out) == len(laps) - 1  # the NaT lap dropped


def test_representative_laps_removes_outlier():
    laps = pp.clean_laps(_synthetic_laps())
    rep = pp.representative_laps(laps)
    assert rep["LapTimeSeconds"].max() < laps["LapTimeSeconds"].max()  # 20s outlier gone
    assert len(rep) >= 20


def test_stint_summary():
    out = pp.stint_summary(_synthetic_laps())
    assert list(out.columns) == ["Stint", "Compound", "Laps", "StartLap", "EndLap"]
    assert out.iloc[0]["Compound"] == "MEDIUM"


def test_align_telemetry_requires_distance():
    with pytest.raises(ValueError):
        pp.align_telemetry_on_distance(pd.DataFrame({"Speed": [1, 2, 3]}))
