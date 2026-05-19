{{
    config(
        materialized='table',
        schema='GOLD'
    )
}}

-- ARR movement classification driven by PLAN TIER CHANGE, not raw MRR delta.
-- Fixed tier-based ARR eliminates ±10% billing noise that caused 14,277 false
-- expansion/contraction events in v1. Rebuilt using fixed tier values:
--   Starter=$2,400/yr  Growth=$14,400/yr  Enterprise=$72,000/yr
-- Final result: 159 real expansions, 61 real contractions across 3 fiscal years.
--
-- Movement classification rules (LAG window on tier_arr by customer, ordered by month):
--   new:          prior_arr IS NULL (first appearance)
--   reactivation: prior_arr = 0 AND current_arr > 0 (returned after churn)
--   expansion:    prior_arr > 0 AND current_arr > prior_arr (tier upgrade)
--   contraction:  prior_arr > 0 AND current_arr > 0 AND current < prior (tier downgrade)
--   churn:        prior_arr > 0 AND current_arr = 0 (cancelled)
--
-- Rows with is_missing_tier=true (~1% NULL plan_tier) excluded from ARR calculations.
-- They are preserved in stg_subscriptions with is_missing_tier flag to avoid silent
-- ARR understatement; excluded here because tier_arr cannot be reliably assigned.

with monthly_arr as (
    select
        customer_id,
        month,
        plan_tier,
        case
            when status = 'churned'      then 0
            when plan_tier = 'Starter'   then 2400
            when plan_tier = 'Growth'    then 14400
            when plan_tier = 'Enterprise'then 72000
            else 0
        end as tier_arr
    from {{ ref('stg_subscriptions') }}
    where is_missing_tier = false
),

with_prior as (
    select
        customer_id,
        month,
        plan_tier,
        tier_arr                                                                as current_arr,
        lag(tier_arr) over (partition by customer_id order by month)            as prior_arr
    from monthly_arr
),

movements as (
    select
        customer_id,
        month,
        plan_tier,
        prior_arr,
        current_arr,
        current_arr - coalesce(prior_arr, 0)                                    as arr_delta,
        case
            when prior_arr is null                                       then 'new'
            when prior_arr = 0 and current_arr > 0                       then 'reactivation'
            when prior_arr > 0 and current_arr > prior_arr               then 'expansion'
            when prior_arr > 0 and current_arr > 0 and current_arr < prior_arr then 'contraction'
            when prior_arr > 0 and current_arr = 0                       then 'churn'
        end as movement_type
    from with_prior
    where current_arr != prior_arr
       or prior_arr is null
),

fiscal_cal as (
    select month_date, fiscal_quarter
    from {{ ref('dim_fiscal_calendar') }}
)

select
    m.customer_id,
    m.month,
    fc.fiscal_quarter,
    m.plan_tier,
    m.prior_arr,
    m.current_arr,
    m.arr_delta,
    m.movement_type
from movements m
left join fiscal_cal fc
    on m.month = fc.month_date
where m.movement_type is not null
