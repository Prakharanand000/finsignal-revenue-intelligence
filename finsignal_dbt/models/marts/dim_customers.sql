{{
    config(
        materialized='table',
        schema='GOLD'
    )
}}

with customers as (
    select * from {{ ref('stg_customers') }}
),

subscriptions as (
    select * from {{ ref('stg_subscriptions') }}
),

first_months as (
    select
        customer_id,
        min(month) as first_active_month
    from subscriptions
    group by customer_id
),

latest_status as (
    select
        customer_id,
        status,
        row_number() over (partition by customer_id order by month desc) as rn
    from subscriptions
),

fiscal_cal as (
    select * from {{ ref('dim_fiscal_calendar') }}
)

select
    c.customer_id,
    c.signup_date,
    c.region,
    c.initial_plan_tier,
    fm.first_active_month,
    fc.fiscal_quarter    as signup_fiscal_quarter,
    ls.status            as current_status
from customers c
left join first_months fm
    on c.customer_id = fm.customer_id
left join fiscal_cal fc
    on date_trunc('month', c.signup_date) = fc.month_date
left join latest_status ls
    on c.customer_id = ls.customer_id
    and ls.rn = 1
