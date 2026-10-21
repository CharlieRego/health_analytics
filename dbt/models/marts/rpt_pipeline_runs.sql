{{ config(materialized='view') }}

select
    run_id,
    started_at,
    finished_at,
    status,
    rows_loaded,
    data_version,
    message,
    extract(epoch from (finished_at - started_at))::int as duration_seconds
from {{ source('audit', 'pipeline_runs') }}
order by started_at desc
limit 50
