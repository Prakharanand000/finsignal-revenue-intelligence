# Cortex Code Session Log — FinSignal

| Date | Surface | What I built | ~Prompts |
|------|---------|--------------|----------|
| 2026-05-18 | Snowsight | DB + warehouse + bronze/silver/gold scaffold (manual SQL) | 0 |

| 2026-05-18 | Snowsight Cortex Code | Synthetic SaaS generator → BRONZE; agent self-recovered from 2 runtime errors; bad-quarter signal validated | ~4 |
| 2026-05-18 | Snowsight Cortex Code | dbt init + 4 silver staging models, 11 schema tests green; agent self-corrected quoted-identifier assumption | ~4 |
| 2026-05-18 | Snowsight Cortex Code | Silver dedup + null-flag verified empirically (617 dupes removed, 0 remaining); README validation notes | ~2 |
| 2026-05-18 | Snowsight Cortex Code | Gold dims: fiscal_calendar + dim_customers; hand-verified fiscal quarter math on 3 boundary cases incl. Jan rollover | ~3 |
| 2026-05-18 | Snowsight Cortex Code | Gold dims built (fiscal_calendar 36 rows, dim_customers 2000); generate_schema_name macro override; fiscal math verified | ~3 |

| 2026-05-18 | Snowsight Cortex Code | Built fct_arr_movements; caught + fixed ARR misclassification (MRR noise vs tier-change); validated bridge identity | ~5 |

| 2026-05-18 | Snowsight Cortex Code | fct_arr_movements v1 caught billing-noise bug (14K→159 real expansions); rebuilt tier-based ARR; bridge identity verified | ~6 |
| 2026-05-18 | Snowsight Cortex Code | Semantic model staged + Streamlit 3-page dashboard + openpyxl quarter-close export | ~4 |

| 2026-05-18 | Snowsight Cortex Code | fct_revenue_waterfall + fct_nrr_cohorts + semantic model + Streamlit dashboard + openpyxl quarter-close export | ~8 |