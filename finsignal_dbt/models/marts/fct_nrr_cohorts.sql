{{
    config(
        materialized='table',
        schema='GOLD'
    )
}}

-- NRR = ARR retained from a specific cohort of existing customers over time,
-- including expansions and contractions but EXCLUDING new logos.
-- NRR > 100% means existing customers are growing without new acquisition.
-- Grain: one row per (cohort_quarter, measurement_fiscal_quarter).

with customer_cohorts as (
    select
        customer_id,
        signup_fiscal_quarter as cohort_quarter
    from {{ ref('dim_customers') }}
    where signup_fiscal_quarter is not null
),

monthly_arr as (
    select
        s.customer_id,
        s.month,
        fc.fiscal_quarter,
        case
            when s.status = 'churned'       then 0
            when s.plan_tier = 'Starter'    then 2400
            when s.plan_tier = 'Growth'     then 14400
            when s.plan_tier = 'Enterprise' then 72000
            else 0
        end as tier_arr
    from {{ ref('stg_subscriptions') }} s
    join {{ ref('dim_fiscal_calendar') }} fc
        on s.month = fc.month_date
    where s.is_missing_tier = false
),

-- Customers who were active (ARR > 0) in their cohort's first quarter
cohort_first_quarter_customers as (
    select
        cc.customer_id,
        cc.cohort_quarter
    from customer_cohorts cc
    join monthly_arr ma
        on cc.customer_id = ma.customer_id
        and ma.fiscal_quarter = cc.cohort_quarter
        and ma.tier_arr > 0
    group by cc.customer_id, cc.cohort_quarter
),

cohort_starting_arr as (
    select
        cfc.cohort_quarter,
        sum(ma.tier_arr) as cohort_starting_arr
    from cohort_first_quarter_customers cfc
    join monthly_arr ma
        on cfc.customer_id = ma.customer_id
        and ma.fiscal_quarter = cfc.cohort_quarter
    group by cfc.cohort_quarter
),

-- Track same cohort customers forward into all subsequent quarters
cohort_quarterly_arr as (
    select
        cfc.cohort_quarter,
        ma.fiscal_quarter,
        sum(ma.tier_arr) as cohort_current_arr
    from cohort_first_quarter_customers cfc
    join monthly_arr ma
        on cfc.customer_id = ma.customer_id
    where ma.fiscal_quarter >= cfc.cohort_quarter
    group by cfc.cohort_quarter, ma.fiscal_quarter
)

select
    cqa.cohort_quarter,
    cqa.fiscal_quarter,
    csa.cohort_starting_arr,
    cqa.cohort_current_arr,
    round(cqa.cohort_current_arr / nullif(csa.cohort_starting_arr, 0) * 100, 2) as nrr_pct
from cohort_quarterly_arr cqa
join cohort_starting_arr csa
    on cqa.cohort_quarter = csa.cohort_quarter
order by cqa.cohort_quarter, cqa.fiscal_quarter
