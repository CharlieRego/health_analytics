"""Expected-vs-actual model for the 4-hour ED target.

Phase 2 (evaluation): python -m pipeline.ml_expected

Compares two simple baselines with two models. Every hospital-year is predicted
by a model that never saw that hospital: GroupKFold splits by hospital, so all
of a hospital's years sit in the same fold. Score = mean absolute error (MAE)
in percentage points.
"""
import logging

import numpy as np
import pandas as pd
import psycopg
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from .config import db_dsn

log = logging.getLogger("pipeline.ml_expected")

TARGET = "pct_within_4h"
NUMERIC = [
    "log_ed_presentations",
    "share_resus_emergency",
    "share_non_urgent",
    "share_admitted",
    "fy_start_year",
    "covid_period",
]
WITH_STATE = ["state", "peer_group_name"]
NO_STATE = ["peer_group_name"]
NO_PEER_GROUP = {"Not peered", "Unpeered"}
FOLDS = GroupKFold(n_splits=5)


# ── Data ────────────────────────────────────────────────────────────────────

def load_features(conn) -> pd.DataFrame:
    """One row per hospital-year from marts.ml_ed_features."""
    cur = conn.execute("select * from marts.ml_ed_features order by reporting_unit_code, fy_start_year")
    df = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
    for col in [TARGET, "ed_presentations", *NUMERIC]:
        df[col] = df[col].astype(float)          # Postgres numeric arrives as Decimal
    for col in ["state", "peer_group_name", "reporting_unit_code"]:
        df[col] = df[col].astype(object)
    return df.reset_index(drop=True)


# ── Baselines: simple averages from the training hospitals only ─────────────

