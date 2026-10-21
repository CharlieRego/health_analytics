{{ config(severity='warn') }}
-- A suppressed value should never carry a number
select *
from {{ ref('fct_hospital_measure') }}
where is_suppressed
  and value is not null
