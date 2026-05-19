# FinSignal — Quarterly Revenue Intelligence Platform

[GitHub](https://github.com/Prakharanand000/finsignal-revenue-intelligence) | [Live App](https://app.snowflake.com/us-east-1/uoc61675/#/streamlit-apps/FINSIGNAL.GOLD.FINSIGNAL_DASHBOARD)

> **Built with Snowflake Cortex Code | dbt | Streamlit | Cortex Analyst**
> A production-grade Snowflake-native finance analytics platform simulating the quarterly revenue intelligence stack a Strategic Finance team actually runs.

**Live App:** `https://app.snowflake.com/us-east-1/uoc61675/#/streamlit-apps/FINSIGNAL.GOLD.FINSIGNAL_DASHBOARD`
**Cortex Code sessions:** ~30 logged sessions, built in a single day (2026-05-18)
**See:** [`cortex_session_log.md`](./cortex_session_log.md) for session-by-session evidence

---

## Architecture

```
SYNTHETIC DATA GENERATOR (Snowpark Python)
              |
              v
    FINSIGNAL.BRONZE
    RAW_CUSTOMERS | RAW_SUBSCRIPTIONS | RAW_INVOICES | RAW_USAGE_EVENTS
    (2,000 customers, FY2024-FY2026, Feb-1 fiscal year, deliberate FY2026-Q3 anomaly)
              |
              v  dbt staging layer (views, FINSIGNAL.SILVER)
    stg_customers | stg_subscriptions | stg_invoices | stg_usage_events
    - Quoted-lowercase bronze identifiers normalized
    - ROW_NUMBER() window dedup: 31,469 → 30,852 invoices (617 dupes removed)
    - NULL plan_tier flagged (is_missing_tier), not dropped
    - 11 dbt schema tests, all green
              |
              v  dbt marts layer (tables, FINSIGNAL.GOLD)
    dim_fiscal_calendar   FY starts Feb 1, Q1=Feb-Apr, Q2=May-Jul, Q3=Aug-Oct, Q4=Nov-Jan
    dim_customers         signup fiscal quarter, current status via window function
    fct_arr_movements     tier-based ARR movement classification (LAG window)
    fct_revenue_waterfall quarterly ARR bridge with QoQ growth %
    fct_nrr_cohorts       net revenue retention by cohort, new logos excluded
              |
     +--------+----------+------------------+
     v        v          v                  v
 CORTEX   STREAMLIT   CORTEX ANALYST    QUARTER-CLOSE
 ANALYST  DASHBOARD   SEMANTIC MODEL    EXCEL EXPORT
 (NL Q&A) (3 pages,   (YAML, staged,    (4-tab openpyxl-
          deployed)    synonyms)          style, stdlib)
```

---

## What This Project Demonstrates

### 1. Cortex Code / AI-Assisted Development
Built entirely through Snowflake Cortex Code (Snowsight agent, Plan mode) across ~30 logged sessions in a single day. Key behaviors documented:

- **Steered the agent on wrong assumptions:** CoCo initially claimed bronze columns were case-insensitive unquoted identifiers. I had it verify empirically — it discovered they were quoted-lowercase from `write_pandas` and corrected all model SQL before running. One missed assumption would have broken all 4 staging models.
- **Caught an error in my own spec:** CoCo flagged that Aug–Oct 2025 maps to FY2026-Q3, not Q2 as I had labeled it. I traced the fiscal quarter math by hand, confirmed the agent was right, and corrected the spec before approving.
- **Reviewed outputs before approving:** Used Plan mode for every build step. Reviewed distribution results and fiscal calendar logic before proceeding.

### 2. Fiscal Year / Earnings Cycle Ownership
- Implemented a **Feb-1 fiscal calendar** (FY ≠ calendar year). Fiscal quarter formula: `fiscal_month_number = mod(calendar_month - 2 + 12, 12) + 1`, `fiscal_quarter = ceil(fiscal_month_number / 3)`. Verified on 3 boundary cases before approving.
- Built a **quarter-close routine** that snapshots ending ARR, computes QoQ/YoY variance, and emits an IR-style 4-tab Excel export for any fiscal quarter.
- **ARR bridge identity verified:** Beginning + New + Reactivation + Expansion − Contraction − Churn = Ending ARR, within ~1%. Residuals explained by intra-quarter round-trips (new+churn in same quarter), not model errors.

### 3. Finance Domain Vocabulary — Implemented, Not Listed

**ARR Movement Classification Bug Caught and Fixed:**
The initial `fct_arr_movements` model used `mrr * 12` which had ±10% random billing variance per month. This produced **14,277 false expansion/contraction events** on 2,000 customers — every random billing wiggle was classified as a tier change. Caught this by inspecting the movement distribution. Rebuilt using fixed tier-based ARR (Starter $2,400 / Growth $14,400 / Enterprise $72,000) so only actual plan-tier transitions generate movement rows. Final: **159 real expansions, 61 real contractions** — consistent with the simulated 8% annual expansion rate.

**Key metrics implemented:**
| Metric | How it's built |
|---|---|
| **ARR** | Fixed tier-based annual value; moves only on plan-tier change |
| **NRR** | Cohort ARR tracked forward from signup quarter; new logos excluded; NRR > 100% = existing base growing |
| **Bookings** | `movement_type = 'new'` in `fct_arr_movements` |
| **Revenue Waterfall** | Quarterly bridge: beginning + [new, reactivation, expansion, contraction, churn] = ending |
| **Churn** | Plan-tier-driven; `status = 'churned'` maps to `tier_arr = 0`; classified via LAG window |

---

## Data Model

### Bronze (raw, FINSIGNAL.BRONZE)
Synthetic Northwind Cloud B2B SaaS data generated via Snowpark Python:
- **2,000 customers**, FY2024–FY2026, Feb-1 fiscal year
- **Deliberate anomaly:** Growth-tier churn doubled in Aug–Oct 2025 (FY2026-Q3)
- **Injected messiness:** ~2% duplicate invoices, ~1% NULL plan tiers, ~5% late-dated invoices
- Deterministic via `np.random.seed(42)` — fully reproducible

### Silver (cleaned, FINSIGNAL.SILVER) — dbt views
| Model | Key transformation |
|---|---|
| `stg_customers` | Normalize casing, cast signup_date |
| `stg_subscriptions` | Normalize, flag NULL plan_tier as `is_missing_tier` (not dropped) |
| `stg_invoices` | `ROW_NUMBER()` dedup by invoice_id — 31,469 → 30,852 rows |
| `stg_usage_events` | Normalize, cast event_date |

### Gold (metrics, FINSIGNAL.GOLD) — dbt tables
| Model | Description |
|---|---|
| `dim_fiscal_calendar` | 36 months, Feb-1 FY, verified boundary cases |
| `dim_customers` | Enriched with first active month, signup fiscal quarter, current status |
| `fct_arr_movements` | Tier-based ARR movement classification (new/expansion/contraction/churn/reactivation) |
| `fct_revenue_waterfall` | Quarterly ARR bridge with QoQ growth % |
| `fct_nrr_cohorts` | NRR by signup cohort, new logos excluded |

---

## Key Design Decisions and Why

**Bronze → Silver identifier normalization:** `write_pandas()` creates quoted-lowercase column names in Snowflake. Silver staging models normalize to standard unquoted identifiers as their first transformation. This is why the bronze layer requires `"month"` (quoted) but silver exposes `MONTH` (standard). Documented after catching this empirically.

**NULL tier flagging vs. dropping:** ~1% of subscription rows have NULL plan_tier (simulated upstream data gap). Dropping them would silently understate ARR by ~1%. Instead, `stg_subscriptions` flags them with `is_missing_tier = TRUE` and `fct_arr_movements` explicitly excludes them with a model comment explaining the decision.

**Fixed tier ARR vs. MRR-based ARR:** Using `mrr * 12` caused billing noise (±10% random variance) to appear as 14,277 expansion/contraction events. Finance ARR is driven by contractual tier, not billed amount. Rebuilt on fixed tier values — only real tier changes appear in the movement table.

**Quarter-close Excel without openpyxl:** Snowflake notebook service has no external network access. Rebuilt the Excel export using Python stdlib `zipfile` + `xml.etree.ElementTree` (XLSX is a ZIP of XML files). Output opens correctly in Excel. Styling would require an external access integration — documented as a known limitation.

---

## Bad Quarter Narrative (FY2026-Q3)

The seeded anomaly is detectable and quantifiable in the data:

| Quarter | Churn ARR | QoQ Growth |
|---|---|---|
| FY2026-Q2 | -$972K | +5.38% |
| **FY2026-Q3** | **-$1.26M** | **+4.53%** |
| FY2026-Q4 | -$1.24M | +7.61% |

Churn spiked 30% in Q3 (Growth-tier doubled to 3%/month in Aug–Oct 2025). QoQ growth hit its lowest point. The contraction line actually *decreased* because many Growth-tier customers churned outright rather than downgrading — a secondary signal a Finance Analytics person would be expected to surface in a QBR.

---

## Screenshots

*Add screenshots to `/screenshots/` folder after deployment:*
- `screenshots/01_revenue_summary.png` — Revenue Summary page with metric cards
- `screenshots/02_arr_waterfall.png` — ARR Waterfall bar chart
- `screenshots/03_nrr_cohorts.png` — NRR cohort heatmap

---

## Repository Structure

```
finsignal-revenue-intelligence/
├── generate_billing_data.py          # Snowpark data generator → BRONZE
├── finsignal_dashboard.py            # Streamlit app (3 pages, deployed to Snowflake)
├── finsignal_semantic_model.yaml     # Cortex Analyst semantic model
├── finsignal_quarter_close.py        # Quarter-close Excel export routine
├── cortex_session_log.md             # Cortex Code session evidence log
├── finsignal_dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── macros/
│   │   └── generate_schema_name.sql  # Ensures gold models land in GOLD (not SILVER_GOLD)
│   └── models/
│       ├── sources.yml
│       ├── staging/
│       │   ├── stg_customers.sql
│       │   ├── stg_subscriptions.sql
│       │   ├── stg_invoices.sql
│       │   ├── stg_usage_events.sql
│       │   └── schema.yml
│       └── marts/
│           ├── dim_fiscal_calendar.sql
│           ├── dim_customers.sql
│           ├── fct_arr_movements.sql
│           ├── fct_revenue_waterfall.sql
│           ├── fct_nrr_cohorts.sql
│           └── schema.yml
└── screenshots/
```

---

## dbt Test Results
```
dbt run  — PASS=9 (4 staging views + 5 gold tables)
dbt test — PASS=20, WARN=0, ERROR=0, SKIP=0
```

