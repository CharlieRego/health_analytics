#!/usr/bin/env bash
# Restore the latest backup into a temporary database and check it matches the live one:
# same tables, same row counts, same fact-table checksum. Drops the copy afterwards.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

DUMP=${1:-$(ls -1t "$HOME"/backups/hospital_*.dump | head -1)}
TMP_DB=restore_test

psql_in() {  # psql_in <db> <sql>
    docker exec hospital-db sh -c "psql -U \"\$POSTGRES_USER\" -d $1 -At -F'|' -c \"$2\""
}

COUNTS="SELECT table_schema||'.'||table_name, (xpath('/row/n/text()', query_to_xml(format('SELECT count(*) AS n FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1"
CHECKSUM="SELECT md5(string_agg(md5(f::text), '' ORDER BY f::text)) FROM marts.fct_hospital_measure f"

cleanup() { psql_in postgres "DROP DATABASE IF EXISTS $TMP_DB" > /dev/null; }
trap cleanup EXIT

echo "Restoring $DUMP"
cleanup
psql_in postgres "CREATE DATABASE $TMP_DB" > /dev/null
start=$(date +%s)
docker exec -i hospital-db sh -c "pg_restore -U \"\$POSTGRES_USER\" -d $TMP_DB --exit-on-error" < "$DUMP"
echo "Restored in $(( $(date +%s) - start ))s"

if diff <(psql_in "$POSTGRES_DB" "$COUNTS") <(psql_in "$TMP_DB" "$COUNTS"); then
    echo "Row counts match ($(psql_in "$TMP_DB" "$COUNTS" | wc -l) tables and views)"
else
    echo "FAIL: row counts differ (live < > restored)"; exit 1
fi

live=$(psql_in "$POSTGRES_DB" "$CHECKSUM"); restored=$(psql_in "$TMP_DB" "$CHECKSUM")
[ "$live" = "$restored" ] || { echo "FAIL: fact table checksum differs"; exit 1; }
echo "Fact table checksum matches ($restored)"
echo "PASS"
