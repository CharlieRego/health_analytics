# Decisions

## 2026-10-21 – Download elective surgery data one measure at a time
**Decision:** Fetch each measure category per `measure_code` (e.g. MYH-ES → MYH0006, MYH0007, MYH0008, MYH0009) instead of paging through the whole category. Retries now wait 5, 15, 30, then 60 seconds.
**Why:** MYH-ES has 693,110 rows. Paging with `skip`/`top` got slower the deeper it went, and failed at skip=290,000 with 504 Gateway Timeouts. Splitting by measure keeps the deepest offset at about 235,000. I checked first that the four measure totals add up exactly to the category total, so nothing is missed or duplicated.
**Trade-off:** One extra API call per category to list its measures, and the code depends on the API's `measure_code` filter. A fair cost, since the load now finishes reliably.

## 2026-10-21 – Record partial progress when a run fails
**Decision:** Update `audit.pipeline_runs.rows_loaded` after each category loads, and don't overwrite it with 0 if the run fails later.
**Why:** The failed run above loaded three categories before it broke, but the audit table said 0 rows. An audit trail has to be right on the days a run fails, because that's when someone reads it.
**Trade-off:** One small extra update per category, which costs almost nothing.

## 2026-10-21 – Treat "*" (code X42) as a caution flag, not suppression
**Decision:** In staging, `is_suppressed` excludes suppression code X42 ("*"), and a new `is_caution` column flags those rows instead.
**Why:** The `assert_suppressed_values_are_blank` test warned that 879 "suppressed" rows had values. The API's `/suppressions` list showed X42 means "interpret with caution: 5–10% of presentations had missing or invalid time data", so the value is valid. All other codes (NP, <5, -, NP†, Not peered) never carry a value. So the data was fine; I had misread the source.
**Trade-off:** Hard-codes one code. If AIHW adds other caution-only codes, the same test will warn again, which is the point of keeping it.

## 2026-10-21 – Model the marts as a star schema
**Decision:** One fact table (`fct_hospital_measure`, one row per unit × reported measure × period) joined to two dimensions (`dim_reporting_unit`, `dim_measure`).
**Why:** Power BI's engine is built for this shape: filters flow from small dimension tables to the big fact table, measures stay simple, and names and units live in one place instead of repeating on 862k rows.
**Trade-off:** One more modelling layer than querying staging directly. Clean relationships and fast visuals make up for it.

## 2026-10-21 – Quarantine duplicate source rows instead of dropping them
**Decision:** Staging gives each row a `dup_rank` per unit/measure/period. The marts only take `dup_rank = 1`, and a warn-level test lists any extras.
**Why:** Silently deleting rows hides upstream problems. Flagging them keeps the facts clean while making every duplicate visible and countable, and the reconciliation test accounts for them. This load had 0 duplicates, so the control is in place but has nothing to report.
**Trade-off:** A window function over ~860k rows on every build (a few seconds). That's a small cost for making every duplicate visible.

## 2026-10-21 – Make three-way reconciliation the headline control
**Decision:** A custom dbt test checks that rows the API sent (`audit.source_loads`) = rows stored in raw = rows in the fact table + quarantined duplicates, for the latest data version. It fails the build if not.
**Why:** The other tests check that values look right. Only reconciliation proves that nothing was lost or invented between source and dashboard, which is the question an auditor or a health executive asks first. Current result: 862,030 = 862,030 = 862,030 + 0.
**Trade-off:** Relies on the audit log being accurate, which is why ingest records counts in the same transaction as the load.

## 2026-10-23 – Keep Postgres off the internet; connect through an SSH tunnel
*(Decided at setup on 20 Oct; logged here with the other foundations.)*
**Decision:** Docker publishes Postgres on `127.0.0.1:5432` only, and the firewall (ufw) allows SSH and nothing else. Power BI reaches the database through an SSH tunnel (`localhost:5433` on the laptop) as `powerbi_reader`, a login that can read the marts but not raw.
**Why:** A database port open to the internet gets scanned and brute-forced within hours. The tunnel reuses SSH key authentication I already trust, so no extra service, certificate or open port is needed.
**Trade-off:** The tunnel has to be open before refreshing the dashboard, which is also why the Power BI file is a snapshot (see below).

## 2026-10-23 – Store raw API records unchanged as JSONB
**Decision:** `raw.myh_flat` stores each API record exactly as received in a `record jsonb` column, with only load metadata (run, category, data version) alongside. All parsing happens in dbt staging.
**Why:** If a parsing rule is wrong (like the X42 "*" misread), I fix the dbt model and rebuild, with no re-download. The raw layer is also the evidence for reconciliation: it is what the API actually sent.
**Trade-off:** JSONB takes more space than typed columns and staging has to cast every field. At ~860k rows the raw table is about 0.9 GB including indexes, which is fine on this server.

## 2026-10-23 – Bulk-load with COPY, one transaction per category
**Decision:** Once a category is downloaded, its rows are streamed into Postgres with `COPY`, inside one transaction together with its `audit.source_loads` row.
**Why:** `COPY` is far faster than row-by-row `INSERT`, so writing to the database takes far less time than downloading. One transaction means a category is either fully loaded and logged or not there at all, so a failure can't leave half a category behind.
**Trade-off:** A failure loses that category's progress and it is re-downloaded next run. Acceptable because the per-measure download makes failures rare.

