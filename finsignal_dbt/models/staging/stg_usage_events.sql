with source as (
    select * from {{ source('bronze', 'RAW_USAGE_EVENTS') }}
),

cleaned as (
    select
        "event_id"          as event_id,
        "customer_id"       as customer_id,
        "event_date"::date  as event_date,
        "event_type"        as event_type
    from source
)

select * from cleaned
