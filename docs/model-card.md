# Model card: expected vs actual ED performance

## What it does

For each Australian public hospital and financial year, the model estimates the **expected** share of emergency department (ED) patients who leave within 4 hours, given the hospital's size and patient mix. **Actual minus expected** shows which hospitals do better or worse than similar hospitals. A funnel plot then separates hospitals that are clearly unusual from normal year-to-year variation.

The question it answers: *"Given its size and patient mix, how should this hospital perform on the 4-hour target, and is it doing better or worse than that?"*

## Intended use

- **Where to look.** A starting point for questions, such as "Redland was 15 points above expected in 2024-25: what are they doing?" or "this hospital fell below expected: why?".
- **A fairer comparison than a league table.** A small rural hospital and a major city hospital are each compared with what's expected for a hospital like them.

## Not for

- **Judging quality or performance.** Public data has no patient-level detail (age, diagnosis, time of day, staffing, bed availability). A gap between actual and expected shows where to look, not who is failing.
- **Explaining causes.** The admitted share and patient urgency *predict* the 4-hour result; that doesn't prove they *cause* it.
- **Forecasting next year.** It describes a hospital-year after the fact. It isn't a forecast (see Limits).
- **Individual patients.** It works on hospital-level yearly totals only.

## Data

- **Source:** AIHW MyHospitals API (CC BY 3.0 AU), loaded weekly by this pipeline. Annual data, 2011-12 to 2024-25.
- **Rows:** 3,855 hospital-years from 311 public hospitals (29 in Queensland), from `marts.ml_ed_features`. 20 hospital-years were dropped because the 4-hour value wasn't published.
- **Target:** % of all ED patients leaving within 4 hours (`MYH-RM0015`).
- **Suppressed counts:** patient counts published as "<5" are filled with 2. Filling with 0 or 4 instead changes the error by at most 0.05 points.

## Inputs

| Input | Why |
|---|---|
| ED presentations (log) | Size and demand |
| Share resuscitation + emergency | Sicker patients take longer |
| Share non-urgent | Quick cases raise the 4-hour figure |
| Share subsequently admitted | Admitted patients wait for a ward bed |
| State | States count and run EDs differently |
| Peer group (AIHW) | Hospital type, where AIHW assigns one |
| Financial year, COVID flag | The long-term trend and the pandemic years |

**Deliberately left out:** median time in ED and 90th-percentile time in ED. They measure the same patients' stays as the target, so they would make the model look accurate without explaining anything (leakage).

## Model and validation

- **Model:** gradient-boosted trees (scikit-learn `HistGradientBoostingRegressor`), chosen over a regularised linear model (Ridge) and two simple baselines.
- **Validation:** 5-fold cross-validation **grouped by hospital**. Every hospital-year is predicted by a model that never saw that hospital, in any year. Splitting by row instead would let the model recognise a hospital from its other years and look better than it is.
- **Expected values in the results are out-of-fold:** each one comes from a model that didn't train on that hospital.

## Accuracy

Mean absolute error in percentage points, on hospitals the model never saw:

| Method | All hospitals | Queensland |
|---|---|---|
| Baseline: state and year average | 10.75 | 7.48 |
| Baseline: peer group and year average | 7.42 | 5.96 |
| Ridge (linear), with state | 5.67 | 6.46 |
| **Gradient boosting, with state** | **4.68** | **5.00** |

- R² = 0.84. Without the COVID years: 4.83, so the pandemic years don't flatter it.
- **What drives it** (how much worse the error gets when one input is shuffled): hospital size 5.4 points, year 2.1, resuscitation + emergency share 0.9, state 0.9, peer group 0.8, non-urgent share 0.5, admitted share 0.4, COVID flag 0.0. Inputs that move together (size and admitted share) share the credit, so these are a ranking, not exact effects.

## Flags (funnel plot)

- Residual = actual − expected. Limits at 95% and 99.8% use the binomial standard error **plus** the normal hospital-to-hospital spread (tau = 4.7 points; Spiegelhalter 2005). Without that spread, every large hospital would be flagged.
- Hospital-years outside 99.8% are flagged "well above expected" or "well below expected": 106 of 3,855 (2.7%). In 2024-25, 9 above and 6 below out of 292.
- The limits fit loosely: 13% of hospital-years fall outside the 95% limits, where about 5% would be a perfect fit. That's why flags use 99.8%.
- Example: Toowoomba 2024-25, 44% actual vs 44.4% expected, inside the limits (every year since 2011-12 is inside).

## Limits

- **One number per hospital per year.** It can't see within-year changes, or anything the AIHW doesn't publish.
- **Size dominates.** The model mostly learns that bigger EDs struggle more with the 4-hour target. Patient mix adds a little; much of what drives ED flow (beds, staffing, community services) isn't in the data.
- **No per-hospital forecast.** 14 yearly points per hospital is too few to forecast each one; the model pools all hospitals instead. A next-year early warning (Phase 6) would need its own test against "same as last year".
- **Peer group comes from the latest period** and doesn't change by year.

## How it runs

- **Code:** `pipeline/ml_expected.py`. Features: `dbt/models/marts/ml_ed_features.sql`. Comparison of all methods: `python -m pipeline.ml_expected`.
- **In the pipeline:** with `ML_ENABLED=1`, the weekly run retrains only when the AIHW data version changes (about once a year). Results go to `marts.ml_ed_expected` in one transaction, with a row in `audit.model_runs` (data version, model version, model and baseline error, flags), and dbt tests check the output.
- **Decisions and history:** `docs/decisions.md` and `docs/devlog.md` (27 Oct 2026).
