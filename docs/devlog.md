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
