"""Network-free tests for the modeling component, using synthetic degradation data."""
import numpy as np
import pandas as pd

from src import modeling as mdl
from src import telemetry_analysis as ta


def _degrading_laps(n_per=25, slope=0.05, base=90.0):
    """Two compounds with a known lap-time-vs-tyre-life slope, plus mild noise."""
    rng = np.random.default_rng(1)
    rows = []
    for stint, (comp, off) in enumerate([("MEDIUM", 0.0), ("HARD", 0.6)], start=1):
        for age in range(1, n_per + 1):
            lt = base + off + slope * age + rng.normal(0, 0.1)
            rows.append(
                {
                    "LapTime": pd.to_timedelta(lt, unit="s"),
                    "LapNumber": len(rows) + 1,
                    "Compound": comp,
                    "TyreLife": float(age),
                    "Stint": stint,
                    "Driver": "AAA",
                    "Sector1Time": pd.to_timedelta(lt * 0.33, unit="s"),
                    "Sector2Time": pd.to_timedelta(lt * 0.33, unit="s"),
                    "Sector3Time": pd.to_timedelta(lt * 0.34, unit="s"),
                    "IsAccurate": True,
                }
            )
    return pd.DataFrame(rows)


def test_tyre_degradation_recovers_slope():
    deg = mdl.tyre_degradation(_degrading_laps(slope=0.05))
    assert len(deg) == 2
    for d in deg:
        # recovered slope should be close to the injected 0.05 s/lap
        assert abs(d.slope_s_per_lap - 0.05) < 0.02
        assert d.r_squared > 0.5


def test_model_beats_baseline():
    res = mdl.evaluate_laptime_model(_degrading_laps()).to_dict()
    assert res["model_mae"] < res["baseline_mae"]
    assert res["n_train"] > 0 and res["n_test"] > 0
    assert res["improvement_mae_pct"] > 0
    assert res["notes"]  # limitations are reported


def test_sector_deltas_sign():
    a = pd.Series({"Sector1Time": pd.to_timedelta(30, "s"), "Sector2Time": pd.to_timedelta(30, "s"),
                   "Sector3Time": pd.to_timedelta(30, "s")})
    b = pd.Series({"Sector1Time": pd.to_timedelta(31, "s"), "Sector2Time": pd.to_timedelta(29, "s"),
                   "Sector3Time": pd.to_timedelta(30, "s")})
    sd = ta.sector_deltas(a, b)
    assert round(sd.loc[sd["Sector"] == "S1", "Delta"].iloc[0], 3) == 1.0   # B slower in S1
    assert round(sd.loc[sd["Sector"] == "S2", "Delta"].iloc[0], 3) == -1.0  # B faster in S2


def test_delta_time_zero_for_identical_laps():
    tel = pd.DataFrame({"Distance": np.arange(0, 1000, 10.0), "Speed": np.full(100, 200.0)})
    d = ta.delta_time(tel, tel.copy())
    assert abs(d["DeltaTime"].iloc[-1]) < 1e-6
