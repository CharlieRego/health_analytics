-- One row per hospital and financial year: the 4-hour ED result (the target)
-- and the inputs the expected-vs-actual model uses.
-- Patient counts suppressed as "<5" are filled with 2 (the middle of 0-4).
-- Any other missing value drops that hospital-year.

with measures as (
    select
        f.reporting_unit_code,
        f.period_start,
        f.period_label,
        f.reported_measure_code,
        f.is_caution,
        case
            when not f.is_suppressed and f.value is not null then f.value
            when f.reported_measure_code <> 'MYH-RM0015' and f.suppression = '<5' then 2
        end as value
    from {{ ref('fct_hospital_measure') }} f
    join {{ ref('dim_reporting_unit') }} u using (reporting_unit_code)
    where u.reporting_unit_type_code = 'H'
      and f.reported_measure_code in (
          'MYH-RM0015',  -- % leaving ED within 4 hours, all patients (target)
          'MYH-RM0023',  -- ED presentations, all patients
          'MYH-RM0025',  -- resuscitation
          'MYH-RM0026',  -- emergency
          'MYH-RM0029',  -- non-urgent
          'MYH-RM0022'   -- subsequently admitted
      )
),

pivoted as (
    select
        reporting_unit_code,
        period_start,
        period_label,
        max(value) filter (where reported_measure_code = 'MYH-RM0015') as pct_within_4h,
        max(value) filter (where reported_measure_code = 'MYH-RM0023') as ed_presentations,
        max(value) filter (where reported_measure_code = 'MYH-RM0025') as resuscitation,
        max(value) filter (where reported_measure_code = 'MYH-RM0026') as emergency,
        max(value) filter (where reported_measure_code = 'MYH-RM0029') as non_urgent,
        max(value) filter (where reported_measure_code = 'MYH-RM0022') as admitted,
        bool_or(is_caution) as has_caution
    from measures
    group by reporting_unit_code, period_start, period_label
)

select
    p.reporting_unit_code,
    u.reporting_unit_name,
    u.state,
    u.peer_group_name,
    p.period_label,
    extract(year from p.period_start)::int                  as fy_start_year,
    p.period_label in ('2019-20', '2020-21', '2021-22')     as covid_period,
    p.pct_within_4h,
    p.ed_presentations,
    ln(p.ed_presentations)                                  as log_ed_presentations,
    (p.resuscitation + p.emergency) / p.ed_presentations    as share_resus_emergency,
    p.non_urgent / p.ed_presentations                       as share_non_urgent,
    p.admitted / p.ed_presentations                         as share_admitted,
    p.has_caution
from pivoted p
join {{ ref('dim_reporting_unit') }} u using (reporting_unit_code)
where p.pct_within_4h is not null
  and p.ed_presentations > 0
  and p.resuscitation is not null
  and p.emergency is not null
  and p.non_urgent is not null
  and p.admitted is not null
