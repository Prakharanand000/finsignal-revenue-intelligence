with source as (
    select * from {{ source('bronze', 'RAW_CUSTOMERS') }}
),

cleaned as (
    select
        "customer_id"       as customer_id,
        "signup_date"::date as signup_date,
        trim("region")      as region,
        "initial_plan_tier" as initial_plan_tier
    from source
)

select * from cleaned