def state_year_average(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Average of training hospitals in the same state and year (else the year's average)."""
    by_state_year = train.groupby(["state", "fy_start_year"])[TARGET].mean()
    pred = by_state_year.reindex(pd.MultiIndex.from_frame(test[["state", "fy_start_year"]])).to_numpy()
    year_avg = test["fy_start_year"].map(train.groupby("fy_start_year")[TARGET].mean()).to_numpy()
    return np.where(np.isnan(pred), year_avg, pred)


def peer_year_average(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Average of training hospitals in the same peer group and year.
    Hospitals without a peer group fall back to the state-and-year average."""
    peered = train[~train["peer_group_name"].isin(NO_PEER_GROUP)]
    by_peer_year = peered.groupby(["peer_group_name", "fy_start_year"])[TARGET].mean()
    pred = by_peer_year.reindex(
        pd.MultiIndex.from_frame(test[["peer_group_name", "fy_start_year"]])
    ).to_numpy()
    return np.where(np.isnan(pred), state_year_average(train, test), pred)


# ── Models ──────────────────────────────────────────────────────────────────

def ridge(categorical: list[str]):
    """Linear regression with regularisation; strength chosen by internal CV."""
    prep = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
    ])
    return make_pipeline(prep, RidgeCV(alphas=np.logspace(-3, 3, 13)))


def boosting(categorical: list[str]):
    """Gradient-boosted trees; picks up curves and interactions a line can't."""
    prep = ColumnTransformer([
        ("num", "passthrough", NUMERIC),
        ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1,
                               encoded_missing_value=-1), categorical),
    ])
    cat_idx = list(range(len(NUMERIC), len(NUMERIC) + len(categorical))) or None
    model = HistGradientBoostingRegressor(
        categorical_features=cat_idx, max_iter=300, learning_rate=0.05,
        min_samples_leaf=20, random_state=0,
    )
    return make_pipeline(prep, model)


def model_method(factory, categorical: list[str]):
    """Wrap a model so it has the same fit-and-predict shape as the baselines."""
    cols = NUMERIC + categorical

    def fit_predict(train, test):
        return factory(categorical).fit(train[cols], train[TARGET]).predict(test[cols])
    return fit_predict


METHODS = {
    "Baseline: state and year average": state_year_average,
    "Baseline: peer group and year average": peer_year_average,
    "Ridge, with state": model_method(ridge, WITH_STATE),
    "Ridge, without state": model_method(ridge, NO_STATE),
    "Gradient boosting, with state": model_method(boosting, WITH_STATE),
    "Gradient boosting, without state": model_method(boosting, NO_STATE),
}


# ── Evaluation ──────────────────────────────────────────────────────────────

def out_of_fold(df: pd.DataFrame, fit_predict) -> np.ndarray:
    """Predict every row with a model trained on the other hospitals only."""
    pred = np.full(len(df), np.nan)
    for train_idx, test_idx in FOLDS.split(df, groups=df["reporting_unit_code"]):
        pred[test_idx] = fit_predict(df.iloc[train_idx], df.iloc[test_idx])
    return pred


def score_table(df: pd.DataFrame, methods: dict) -> tuple[pd.DataFrame, dict]:
    rows, preds = [], {}
    qld = (df["state"] == "Qld").to_numpy()
    for name, method in methods.items():
        pred = out_of_fold(df, method)
        preds[name] = pred
        rows.append({
            "method": name,
            "MAE (pts)": mean_absolute_error(df[TARGET], pred),
            "MAE Qld (pts)": mean_absolute_error(df.loc[qld, TARGET], pred[qld]),
            "R2": r2_score(df[TARGET], pred),
        })
    return pd.DataFrame(rows).set_index("method").round(2), preds


def importance(df: pd.DataFrame, factory, categorical: list[str]) -> pd.Series:
    """How much worse MAE gets when one input is shuffled (on held-out hospitals)."""
    cols = NUMERIC + categorical
    totals = pd.Series(0.0, index=cols)
    for train_idx, test_idx in FOLDS.split(df, groups=df["reporting_unit_code"]):
        train, test = df.iloc[train_idx], df.iloc[test_idx]
        model = factory(categorical).fit(train[cols], train[TARGET])
        result = permutation_importance(
            model, test[cols], test[TARGET], scoring="neg_mean_absolute_error",
            n_repeats=5, random_state=0,
        )
        totals += pd.Series(result.importances_mean, index=cols)
    return (totals / FOLDS.get_n_splits()).sort_values(ascending=False).round(2)


def with_resus_fill(df: pd.DataFrame, fill: int) -> pd.DataFrame:
    """Redo the "<5" resuscitation fill with another value (the table uses 2)."""
    out = df.copy()
    shift = (fill - 2) / out["ed_presentations"]
    out.loc[out["resus_filled"], "share_resus_emergency"] += shift[out["resus_filled"]]
    return out


def evaluate(df: pd.DataFrame) -> None:
    pd.set_option("display.width", 120)
    print(f"\nRows: {len(df)} hospital-years, {df['reporting_unit_code'].nunique()} hospitals, "
          f"financial years starting {int(df['fy_start_year'].min())} to {int(df['fy_start_year'].max())}")

    table, preds = score_table(df, METHODS)
    print("\n== Main results (out-of-fold, unseen hospitals) ==")
    print(table.to_string())

    best = table.drop(index=[m for m in table.index if m.startswith("Baseline")])["MAE (pts)"].idxmin()
    print(f"\nBest model: {best}")

    print("\n== Sensitivity: without the COVID years (2019-20 to 2021-22) ==")
    no_covid = df[df["covid_period"] == 0].reset_index(drop=True)
    print(score_table(no_covid, {k: METHODS[k] for k in
                                 ["Baseline: state and year average", best]})[0].to_string())

    print('\n== Sensitivity: "<5" resuscitation counts filled with 0 or 4 instead of 2 ==')
    for fill in (0, 4):
        t = score_table(with_resus_fill(df, fill), {best: METHODS[best]})[0]
        print(f"fill={fill}: MAE {t.loc[best, 'MAE (pts)']}")

    factory = ridge if best.startswith("Ridge") else boosting
    categorical = WITH_STATE if best.endswith("with state") else NO_STATE
    print(f"\n== What drives it: MAE increase when each input is shuffled ({best}) ==")
    print(importance(df, factory, categorical).to_string())

    print("\n== Check: Toowoomba, last 3 years ==")
    check = df.assign(expected=preds[best].round(1))
    check = check[check["reporting_unit_name"].str.startswith("Toowoomba")]
    print(check[["period_label", TARGET, "expected"]].tail(3).to_string(index=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with psycopg.connect(db_dsn()) as conn:
        features = load_features(conn)
    evaluate(features)
