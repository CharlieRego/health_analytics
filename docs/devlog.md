# Devlog

## Wed 21 Oct 2026
- **Module 4:** first full run had failed at skip=290,000 on MYH-ES (693,110 rows) with 504 Gateway Timeouts. Fix: download one `measure_code` at a time (4 measures, deepest offset ~235k), longer retries (5/15/30/60 s). Checked the 4 measure totals add up exactly to the category total first. Also fixed the audit log showing 0 rows for a failed run that had loaded 3 categories. Both written up in `decisions.md`.
- Re-ran the load (started 11:37). ED categories skipped as already loaded (idempotency working).
- **Module 6:** dbt 1.12.6 installed, `dbt debug` and `dbt seed` pass. Staging model, sources and tests written.
- **Module 7:** marts (star schema), reporting views, standard + 5 custom data-quality tests, and `dbt_audit.py` written. `dbt parse` OK.
- **Module 5:** `.dockerignore`, `Dockerfile` (with dbt), compose job and `run_pipeline.sh` written; image builds. Healthchecks.io check created (1 week period, 1 day grace).
- Next: finish MYH-ES load → run `scripts/check_ingest.sql` (record total N) → `python -m pipeline.main` (dbt build + idempotency) → Docker run → cron → Module 6 step 11 data exploration (Toowoomba code).
