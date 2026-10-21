select *
from {{ ref('fct_hospital_measure') }}
where period_start > period_end
