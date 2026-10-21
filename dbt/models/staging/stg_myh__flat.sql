with latest as (
    select measure_category_code, max(data_version) as data_version
    from {{ source('raw', 'myh_flat') }}
    group by measure_category_code
),

parsed as (
    select
        r.id                                              as raw_id,
        r.measure_category_code,
        r.data_version,
        r.record ->> 'measure_code'                       as measure_code,
        r.record ->> 'measure_name'                       as measure_name,
        r.record ->> 'reported_measure_code'              as reported_measure_code,
        r.record ->> 'reported_measure_name'              as reported_measure_name,
        r.record ->> 'reported_measure_category_type_name' as disaggregation_type,
        r.record ->> 'reporting_unit_code'                as reporting_unit_code,
        r.record ->> 'reporting_unit_name'                as reporting_unit_name,
        r.record ->> 'reporting_unit_type_code'           as reporting_unit_type_code,
        r.record ->> 'reporting_unit_type_name'           as reporting_unit_type_name,
        r.record ->> 'mapped_state'                       as state,
        r.record ->> 'peer_group_name'                    as peer_group_name,
        (r.record ->> 'reporting_start_date')::date       as period_start,
        (r.record ->> 'reporting_end_date')::date         as period_end,
        (r.record ->> 'value')::numeric                   as value,
        (r.record ->> 'peer_value')::numeric              as peer_value,
        r.record ->> 'units_name'                         as units,
        r.record ->> 'suppression'                        as suppression,
        r.record ->> 'caveat'                             as caveat,
        r.record ->> 'caveat_footnotes'                   as caveat_footnotes,
        (r.record ->> 'suppression') is not null          as is_suppressed
    from {{ source('raw', 'myh_flat') }} as r
    inner join latest as l
        on  r.measure_category_code = l.measure_category_code
        and r.data_version = l.data_version
)

select
    *,
    -- 1 = first copy of this unit/measure/period; anything higher is a duplicate
    row_number() over (
        partition by reporting_unit_code, reported_measure_code, period_start, period_end
        order by raw_id
    ) as dup_rank
from parsed
