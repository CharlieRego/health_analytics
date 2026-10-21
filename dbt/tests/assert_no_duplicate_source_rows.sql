{{ config(severity='warn') }}
-- Duplicates are kept out of the marts. This warning lists them so they're visible, not hidden.
select *
from {{ ref('stg_myh__flat') }}
where dup_rank > 1