## 2026-10-23 – Two guards against loading the same data twice
**Decision:** Before downloading, the pipeline checks `audit.source_loads` for the category's current `data_version` and skips it if found. Separately, `(measure_category_code, data_version)` is the table's primary key.
**Why:** The check makes normal re-runs cheap (a week with no new AIHW release loads 0 rows). The primary key is the backstop: even if the check were bypassed or two runs overlapped, the second insert fails and its transaction rolls back, so duplicate data can't be committed.
**Trade-off:** Depends on AIHW bumping `data_version` when it changes data. If it ever corrected data in place without a new version, the pipeline would not notice; reconciliation against the API count would be the next line of defence.

## 2026-10-23 – Power BI in Import mode, committed as a snapshot
**Decision:** The report imports data into the .pbix rather than using DirectQuery, and the committed file is a snapshot refreshed by hand.
**Why:** Anyone can download the file and open it without database access, visuals are fast, and the university tenant blocks the Power BI service, so scheduled refresh through a gateway isn't available. The Data Assurance page shows the date of the last successful run so viewers know how current it is.
**Trade-off:** The dashboard is only as current as the last manual refresh. In production I'd publish to the Power BI service with an on-premises data gateway and schedule a refresh after each Monday load.

## 2026-10-24 – Publish run status to its own git branch
**Decision:** After each run, `scripts/publish_status.sh` commits `status/status.json` (run result, finish time, test counts, data version) to a `status` branch that holds only that file. The project website reads it from `raw.githubusercontent.com`.
**Why:** The website can show that the pipeline actually runs, with no web server or open port on the VPS. A separate branch keeps `main` history to code changes only, and the script uses git plumbing so the cron job never switches branches or rewrites the server's code checkout.
**Trade-off:** GitHub caches raw files for a few minutes and the site re-fetches hourly, so the panel can lag a run by up to an hour. If a run dies before it writes the file, the panel shows the previous run, which is why the site flags a run older than 8 days as overdue.

## 2026-10-27 – Model target: % leaving ED within 4 hours, with no time-in-ED inputs
**Decision:** The expected-vs-actual model predicts `MYH-RM0015` (% of all ED patients leaving within 4 hours). Median time in ED (MYH0036) and 90th-percentile time (MYH0013) are never inputs.
**Why:** It's the national 4-hour target and every hospital reports it. The first plan used "seen on time" (MYH0010), which only exists split by triage category. The time-in-ED measures describe the same patients' stays as the target, so using them would make the model look accurate without explaining anything (leakage).
**Trade-off:** The inputs are only size and patient mix, so the model will be less accurate than one that "cheats". That's the point: the gap between actual and expected should reflect what size and patient mix can't explain.

## 2026-10-27 – Fill "<5" patient counts with 2 in the model features
**Decision:** In `ml_ed_features`, an ED patient count suppressed as "<5" is set to 2 (the middle of 0–4). Any other missing value drops the hospital-year.
**Why:** 563 hospital-years (15%) had "<5" resuscitation patients, almost all at small hospitals. Dropping them would remove most small hospitals over a tiny number. For 90% of those hospitals the fill can move the resuscitation + emergency share by 0.3 percentage points at most.
**Trade-off:** A made-up value, though a bounded one. A sensitivity check in Phase 2 (fill with 0 or 4 instead) will show whether it matters.

## 2026-10-27 – Gradient boosting with state for the expected-vs-actual model
**Decision:** Use `HistGradientBoostingRegressor` with state as an input. Every hospital-year is scored by a model that never saw that hospital (`GroupKFold` by hospital).
**Why:** On unseen hospitals it is off by 4.81 points on average, against 9.20 for the best simple average (peer group and year) and 6.09 for Ridge. It is also the only model that beats the peer-group average for Queensland hospitals (5.34 vs 6.52). Including state helps (5.40 without it): hospitals are compared with their own state's system, which is fairer when states count and run EDs differently. Grouping folds by hospital matters because a hospital's years look alike; splitting by row would let the model recognise the hospital and look better than it is.
**Trade-off:** Harder to explain than a linear model, so the model card leans on permutation importance (size first, then year and patient mix). And it can't say why a hospital differs from expected, only that it does. The "<5" fill made no difference (MAE 4.81 with 0, 2 or 4).

## 2026-10-27 – Funnel limits with an allowance for hospital-to-hospital spread
**Decision:** Funnel-plot limits use sd = √(binomial SE² + tau²), with tau estimated from z-scores winsorised at 10% each tail (Spiegelhalter 2005). Flags use the 99.8% limits.
**Why:** Plain binomial limits for a hospital with 60,000 presentations are about ±0.6 points, so almost every large hospital would be "unusual". The real spread between similar hospitals (tau ≈ 5 points) is much bigger than counting noise, and includes what the model can't explain. Adding it gives limits that flag about 3% of hospital-years instead of most of them.
**Trade-off:** The limits are nearly flat across hospital size, so the chart looks less like a classic funnel. And tau is estimated from the same data, so it moves a little each year.
