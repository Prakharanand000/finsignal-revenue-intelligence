import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(layout="wide", page_title="FinSignal — Revenue Intelligence")
st.title("FinSignal — Revenue Intelligence")
st.caption("Northwind Cloud | B2B SaaS | FY2024–FY2026 | Built with Snowflake Cortex Code + dbt")

page = st.sidebar.radio("Navigate", ["Revenue Summary", "ARR Waterfall", "NRR Cohorts"])

@st.cache_data
def load_waterfall():
    return session.sql(
        "SELECT * FROM FINSIGNAL.GOLD.FCT_REVENUE_WATERFALL ORDER BY FISCAL_QUARTER"
    ).to_pandas()

@st.cache_data
def load_nrr():
    return session.sql(
        "SELECT * FROM FINSIGNAL.GOLD.FCT_NRR_COHORTS ORDER BY COHORT_QUARTER, FISCAL_QUARTER"
    ).to_pandas()

waterfall_df = load_waterfall()
quarters = waterfall_df["FISCAL_QUARTER"].tolist()

# ── Page 1: Revenue Summary ──────────────────────────────────────────────────
if page == "Revenue Summary":
    st.header("Revenue Summary")
    selected_q = st.selectbox("Fiscal Quarter", quarters, index=len(quarters) - 1)
    row = waterfall_df[waterfall_df["FISCAL_QUARTER"] == selected_q].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ending ARR", f"${row['ENDING_ARR']:,.0f}")
    col2.metric(
        "QoQ Growth",
        f"{row['QOQ_GROWTH_PCT']:.2f}%" if pd.notna(row['QOQ_GROWTH_PCT']) else "N/A"
    )
    col3.metric(
        "Net New ARR",
        f"${row['NET_NEW_ARR']:,.0f}" if pd.notna(row['NET_NEW_ARR']) else "N/A"
    )
    col4.metric("Churn ARR", f"${row['CHURN_ARR']:,.0f}")

    st.divider()
    st.subheader("All Quarters — Waterfall Summary")
    display_cols = ["FISCAL_QUARTER", "BEGINNING_ARR", "NEW_ARR", "EXPANSION_ARR",
                    "CONTRACTION_ARR", "CHURN_ARR", "ENDING_ARR", "QOQ_GROWTH_PCT"]
    st.dataframe(
        waterfall_df[display_cols].style.format({
            "BEGINNING_ARR": "${:,.0f}", "NEW_ARR": "${:,.0f}",
            "EXPANSION_ARR": "${:,.0f}", "CONTRACTION_ARR": "${:,.0f}",
            "CHURN_ARR": "${:,.0f}", "ENDING_ARR": "${:,.0f}",
            "QOQ_GROWTH_PCT": "{:.2f}%"
        }),
        use_container_width=True
    )

# ── Page 2: ARR Waterfall ─────────────────────────────────────────────────────
elif page == "ARR Waterfall":
    st.header("ARR Waterfall Bridge")
    selected_q = st.selectbox("Fiscal Quarter", quarters, index=len(quarters) - 1)
    row = waterfall_df[waterfall_df["FISCAL_QUARTER"] == selected_q].iloc[0]

    beginning = row["BEGINNING_ARR"] if pd.notna(row["BEGINNING_ARR"]) else 0

    bridge_data = pd.DataFrame({
        "Component": ["Beginning ARR", "New", "Reactivation", "Expansion",
                       "Contraction", "Churn", "Ending ARR"],
        "ARR ($)": [
            beginning,
            row["NEW_ARR"],
            row["REACTIVATION_ARR"],
            row["EXPANSION_ARR"],
            row["CONTRACTION_ARR"],
            row["CHURN_ARR"],
            row["ENDING_ARR"]
        ]
    })

    col1, col2 = st.columns([2, 1])
    with col1:
        st.bar_chart(bridge_data.set_index("Component"), height=400)
    with col2:
        st.subheader(f"FY Quarter: {selected_q}")
        for _, r in bridge_data.iterrows():
            sign = "+" if r["ARR ($)"] > 0 else ""
            color = "green" if r["ARR ($)"] > 0 else "red"
            if r["Component"] in ["Beginning ARR", "Ending ARR"]:
                st.write(f"**{r['Component']}:** ${r['ARR ($)']:,.0f}")
            else:
                st.write(f"{r['Component']}: {sign}${r['ARR ($)']:,.0f}")

    st.divider()
    st.subheader("Movement Detail — " + selected_q)
    movements = session.sql(f"""
        SELECT MOVEMENT_TYPE, COUNT(*) AS CUSTOMERS, SUM(ARR_DELTA) AS ARR_DELTA
        FROM FINSIGNAL.GOLD.FCT_ARR_MOVEMENTS
        WHERE FISCAL_QUARTER = '{selected_q}'
        GROUP BY MOVEMENT_TYPE ORDER BY ARR_DELTA DESC
    """).to_pandas()
    st.dataframe(movements, use_container_width=True)

# ── Page 3: NRR Cohorts ───────────────────────────────────────────────────────
elif page == "NRR Cohorts":
    st.header("Net Revenue Retention — Cohort Analysis")
    st.caption("NRR tracks existing customers forward from their signup quarter, excluding new logos.")

    nrr_df = load_nrr()
    pivot = nrr_df.pivot(index="COHORT_QUARTER", columns="FISCAL_QUARTER", values="NRR_PCT")

    def color_nrr(val):
        if pd.isna(val):
            return ""
        if val >= 100:
            return "background-color: #c6efce; color: #276221"
        elif val >= 80:
            return "background-color: #ffeb9c; color: #9c5700"
        else:
            return "background-color: #ffc7ce; color: #9c0006"

    st.dataframe(
        pivot.style.applymap(color_nrr).format("{:.1f}%", na_rep=""),
        use_container_width=True,
        height=500
    )

    st.divider()
    st.subheader("NRR Trend — Select a Cohort")
    cohorts = nrr_df["COHORT_QUARTER"].unique().tolist()
    selected_cohort = st.selectbox("Cohort", cohorts)
    cohort_trend = nrr_df[nrr_df["COHORT_QUARTER"] == selected_cohort]
    st.line_chart(cohort_trend.set_index("FISCAL_QUARTER")["NRR_PCT"], height=300)
