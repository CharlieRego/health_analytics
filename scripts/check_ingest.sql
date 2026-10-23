-- Post-ingest checks: raw rows vs audit log, per-measure counts, duplicates, total rows, recent runs.
-- Run: docker exec -i hospital-db psql -U pipeline -d hospital < scripts/check_ingest.sql

\echo '1) Raw rows vs audit log, per category (match should be t)'
select s.measure_category_code, s.data_version, s.rows_loaded as audit_rows,
       count(r.id) as raw_rows, s.rows_loaded = count(r.id) as match
from audit.source_loads s
left join raw.myh_flat r
  on r.measure_category_code = s.measure_category_code
 and r.data_version = s.data_version
group by 1, 2, 3
order by 1, 2;

\echo '2) MYH-ES rows per measure (API: MYH0006 223990, MYH0007 222083, MYH0008 12477, MYH0009 234560 = 693110)'
select record->>'measure_code' as measure_code, count(*) as rows
from raw.myh_flat
where measure_category_code = 'MYH-ES'
group by 1
order by 1;

\echo '3) Exact duplicate records per category (should all be 0)'
select measure_category_code, data_version,
       count(*) - count(distinct record) as duplicates
from raw.myh_flat
group by 1, 2
order by 1, 2;

\echo '4) Grand total raw rows (record this N for the resume line)'
select count(*) as total_raw_rows from raw.myh_flat;

\echo '5) Latest pipeline runs'
select started_at::timestamp(0), finished_at::timestamp(0), status, rows_loaded, data_version,
       left(message, 60) as message
from audit.pipeline_runs
order by started_at desc
limit 5;
