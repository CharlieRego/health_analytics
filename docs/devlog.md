# Devlog

## Wed 21 Oct 2026
- **Module 4:** first full run had failed at skip=290,000 on MYH-ES (693,110 rows) with 504 Gateway Timeouts. Fix: download one `measure_code` at a time (4 measures, deepest offset ~235k), longer retries (5/15/30/60 s). Checked the 4 measure totals add up exactly to the category total first. Also fixed the audit log showing 0 rows for a failed run that had loaded 3 categories. Both written up in `decisions.md`.
- Re-ran the load (started 11:37). ED categories skipped as already loaded (idempotency working).
- **Module 6:** dbt 1.12.6 installed, `dbt debug` and `dbt seed` pass. Staging model, sources and tests written.
- **Module 7:** marts (star schema), reporting views, standard + 5 custom data-quality tests, and `dbt_audit.py` written. `dbt parse` OK.
- **Module 5:** `.dockerignore`, `Dockerfile` (with dbt), compose job and `run_pipeline.sh` written; image builds. Healthchecks.io check created (1 week period, 1 day grace).
- Next: finish MYH-ES load → run `scripts/check_ingest.sql` (record total N) → `python -m pipeline.main` (dbt build + idempotency) → Docker run → cron → Module 6 step 11 data exploration (Toowoomba code).

### Data exploration (Module 6 step 11)
- **Unit types:** H Hospital (390), LHN Local Hospital Network (86), PG Peer Group (8), S State (8), NAT National (1).
- **Toowoomba Hospital: `H0439`**, peer group *Large regional hospitals*. Its LHN is **Darling Downs `LHN325`**.
- **Queensland: `Qld`** (state code is mixed case, `state = 'Qld'`, not `QLD`). **National: `NAT`**.
- **Periods:** 2011-07-01 to 2025-06-30 (financial years).
- **Duplicates:** 0 source rows with `dup_rank > 1`.
- **Measures:** ED: MYH0035/0011/0012 presentations, MYH0010 % seen on time, MYH0005 % left ED within 4 h, MYH0013 90th pct time in ED, MYH0036 median time in ED. Elective surgery: MYH0006 count, MYH0007 % waited >365 days, MYH0008 % on time, MYH0009 median wait (days).
- **"All patients" breakdowns exist only for the ED-time measures:** MYH0005 → `MYH-RM0015` (4-hour rule, best Qld headline), MYH0013 → `MYH-RM0302`, MYH0036 → `MYH-RM0300`, MYH0012 → `MYH-RM0023`.
- **MYH0010 (ED seen on time) has no "all patients" row**, only 5 triage categories (MYH-RM0035–0039). **MYH0008** only has urgency categories (MYH-RM0047 urgent, 0048 semi-urgent, 0049 non-urgent). Dashboards should pick a category, or use MYH0005 for an overall ED figure. Matters for Module 11 (stretch).
- Next: Module 8 Power BI (connect, model, pages 1–2).
