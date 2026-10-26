-- One row per reporting unit, described by its latest period.
-- A hospital can be "Not peered" on count measures but in a peer group on rate
-- measures in the same period, so a real peer group is preferred, and the order
-- is fully fixed so the same row wins on every build.
select distinct on (reporting_unit_code)
    reporting_unit_code,
    reporting_unit_name,
    reporting_unit_type_code,
    reporting_unit_type_name,
    state,
    coalesce(peer_group_name, 'Not peered') as peer_group_name
from {{ ref('stg_myh__flat') }}
where reporting_unit_code is not null
order by
    reporting_unit_code,
    period_end desc,
    coalesce(peer_group_name, 'Not peered') in ('Not peered', 'Unpeered'),   -- real peer group first
    peer_group_name,
    reporting_unit_name
