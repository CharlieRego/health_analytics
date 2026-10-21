-- Rows the API sent = rows stored in raw = rows in the fact table + quarantined duplicates.
-- Any difference means data was lost or invented somewhere in the pipeline.
with latest as (
    select measure_category_code, max(data_version) as data_version
    from {{ source('audit', 'source_loads') }}
    group by measure_category_code
),
api_rows as (
    select sum(s.rows_loaded) as n
    from {{ source('audit', 'source_loads') }} as s
    inner join latest as l
        on  s.measure_category_code = l.measure_category_code
        and s.data_version = l.data_version
),
raw_rows as (
    select count(*) as n
    from {{ source('raw', 'myh_flat') }} as r
    inner join latest as l
        on  r.measure_category_code = l.measure_category_code
        and r.data_version = l.data_version
),
fact_rows as (select count(*) as n from {{ ref('fct_hospital_measure') }}),
dup_rows  as (select count(*) as n from {{ ref('stg_myh__flat') }} where dup_rank > 1)

select
    api_rows.n  as api_rows,
    raw_rows.n  as raw_rows,
    fact_rows.n as fact_rows,
    dup_rows.n  as duplicate_rows
from api_rows, raw_rows, fact_rows, dup_rows
where api_rows.n <> raw_rows.n
   or raw_rows.n <> fact_rows.n + dup_rows.n
