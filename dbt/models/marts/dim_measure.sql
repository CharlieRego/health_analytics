with measures as (
    select distinct on (reported_measure_code)
        reported_measure_code,
        reported_measure_name,
        measure_code,
        measure_name,
        measure_category_code,
        disaggregation_type,
        units
    from {{ ref('stg_myh__flat') }}
    order by reported_measure_code, period_end desc
)

select
    m.*,
    d.higher_is_better
from measures as m
left join {{ ref('measure_direction') }} as d
    on d.measure_code = m.measure_code
