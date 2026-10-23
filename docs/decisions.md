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
