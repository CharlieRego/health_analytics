# Devlog

## Wed 21 Oct 2026
- **Ingestion fix:** first full run had failed at skip=290,000 on MYH-ES (693,110 rows) with 504 Gateway Timeouts. Fix: download one `measure_code` at a time (4 measures, deepest offset ~235k), longer retries (5/15/30/60 s). Checked the 4 measure totals add up exactly to the category total first. Also fixed the audit log showing 0 rows for a failed run that had loaded 3 categories. Both written up in `decisions.md`.
- Re-ran the load (started 11:37). ED categories skipped as already loaded (idempotency working).
- **dbt setup:** dbt 1.12.6 installed, `dbt debug` and `dbt seed` pass. Staging model, sources and tests written.
- **Marts and tests:** marts (star schema), reporting views, standard + 5 custom data-quality tests, and `dbt_audit.py` written. `dbt parse` OK.
- **Docker and scheduling:** `.dockerignore`, `Dockerfile` (with dbt), compose job and `run_pipeline.sh` written; image builds. Healthchecks.io check created (1 week period, 1 day grace).
- Next: finish MYH-ES load → run `scripts/check_ingest.sql` (record total N) → `python -m pipeline.main` (dbt build + idempotency) → Docker run → cron → data exploration (find Toowoomba's code).

### Data exploration
- **Unit types:** H Hospital (390), LHN Local Hospital Network (86), PG Peer Group (8), S State (8), NAT National (1).
- **Toowoomba Hospital: `H0439`**, peer group *Large regional hospitals*. Its LHN is **Darling Downs `LHN325`**.
- **Queensland: `Qld`** (state code is mixed case, `state = 'Qld'`, not `QLD`). **National: `NAT`**.
- **Periods:** 2011-07-01 to 2025-06-30 (financial years).
- **Duplicates:** 0 source rows with `dup_rank > 1`.
- **Measures:** ED: MYH0035/0011/0012 presentations, MYH0010 % seen on time, MYH0005 % left ED within 4 h, MYH0013 90th pct time in ED, MYH0036 median time in ED. Elective surgery: MYH0006 count, MYH0007 % waited >365 days, MYH0008 % on time, MYH0009 median wait (days).
- **"All patients" breakdowns exist only for the ED-time measures:** MYH0005 → `MYH-RM0015` (4-hour rule, best Qld headline), MYH0013 → `MYH-RM0302`, MYH0036 → `MYH-RM0300`, MYH0012 → `MYH-RM0023`.
- **MYH0010 (ED seen on time) has no "all patients" row**, only 5 triage categories (MYH-RM0035–0039). **MYH0008** only has urgency categories (MYH-RM0047 urgent, 0048 semi-urgent, 0049 non-urgent). Dashboards should pick a category, or use MYH0005 for an overall ED figure. Matters for the planned prediction model.
- Next: Power BI (connect, model, first two pages).

### Summary: marts and tests
Marts built as a star schema; 23 automated data tests incl. three-way reconciliation (API = raw = facts + duplicates: 862,030 each); results stored per run in `audit.dbt_results`. A test caught the X42 "*" caution-code misread, which is now fixed. Pipeline runs end to end in Docker; Healthchecks.io up. Next: Power BI.

## Fri 23 Oct 2026
- **Power BI:** report rebuilt with a custom theme (`powerbi/qld-hospital-theme.json`), navy slicer panel and four pages: QLD vs National, QLD Hospital comparison, Hospital profile (drill-through, opens on Toowoomba) and Data Assurance (dbt test results, reconciliation, run history). Synced slicers, page navigator, dynamic titles. The .pbix is an Import snapshot; publishing to the Power BI service is blocked by the university tenant, so refresh is manual over the SSH tunnel.

### Learnings (DAX / Power BI)
- **Blank minus a number isn't blank.** `Gap to Peer = [Reporting Unit Value] - [Peer Group Value]` returned the hospital's own value when no peer value is published (e.g. median time in ED showed a "gap" of -302 minutes). DAX treats BLANK as 0 in subtraction. Fix: only subtract when both sides exist, `IF ( NOT ISBLANK ( [Reporting Unit Value] ) && NOT ISBLANK ( [Peer Group Value] ), ... )`.
- **CALCULATE filters intersect with filters already on the visual.** A "Queensland" card copied from a "National" card went blank because the visual still filtered `reporting_unit_name = National`, and Qld AND National is nothing. Fix: `REMOVEFILTERS ( dim_reporting_unit )` inside the measure before setting `reporting_unit_code = "Qld"`.
- **Matrix parent rows always show a total when collapsed**, even with row subtotals off, so averaging different breakdowns gave a wrong headline (46% instead of 44%). Fix: matrix-only measures wrapped in `IF ( ISINSCOPE ( dim_measure[reported_measure_name] ), ... )`.
- **Drill-through "Keep all filters"** carried page 2's Period = 2024-25 slicer onto the profile page, so the trend chart showed one year. Turned it off; the state lived in the Desktop session, not the saved file (checked by unzipping the .pbix and reading the page JSON).
- Power BI names are case-insensitive: a measure called `Value` clashes with the `value` column.

### Summary: export, README and going public
- **Export:** PDF export (`powerbi/qld-hospital-performance.pdf`) and page screenshots (`docs/images/01–05`). Dashboard numbers checked against SQL (Qld 50% vs national 53% on the 4-hour measure, hospital gaps, Toowoomba matrix, 26 Qld hospitals reporting). Healthchecks screenshot cropped so the ping URL isn't public.
- **README and publishing:** full README (architecture, how it works, data-quality controls, dashboard, findings, limitations). Secrets check over the whole git history: clean. `powerbi_reader` confirmed read-only (reads marts, denied raw). Repo made public. Architecture diagram rendered to `docs/images/architecture.png` (source `architecture.mmd`). Backfilled five foundation decisions in `decisions.md` (localhost + SSH tunnel, raw JSONB, COPY, double-load guards, Import snapshot).
- Next: dashboard polish (suppressed-share chart, amber "warn" status, Toowoomba summary text) → restore test from a real backup (Sat) → check the first scheduled Monday 03:00 run.

### Restore test
- Restored the 02:30 backup (68 MB) into a temporary database in 43 s. All 11 tables and views matched the live row counts (862,030 in raw, staging and the fact table), the fact-table checksum matched, and `powerbi_reader` kept its access (marts yes, raw no). Temporary database dropped afterwards.
- Now repeatable with one command: `scripts/restore_test.sh` (exits non-zero on any mismatch).
- Backups sit on the same server, so they cover bad loads and mistakes but not losing the server itself. An off-site copy is a later improvement.

## Sat 24 Oct 2026
### Live status panel (publishing side)
- `scripts/publish_status.sh` pushes `status/status.json` to a `status` branch after every run, success or failure; `run_pipeline.sh` calls it after the Healthchecks ping and a publishing error never fails the run.
- Next: status bar on the website project page, then confirm Monday's 03:00 run publishes on its own.

### Dashboard polish
- Power BI: question titles with dynamic subtitles, Gap vs Peer coloured by each measure's direction (`M vs Peer Colour`), "warn" checks in amber, a self-writing hospital summary on the profile page (`Profile Summary`), and a "How much of the data is unavailable?" chart on Data Assurance (36% of all results are suppressed; 67% for the >365-day elective surgery wait). Refreshed to the 24 Oct run; PDF and README screenshots re-exported.
- Learning: the matrix-only `M …` measures return blank outside the matrix (their ISINSCOPE guard), so the summary card works out the latest year itself with CALCULATE.
- The working .pbix now lives only at `powerbi/qld-hospital-performance.pbix` (no second copy at the repo root).

## Tue 27 Oct 2026
- First scheduled Monday 03:00 run (26 Oct) succeeded on its own: dbt PASS=30, status published to the `status` branch, and `dashboard_reader` still read the marts after the rebuild.
- Moved the live dashboard prototypes to a private archive; the public repo keeps main + status.

### Expected-vs-actual ED model: features (Phase 1)
- `marts.ml_ed_features`: one row per hospital and financial year with the target (% leaving ED within 4 hours, `MYH-RM0015`) and the inputs: log of ED presentations, resuscitation + emergency share, non-urgent share, admitted share, state, year, COVID flag, peer group.
- 3,855 hospital-years from 311 hospitals (29 in Queensland), out of 3,875. The 20 dropped have no published 4-hour value. 563 resuscitation counts were "<5" and are filled with 2 rather than dropped. 36 rows carry the caution flag and are kept.
- 10 dbt tests: one row per hospital-year, target 0–100, shares 0–1, presentations > 0. All pass.
- Check: Toowoomba 2024-25 = 44% within 4 hours, the same as the Power BI report.
- Next: Phase 2, baselines vs Ridge vs gradient boosting, scored on hospitals the model has never seen.

### Expected-vs-actual ED model: baselines vs models (Phase 2)
- `pipeline/ml_expected.py` (run with `python -m pipeline.ml_expected`). Every hospital-year is predicted by a model that never saw that hospital (`GroupKFold` by hospital, 5 folds); baselines are averaged from the training hospitals only. Added `pandas` and `scikit-learn`. `ml_ed_features` gained a `resus_filled` flag for the sensitivity check.
- Results, mean absolute error in percentage points (3,855 hospital-years, 311 hospitals):

  | Method | MAE | MAE Qld | R² |
  |---|---|---|---|
  | Baseline: state and year average | 10.75 | 7.48 | 0.29 |
  | Baseline: peer group and year average | 9.20 | 6.52 | 0.46 |
  | Ridge, with state | 6.09 | 6.92 | 0.75 |
  | Ridge, without state | 6.28 | 7.92 | 0.73 |
  | **Gradient boosting, with state** | **4.81** | **5.34** | **0.83** |
  | Gradient boosting, without state | 5.40 | 7.31 | 0.79 |

- Sensitivity: without the COVID years 4.87 (vs baseline 10.94), so the pandemic years don't flatter it. Filling "<5" resuscitation counts with 0 or 4 instead of 2: MAE 4.81 both times, so the fill doesn't matter.
- What drives it (MAE increase when an input is shuffled): hospital size 6.8 pts, year 2.0, resuscitation + emergency share 0.9, state 0.9, admitted share 0.5, non-urgent share 0.4, peer group 0.1, COVID flag 0.0. Size dominates; the admitted share matters less than expected, probably because it moves with size (shuffling splits credit between related inputs).
- Check: Toowoomba 2024-25 actual 44% vs expected 46.4% (2.4 points below expected); 2022-23 was 10.5 points above.
- Learning: Ridge is worse than the peer-group baseline for Queensland (6.92 vs 6.52) even though it's far better nationally; only boosting beats both everywhere.
- Next: Phase 3, funnel plot and flags from the out-of-fold residuals.

### Expected-vs-actual ED model: funnel plot and flags (Phase 3)
- Residual = actual − expected, from the out-of-fold predictions only. Funnel limits at 95% and 99.8%, with Spiegelhalter's allowance for normal hospital-to-hospital spread (tau = 4.96 points). Hospital-years outside 99.8% are flagged "well above expected" or "well below expected".
- Flags, all years: 58 well above, 54 well below, 3,743 within range (2.9% flagged). 2024-25: 7 above, 6 below, out of 292 hospitals.
- Queensland flags: Mater Adult (above: 2016-17, 2017-18, 2019-20, 2020-21), Gladstone 2017-18 (above), Mount Isa 2024-25 (above, 82% vs 63%), Princess Alexandra 2011-12 (below), Sunshine Coast University 2016-17 (below; the hospital opened in March 2017, part-way through that year).
- Toowoomba: inside the limits every year. Checked by hand for 2024-25: expected 46.4%, binomial SE 0.2 points, sd = √(0.2² + 4.96²) = 4.96, so limits ±9.7 (95%) and ±15.3 (99.8%); actual 44% is 2.4 below. It ran above expected from 2019-20 to 2023-24 (up to +11.8 in 2021-22), so its fall to 44% is roughly what its size and patient mix predict, not an outlier.
- The limits fit loosely: 12.5% of hospital-years sit outside the 95% limits (about 5% would be a perfect fit), so the residuals have heavier tails than a normal curve. That's why flags use the 99.8% limits, and why they're "where to look", not verdicts.
- The funnel is almost flat: for hospitals with more than ~1,000 presentations the limits are set by tau, not by counting noise, so a big hospital gets nearly the same limits as a mid-sized one.
- `scripts/plot_funnel.py` draws `docs/images/06-funnel-plot.png` (2024-25) from `python -m pipeline.ml_expected --csv`. The colours avoid red/green: position already shows above or below, and flagged hospitals get a ring and a label.
- Next: Phase 4, write results to `marts.ml_ed_expected` with an audit row, retraining only when the data version changes.

### Bug fix: peer group picked at random in `dim_reporting_unit`
- Found because the model's baseline scored differently on each run (9.20, 8.84, 9.08). 398 reporting units have two peer-group labels in the same period: e.g. Toowoomba is "Large regional hospitals" on rate measures (4-hour, elective surgery) but "Not peered" on count measures (presentations, admissions). `distinct on` with ties picked one at random on every dbt build, so the label could flip week to week in Power BI as well as in the model.
- Fix: prefer a real peer group, and order on every column so the same row always wins. Hospitals in a peer group went from about 127 to 199 of 311; 112 are genuinely "Not peered". Two rebuilds in a row now give identical results.
- Earlier "184 of 311 hospitals have no peer group" in the model plan was this bug.

### Expected-vs-actual ED model: into the pipeline (Phase 4)
- `db/init/03-ml-tables.sql`: `marts.ml_ed_expected` (one row per hospital-year: actual, expected, residual, limits, flag) and `audit.model_runs` (data version, model version, MAE vs baseline, tau, flags). Applied to the live database; `powerbi_reader` (both tables) and `dashboard_reader` (marts only) got read access from the existing default privileges, no new grants.
- `run_model()` (also `python -m pipeline.ml_expected --train [--force]`): trains, then replaces the results table and writes the audit row in one transaction. It skips when this model version has already been trained on the current AIHW data version, so a quiet week costs one query.
- `pipeline/main.py`: with `ML_ENABLED=1`, the model step runs after a successful build, then `dbt test --select source:ml` checks its output (unique hospital-year, expected 0–100, known flags, hospital exists). The main build excludes those tests so they run once, after the write.
- Tested with two full pipeline runs from a branch image: the first trained (audit row linked to its pipeline run), the second skipped; dbt PASS=41 then PASS=5 both times. Fresh backup + `scripts/restore_test.sh`: PASS, 14 tables and views match.
- **Corrected results after the peer-group fix** (Phase 2 and 3 numbers above used random peer groups):

  | Method | MAE | MAE Qld | R² |
  |---|---|---|---|
  | Baseline: state and year average | 10.75 | 7.48 | 0.29 |
  | Baseline: peer group and year average | 7.42 | 5.96 | 0.66 |
  | Ridge, with state | 5.67 | 6.46 | 0.77 |
  | Ridge, without state | 5.88 | 7.55 | 0.76 |
  | **Gradient boosting, with state** | **4.68** | **5.00** | **0.84** |
  | Gradient boosting, without state | 5.22 | 6.26 | 0.80 |

  Without COVID years 4.83; "<5" fill 0 or 4: 4.69 / 4.73. Importance: size 5.4, year 2.1, resuscitation + emergency share 0.9, state 0.9, peer group 0.8, non-urgent 0.5, admitted 0.4, COVID 0.0. Funnel: tau 4.70, 106 flagged (2.7%); 2024-25: 9 above, 6 below. Queensland flags: Mater Adult 2016-17 and 2019-20, Gladstone 2017-18, Redland 2024-25 (above, 61% vs 46%); Princess Alexandra 2011-12, Sunshine Coast University 2016-17 (below). Mount Isa 2024-25 is no longer flagged. Toowoomba 2024-25: 44% vs 44.4% expected, within limits every year. Chart redrawn.
- Not switched on yet: the weekly run needs `ML_ENABLED=1` in the server `.env` after this branch is merged.
- Next: Phase 5, Power BI page 5, model card, README and website.

### Expected-vs-actual ED model: write-up (Phase 5, part 1)
- `docs/model-card.md`: purpose, intended use, what not to use it for, data, inputs, validation, accuracy, flags, limits, how it runs.
- README: "Predictive model: expected vs actual" section with the funnel chart; how-it-works, tech stack and repo layout updated.
- `marts.ml_ed_expected` gained `ed_presentations` (the funnel's x-axis), so Power BI and the future dashboard don't need a second table. Added on the live table, then retrained with `--force`; dbt output tests PASS=5.
- `decisions.md`: model and "<5" entries corrected to the post-fix numbers.
- Next: Power BI page 5 (expected vs actual), then merge and switch on `ML_ENABLED=1`, then the website section.
