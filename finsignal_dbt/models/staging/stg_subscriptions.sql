-- Bronze columns are quoted-lowercase (created by write_pandas).
-- Silver normalizes casing and flags NULL plan_tier rows rather than dropping them,
-- preventing silent ARR understatement downstream.

with source as (
    select * from {{ source('bronze', 'RAW_SUBSCRIPTIONS') }}
),

cleaned as (
    select
        "subscription_id"                                          as subscription_id,
        "customer_id"                                              as customer_id,
        "month"::date                                              as month,
        "plan_tier"                                                as plan_tier,
        "mrr"::number(12, 2)                                       as mrr,
        "status"                                                   as status,
        case when "plan_tier" is null then true else false end      as is_missing_tier
    from source
)

select * from cleaned
