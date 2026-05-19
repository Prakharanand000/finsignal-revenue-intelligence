# Cortex Code Session Log — FinSignal
# Built entirely in one day: 2026-05-18

| Date       | Surface               | What I built                                                                                      | ~Prompts |
|------------|-----------------------|---------------------------------------------------------------------------------------------------|----------|
| 2026-05-18 | Snowsight SQL         | DB + warehouse + bronze/silver/gold schema scaffold (manual infra setup)                          | 0        |
| 2026-05-18 | Snowsight Cortex Code | Synthetic SaaS data generator → BRONZE (4 tables, 2K customers, FY2024-FY2026); Plan-mode review; agent self-recovered from 2 runtime errors (.dt.strftime bug + SYSADMIN role error); bad-quarter signal validated | ~4 |
| 2026-05-18 | Snowsight Cortex Code | dbt project init + 4 silver staging models; 11 schema tests green; agent self-corrected quoted-lowercase identifier assumption after empirical re-verification | ~4 |
| 2026-05-18 | Snowsight Cortex Code | Silver validation: dedup (31,469→30,852), null-tier flagging (300 rows), dbt test PASS=11        | ~2       |
| 2026-05-18 | Snowsight Cortex Code | Gold dims: dim_fiscal_calendar + dim_customers; hand-verified fiscal quarter math on 3 boundary cases (Feb, Aug, Jan); caught and corrected fiscal-quarter labeling error (Q2→Q3) in my own spec | ~3 |
| 2026-05-18 | Snowsight Cortex Code | fct_arr_movements v1: caught ARR misclassification bug — MRR billing noise (±10%) producing 14,277 false expansion/contraction events; rebuilt on fixed tier-based ARR → 159 real expansions | ~6 |
| 2026-05-18 | Snowsight Cortex Code | fct_revenue_waterfall + fct_nrr_cohorts; bad-quarter churn spike confirmed in FY2026-Q3 (+30% vs prior quarter) | ~4 |
| 2026-05-18 | Snowsight Cortex Code | Cortex Analyst semantic model (YAML, staged); 3-page Streamlit dashboard deployed to Snowflake   | ~4       |
| 2026-05-18 | Snowsight Cortex Code | Quarter-close Excel export (4 tabs); matplotlib/openpyxl not available in notebook runtime — agent rebuilt using stdlib zipfile + xml.etree.ElementTree | ~3 |

## Session Summary
- **Total Cortex Code sessions (logged):** ~30 prompts across 9 sessions
- **Date:** 2026-05-18 (built in a single day)
- **Surface:** Snowsight Cortex Code agent (Plan mode used for all build steps)

## Notable Agent Behaviors
1. Self-corrected a quoted-lowercase identifier assumption mid-build — discovered empirically rather than assuming
2. Caught a fiscal-quarter labeling error in my own spec (Q2 vs Q3) before I shipped an internally inconsistent calendar
3. Self-recovered from 2 runtime errors in the data generator without intervention
4. Rebuilt the Excel export using only Python stdlib when openpyxl/matplotlib were unavailable in the notebook runtime
5. Flagged the ARR billing-noise bug in the movement distribution — prompted a full model rebuild
