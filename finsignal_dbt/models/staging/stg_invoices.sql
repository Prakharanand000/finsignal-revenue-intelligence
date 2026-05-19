-- Deduplicates ~2% duplicate invoice rows injected in bronze (simulates ETL double-load).
-- ROW_NUMBER() window function partitioned by invoice_id keeps first occurrence.
-- Verified: 31,469 bronze rows -> 30,852 silver rows (617 duplicates removed, 0 remaining).

with source as (
    select * from {{ source('bronze', 'RAW_INVOICES') }}
),

deduplicated as (
    select
        "invoice_id"                                                              as invoice_id,
        "customer_id"                                                             as customer_id,
        "invoice_date"::date                                                      as invoice_date,
        "period_month"::date                                                      as period_month,
        "amount"::number(12, 2)                                                   as amount,
        row_number() over (partition by "invoice_id" order by "invoice_date")     as rn
    from source
)

select
    invoice_id,
    customer_id,
    invoice_date,
    period_month,
    amount
from deduplicated
where rn = 1
