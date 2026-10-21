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
