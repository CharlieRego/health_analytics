select distinct on (reporting_unit_code)
    reporting_unit_code,
    reporting_unit_name,
    reporting_unit_type_code,
    reporting_unit_type_name,
    state,
    coalesce(peer_group_name, 'Not peered') as peer_group_name
from {{ ref('stg_myh__flat') }}
where reporting_unit_code is not null
order by reporting_unit_code, period_end desc
