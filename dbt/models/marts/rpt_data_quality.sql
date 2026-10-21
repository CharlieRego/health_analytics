{{ config(materialized='view') }}

-- Every test from the most recent pipeline run that recorded dbt results
with latest_run as (
    select run_id
    from {{ source('audit', 'dbt_results') }}
    group by run_id
    order by max(recorded_at) desc
    limit 1
)

select
    split_part(d.unique_id, '.', 3) as check_name,
    d.status,
    coalesce(d.failures, 0)         as failures,
    d.message,
    d.recorded_at
from {{ source('audit', 'dbt_results') }} as d
inner join latest_run using (run_id)
where d.resource_type = 'test'
