# Decisions

## 2026-10-21 – Download elective surgery data one measure at a time
**Decision:** Fetch each measure category per `measure_code` (e.g. MYH-ES → MYH0006, MYH0007, MYH0008, MYH0009) instead of paging through the whole category. Retries now wait 5, 15, 30, then 60 seconds.
**Why:** MYH-ES has 693,110 rows. Paging with `skip`/`top` got slower the deeper it went, and failed at skip=290,000 with 504 Gateway Timeouts. Splitting by measure keeps the deepest offset at about 235,000. I checked first that the four measure totals add up exactly to the category total, so nothing is missed or duplicated.
**Trade-off:** One extra API call per category to list its measures, and the code depends on the API's `measure_code` filter. Worth it for a load that finishes reliably.

## 2026-10-21 – Record partial progress when a run fails
**Decision:** Update `audit.pipeline_runs.rows_loaded` after each category loads, and don't overwrite it with 0 if the run fails later.
**Why:** The failed run above loaded three categories before it broke, but the audit table said 0 rows. An audit trail that's wrong when things go wrong is the one time it matters.
**Trade-off:** One small extra update per category. Negligible.

## 2026-10-21 – Treat "*" (code X42) as a caution flag, not suppression
**Decision:** In staging, `is_suppressed` excludes suppression code X42 ("*"), and a new `is_caution` column flags those rows instead.
**Why:** The `assert_suppressed_values_are_blank` test warned that 879 "suppressed" rows had values. The API's `/suppressions` list showed X42 means "interpret with caution: 5–10% of presentations had missing or invalid time data", so the value is valid. All other codes (NP, <5, -, NP†, Not peered) never carry a value. The test caught a misreading of the source, not bad data.
**Trade-off:** Hard-codes one code. If AIHW adds other caution-only codes, the same test will warn again, which is the point of keeping it.

## 2026-10-21 – Model the marts as a star schema
**Decision:** One fact table (`fct_hospital_measure`, one row per unit × reported measure × period) joined to two dimensions (`dim_reporting_unit`, `dim_measure`).
**Why:** Power BI's engine is built for this shape: filters flow from small dimension tables to the big fact table, measures stay simple, and names and units live in one place instead of repeating on 862k rows.
**Trade-off:** One more modelling layer than querying staging directly. Worth it for clean relationships and fast visuals.

## 2026-10-21 – Quarantine duplicate source rows instead of dropping them
**Decision:** Staging gives each row a `dup_rank` per unit/measure/period. The marts only take `dup_rank = 1`, and a warn-level test lists any extras.
**Why:** Silently deleting rows hides upstream problems. Flagging them keeps the facts clean while making every duplicate visible and countable, and the reconciliation test accounts for them. This load had 0 duplicates, so the control is in place but has nothing to report.
**Trade-off:** A window function over ~860k rows on every build (a few seconds). Cheap for the audit value.

## 2026-10-21 – Make three-way reconciliation the headline control
**Decision:** A custom dbt test checks that rows the API sent (`audit.source_loads`) = rows stored in raw = rows in the fact table + quarantined duplicates, for the latest data version. It fails the build if not.
**Why:** The other tests check that values look right. Only reconciliation proves that nothing was lost or invented between source and dashboard, which is the question an auditor or a health executive asks first. Current result: 862,030 = 862,030 = 862,030 + 0.
**Trade-off:** Relies on the audit log being accurate, which is why ingest records counts in the same transaction as the load.
