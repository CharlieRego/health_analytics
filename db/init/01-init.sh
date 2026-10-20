#!/bin/bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
-- Layers: raw (untouched API data), staging + marts (built by dbt), audit (controls)
create schema if not exists raw;
create schema if not exists audit;
create schema if not exists staging;
create schema if not exists marts;

-- Every API record stored unchanged as JSON, tagged with the run and data version
create table if not exists raw.myh_flat (
    id                    bigserial   primary key,
    run_id                uuid        not null,
    measure_category_code text        not null,
    data_version          bigint      not null,
    loaded_at             timestamptz not null default now(),
    record                jsonb       not null
);
create index if not exists ix_myh_flat_cat_version
    on raw.myh_flat (measure_category_code, data_version);

-- One row per pipeline run
create table if not exists audit.pipeline_runs (
    run_id       uuid        primary key,
    started_at   timestamptz not null default now(),
    finished_at  timestamptz,
    status       text        not null default 'running',
    rows_loaded  integer     not null default 0,
    data_version bigint,
    message      text
);

-- One row per category per data version. The primary key stops the same data loading twice.
create table if not exists audit.source_loads (
    measure_category_code text        not null,
    data_version          bigint      not null,
    run_id                uuid        not null references audit.pipeline_runs (run_id),
    date_uploaded         timestamptz,
    rows_loaded           integer     not null,
    loaded_at             timestamptz not null default now(),
    primary key (measure_category_code, data_version)
);

-- Results of every dbt model and test, per run
create table if not exists audit.dbt_results (
    id             bigserial   primary key,
    run_id         uuid        not null,
    invocation_id  text        not null,
    unique_id      text        not null,
    resource_type  text        not null,
    status         text        not null,
    failures       integer,
    message        text,
    execution_time numeric,
    recorded_at    timestamptz not null default now()
);

-- Read-only login for Power BI: can read marts and audit, nothing else
create role powerbi_reader login password '${POWERBI_PASSWORD}';
grant connect on database "${POSTGRES_DB}" to powerbi_reader;
grant usage on schema marts, audit to powerbi_reader;
grant select on all tables in schema marts, audit to powerbi_reader;
alter default privileges for role "${POSTGRES_USER}" in schema marts, audit
    grant select on tables to powerbi_reader;
EOSQL
