{{
    config(
        materialized='table',
        schema='GOLD'
    )
}}

-- Fiscal year starts February 1 (FY2026 = Feb 1 2025 to Jan 31 2026).
-- Quarter mapping: Q1=Feb-Apr, Q2=May-Jul, Q3=Aug-Oct, Q4=Nov-Jan.
-- The seeded bad-quarter anomaly (doubled Growth-tier churn) lands in Aug-Oct 2025 = FY2026-Q3.
--
-- Fiscal month number formula: mod(calendar_month - 2 + 12, 12) + 1
--   Feb=1, Mar=2, ..., Aug=7, ..., Jan=12
-- Quarter: ceil(fiscal_month_number / 3)
--
-- Boundary cases verified by hand before approving:
--   Feb 2025 -> FY2026-Q1 (first month of fiscal year) ✓
--   Aug 2025 -> FY2026-Q3 (bad quarter) ✓
--   Jan 2026 -> FY2026-Q4 (last month, calendar year already rolled) ✓

with months as (
    select
        dateadd(month, seq4(), '2023-02-01'::date) as month_date
    from table(generator(rowcount => 36))
),

fiscal as (
    select
        month_date,
        year(month_date)                                                                as calendar_year,
        month(month_date)                                                               as calendar_month,
        case
            when month(month_date) >= 2 then year(month_date) + 1
            else year(month_date)
        end                                                                             as fiscal_year,
        mod(month(month_date) - 2 + 12, 12) + 1                                        as fiscal_month_number,
        ceil((mod(month(month_date) - 2 + 12, 12) + 1) / 3)                            as fiscal_quarter_number,
        'FY' || case
            when month(month_date) >= 2 then year(month_date) + 1
            else year(month_date)
        end || '-Q' || ceil((mod(month(month_date) - 2 + 12, 12) + 1) / 3)             as fiscal_quarter
    from months
)

select
    month_date,
    fiscal_year,
    fiscal_quarter,
    fiscal_quarter_number,
    calendar_year,
    calendar_month
from fiscal
