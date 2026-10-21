-- Percentages must be between 0 and 100
select f.*
from {{ ref('fct_hospital_measure') }} as f
inner join {{ ref('dim_measure') }} as m using (reported_measure_code)
where m.units = 'percent'
  and (f.value < 0 or f.value > 100)
