"""Tyre-degradation estimation and a lap-time model, with an honest baseline comparison.

The goal is a *transparent* data-science component, not a race-strategy oracle. We:

1. Estimate tyre degradation as the slope of lap time vs. tyre age (seconds lost per lap of
   tyre life), per compound, from green representative laps.
2. Fit a simple, interpretable lap-time model (linear regression on tyre life, a fuel-burn
   proxy, compound, and driver) and compare it against a naive baseline (predict the mean lap
   time) on a held-out test split, reporting MAE and RMSE.

Limitations are reported alongside the numbers; see :func:`evaluate_laptime_model`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from .preprocessing import representative_laps

RANDOM_SEED = 42


@dataclass
class DegradationResult:
    """Per-compound tyre-degradation estimate."""

    compound: str
    slope_s_per_lap: float
    r_squared: float
    n_laps: int


@dataclass
class LapTimeModelResult:
    """Held-out comparison of the lap-time model vs. the mean-lap-time baseline."""

    features: list[str]
    n_train: int
    n_test: int
    baseline_mae: float
    baseline_rmse: float
    model_mae: float
    model_rmse: float
    degradation: list[DegradationResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "features": self.features,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "baseline_mae": round(self.baseline_mae, 3),
            "baseline_rmse": round(self.baseline_rmse, 3),
            "model_mae": round(self.model_mae, 3),
            "model_rmse": round(self.model_rmse, 3),
            "improvement_mae_pct": round(100 * (1 - self.model_mae / self.baseline_mae), 1)
            if self.baseline_mae
            else None,
            "degradation": [
                {
                    "compound": d.compound,
                    "slope_s_per_lap": round(d.slope_s_per_lap, 4),
                    "r_squared": round(d.r_squared, 3),
                    "n_laps": d.n_laps,
                }
                for d in self.degradation
            ],
            "notes": self.notes,
        }


def tyre_degradation(laps: pd.DataFrame, min_laps: int = 6) -> list[DegradationResult]:
    """Estimate seconds-lost-per-lap of tyre life, per compound, from green laps.

    A positive slope means lap time increases (car slows) as the tyre ages. Fitted with a simple
    linear regression of lap time on tyre life within each compound.

    Parameters
    ----------
    laps:
        Raw or cleaned laps for one or more drivers.
    min_laps:
        Minimum green laps required to report a compound.
    """
    df = representative_laps(laps)
    results: list[DegradationResult] = []
    if df.empty or "Compound" not in df.columns or "TyreLife" not in df.columns:
        return results
    for compound, grp in df.dropna(subset=["TyreLife", "LapTimeSeconds"]).groupby("Compound"):
        if len(grp) < min_laps:
            continue
        x = grp["TyreLife"].to_numpy().reshape(-1, 1)
        y = grp["LapTimeSeconds"].to_numpy()
        reg = LinearRegression().fit(x, y)
        results.append(
            DegradationResult(
                compound=str(compound),
                slope_s_per_lap=float(reg.coef_[0]),
                r_squared=float(reg.score(x, y)),
                n_laps=int(len(grp)),
            )
        )
    return sorted(results, key=lambda r: r.compound)


def build_laptime_dataset(laps: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Build a feature matrix and target (lap time, s) from green laps.

    Features: tyre life, lap number (a proxy for fuel load burning off), one-hot compound, and
    one-hot driver (to absorb car/driver pace differences).
    """
    df = representative_laps(laps)
    if df.empty:
        raise ValueError("no representative green laps available to model")
    feat = pd.DataFrame(index=df.index)
    feat["TyreLife"] = df["TyreLife"].fillna(df["TyreLife"].median())
    feat["LapNumber"] = df["LapNumber"]
    compounds = pd.get_dummies(df["Compound"].astype(str), prefix="comp")
    drivers = pd.get_dummies(df["Driver"].astype(str), prefix="drv")
    feat = pd.concat([feat, compounds, drivers], axis=1)
    y = df["LapTimeSeconds"]
    return feat, y, list(feat.columns)


def evaluate_laptime_model(laps: pd.DataFrame, random_state: int = RANDOM_SEED) -> LapTimeModelResult:
    """Fit the lap-time model and compare it to a mean-lap-time baseline on a held-out split.

    Returns a :class:`LapTimeModelResult` with MAE/RMSE for both, plus per-compound degradation
    and explicit limitations. Requires enough green laps to form a train/test split.
    """
    X, y, feats = build_laptime_dataset(laps)
    if len(X) < 20:
        raise ValueError(f"not enough green laps to evaluate a model (have {len(X)}, need >= 20)")
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=random_state)

    # Baseline: predict the training mean lap time for every test lap.
    baseline_pred = np.full(len(y_te), float(y_tr.mean()))
    b_mae = mean_absolute_error(y_te, baseline_pred)
    b_rmse = float(np.sqrt(mean_squared_error(y_te, baseline_pred)))

    model = LinearRegression().fit(X_tr, y_tr)
    m_pred = model.predict(X_te)
    m_mae = mean_absolute_error(y_te, m_pred)
    m_rmse = float(np.sqrt(mean_squared_error(y_te, m_pred)))

    notes = [
        "Single-session model; coefficients describe correlation, not causation.",
        "Green-lap filter removes in/out, safety-car and traffic laps but is heuristic.",
        "Driver identity is included, so the model partly memorizes per-driver pace; it is not a "
        "generalizable cross-race predictor.",
        "Weather, track evolution, and fuel mass are only crudely proxied (lap number).",
        "Random lap split can leak within-stint correlation; treat gains as indicative.",
    ]
    return LapTimeModelResult(
        features=feats,
        n_train=int(len(X_tr)),
        n_test=int(len(X_te)),
        baseline_mae=float(b_mae),
        baseline_rmse=float(b_rmse),
        model_mae=float(m_mae),
        model_rmse=float(m_rmse),
        degradation=tyre_degradation(laps),
        notes=notes,
    )
