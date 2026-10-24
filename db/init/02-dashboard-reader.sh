#!/bin/bash
# Read-only login for the live dashboard: can read marts, nothing else (no raw, staging or audit).
# Runs on a fresh database like 01-init.sh. Safe to run again on an existing one:
# creates the login if it's missing, otherwise resets its password and grants.
set -euo pipefail
: "${DASHBOARD_DB_PASSWORD:?Set DASHBOARD_DB_PASSWORD in .env}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v pw="$DASHBOARD_DB_PASSWORD" -v db="$POSTGRES_DB" -v owner="$POSTGRES_USER" <<'EOSQL'
select format('create role dashboard_reader login password %L', :'pw')
where not exists (select from pg_roles where rolname = 'dashboard_reader') \gexec

alter role dashboard_reader with login password :'pw' connection limit 5;
-- A slow query from the dashboard can never hold the database for long
alter role dashboard_reader set statement_timeout = '30s';

grant connect on database :"db" to dashboard_reader;
grant usage on schema marts to dashboard_reader;
grant select on all tables in schema marts to dashboard_reader;
-- dbt drops and recreates the marts on every run; this keeps access to the new tables
alter default privileges for role :"owner" in schema marts
    grant select on tables to dashboard_reader;
EOSQL
