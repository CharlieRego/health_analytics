select
    {{ dbt_utils.generate_surrogate_key([
        'reporting_unit_code', 'reported_measure_code', 'period_start', 'period_end'
    ]) }}                                                       as fact_id,
    reporting_unit_code,
    reported_measure_code,
    period_start,
    period_end,
    to_char(period_start, 'YYYY') || '-' || to_char(period_end, 'YY') as period_label,
    value,
    peer_value,
    value - peer_value                                          as gap_to_peer,
    is_suppressed,
    is_caution,
    suppression,
    caveat
from {{ ref('stg_myh__flat') }}
where dup_rank = 1
