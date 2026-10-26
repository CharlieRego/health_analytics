-- Expected-vs-actual ED model (pipeline/ml_expected.py). Written by Python, not dbt.
-- Runs on a fresh database after 01-init.sh; safe to run again on an existing one.
-- Read access for powerbi_reader comes from the default privileges set in 01-init.sh.

-- One row per model training run
create table if not exists audit.model_runs (
    model_run_id      uuid        primary key,
    pipeline_run_id   uuid,                         -- null when run by hand
    trained_at        timestamptz not null default now(),
    status            text        not null,
    data_version      bigint      not null,
    model_version     text        not null,         -- bumped when features or settings change
    model             text        not null,
    baseline          text        not null,
    rows_scored       integer     not null,
    model_mae         numeric     not null,         -- percentage points, on unseen hospitals
    model_mae_qld     numeric     not null,
    baseline_mae      numeric     not null,
    baseline_mae_qld  numeric     not null,
    tau               numeric     not null,         -- hospital-to-hospital spread in the funnel limits
    n_flagged         integer     not null
);

-- Latest results: one row per hospital-year. Replaced in full on each training run.
create table if not exists marts.ml_ed_expected (
    reporting_unit_code text    not null,
    period_label        text    not null,
    fy_start_year       integer not null,
    pct_within_4h       numeric not null,           -- actual
    expected            numeric not null,           -- out-of-fold: from a model that never saw this hospital
    residual            numeric not null,           -- actual minus expected
    limit_95            numeric not null,
    limit_998           numeric not null,
    flag                text    not null,
    data_version        bigint  not null,
    model_run_id        uuid    not null,
    primary key (reporting_unit_code, period_label)
);
