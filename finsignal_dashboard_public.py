"""
FinSignal — Quarterly Revenue Intelligence Platform
Public deployment version (Streamlit Community Cloud)
Uses snowflake-connector-python + st.secrets for auth
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import snowflake.connector

st.set_page_config(
    page_title="FinSignal — Revenue Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130 0%, #2d3250 100%);
        border: 1px solid #3d4270;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 8px 0;
    }
    .metric-label {
        font-size: 13px;
        color: #8b92a5;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #e8eaf6;
        line-height: 1.1;
    }
    .metric-delta-pos { font-size: 14px; color: #4caf8a; margin-top: 4px; }
    .metric-delta-neg { font-size: 14px; color: #ef5350; margin-top: 4px; }
    .section-header {
        font-size: 22px;
        font-weight: 700;
        color: #e8eaf6;
        margin: 24px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #2d3250;
    }
    .sidebar-info {
        background: #1e2130;
        border-radius: 8px;
        padding: 12px;
        font-size: 12px;
        color: #8b92a5;
        margin-top: 16px;
    }
    div[data-testid="stSelectbox"] label { color: #8b92a5 !important; }
</style>
""", unsafe_allow_html=True)

# ── Snowflake connection ───────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        account   = st.secrets["snowflake"]["account"],
        user      = st.secrets["snowflake"]["user"],
        password  = st.secrets["snowflake"]["password"],
        warehouse = st.secrets["snowflake"]["warehouse"],
        database  = st.secrets["snowflake"]["database"],
        schema    = st.secrets["snowflake"]["schema"],
        role      = st.secrets["snowflake"]["role"],
    )

@st.cache_data(ttl=300)
def query(sql):
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_waterfall():
    return query("SELECT * FROM FINSIGNAL.GOLD.FCT_REVENUE_WATERFALL ORDER BY FISCAL_QUARTER")

@st.cache_data(ttl=300)
def load_nrr():
    return query("SELECT * FROM FINSIGNAL.GOLD.FCT_NRR_COHORTS ORDER BY COHORT_QUARTER, FISCAL_QUARTER")

@st.cache_data(ttl=300)
def load_movements(fq):
    return query(f"""
        SELECT MOVEMENT_TYPE, COUNT(*) AS CUSTOMERS, SUM(ARR_DELTA) AS ARR_DELTA
        FROM FINSIGNAL.GOLD.FCT_ARR_MOVEMENTS
        WHERE FISCAL_QUARTER = '{fq}'
        GROUP BY MOVEMENT_TYPE ORDER BY ARR_DELTA DESC
    """)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bar-chart.png", width=48)
    st.title("FinSignal")
    st.caption("Northwind Cloud | B2B SaaS Analytics")
    st.divider()
    page = st.radio(
        "Navigate",
        ["📈 Revenue Summary", "🌊 ARR Waterfall", "🔄 NRR Cohorts"],
        label_visibility="collapsed"
    )
    st.markdown("""
    <div class="sidebar-info">
    <b>Data:</b> Synthetic Northwind Cloud<br>
    <b>Period:</b> FY2024 – FY2026<br>
    <b>Fiscal year:</b> Feb 1 start<br>
    <b>Built with:</b> Snowflake Cortex Code + dbt
    </div>
    """, unsafe_allow_html=True)

wf_df = load_waterfall()
quarters = wf_df["FISCAL_QUARTER"].tolist()

# ── Plotly theme ──────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e8eaf6", family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="#2d3250", linecolor="#3d4270"),
    yaxis=dict(gridcolor="#2d3250", linecolor="#3d4270"),
)

GREEN = "#4caf8a"
RED   = "#ef5350"
BLUE  = "#5c7cfa"
AMBER = "#ffb74d"

def fmt_arr(v):
    if v is None or pd.isna(v):
        return "N/A"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    return f"${v/1_000:.0f}K"

def metric_card(label, value, delta=None, delta_positive=True):
    delta_html = ""
    if delta is not None:
        css   = "metric-delta-pos" if delta_positive else "metric-delta-neg"
        arrow = "▲" if delta_positive else "▼"
        delta_html = f'<div class="{css}">{arrow} {delta}</div>'
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>"""

# ── Page 1: Revenue Summary ───────────────────────────────────────────────────
if page == "📈 Revenue Summary":
    st.markdown('<div class="section-header">Revenue Summary</div>', unsafe_allow_html=True)

    selected_q = st.selectbox("Fiscal Quarter", quarters, index=len(quarters)-1)
    row        = wf_df[wf_df["FISCAL_QUARTER"] == selected_q].iloc[0]

    beg = row["BEGINNING_ARR"] if pd.notna(row["BEGINNING_ARR"]) else None
    end = row["ENDING_ARR"]
    nna = row["NET_NEW_ARR"]   if pd.notna(row["NET_NEW_ARR"]) else None
    qoq = row["QOQ_GROWTH_PCT"] if pd.notna(row["QOQ_GROWTH_PCT"]) else None
    churn = row["CHURN_ARR"]
    exp   = row["EXPANSION_ARR"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Ending ARR", fmt_arr(end),
            f"{qoq:.1f}% QoQ" if qoq else None, qoq > 0 if qoq else True),
            unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Net New ARR", fmt_arr(nna),
            None), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Churn ARR", fmt_arr(churn),
            "Growth-tier spike" if selected_q == "FY2026-Q3" else None, False),
            unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Expansion ARR", fmt_arr(exp)), unsafe_allow_html=True)

    st.divider()

    # ARR trend line chart
    st.markdown("**Ending ARR Trend — All Quarters**")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=wf_df["FISCAL_QUARTER"], y=wf_df["ENDING_ARR"],
        mode="lines+markers+text",
        line=dict(color=BLUE, width=3),
        marker=dict(size=8, color=BLUE),
        text=[fmt_arr(v) for v in wf_df["ENDING_ARR"]],
        textposition="top center",
        textfont=dict(size=11),
        name="Ending ARR"
    ))
    # Highlight bad quarter
    bq_row = wf_df[wf_df["FISCAL_QUARTER"] == "FY2026-Q3"]
    if not bq_row.empty:
        fig_trend.add_trace(go.Scatter(
            x=["FY2026-Q3"], y=[bq_row["ENDING_ARR"].values[0]],
            mode="markers", marker=dict(size=14, color=RED, symbol="circle"),
            name="FY2026-Q3 (anomaly)"
        ))
    fig_trend.update_layout(
        **PLOTLY_LAYOUT, height=340,
        xaxis_title="Fiscal Quarter", yaxis_title="ARR ($)",
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # QoQ growth bars
    st.markdown("**QoQ Growth % — All Quarters**")
    qoq_df = wf_df.dropna(subset=["QOQ_GROWTH_PCT"]).copy()
    colors = [RED if v < 0 else GREEN for v in qoq_df["QOQ_GROWTH_PCT"]]
    fig_qoq = go.Figure(go.Bar(
        x=qoq_df["FISCAL_QUARTER"], y=qoq_df["QOQ_GROWTH_PCT"],
        marker_color=colors,
        text=[f"{v:.1f}%" for v in qoq_df["QOQ_GROWTH_PCT"]],
        textposition="outside"
    ))
    fig_qoq.update_layout(**PLOTLY_LAYOUT, height=280, yaxis_title="QoQ Growth (%)")
    st.plotly_chart(fig_qoq, use_container_width=True)

# ── Page 2: ARR Waterfall ─────────────────────────────────────────────────────
elif page == "🌊 ARR Waterfall":
    st.markdown('<div class="section-header">ARR Waterfall Bridge</div>', unsafe_allow_html=True)
    st.caption("How ARR changed from beginning to end of the fiscal quarter.")

    selected_q = st.selectbox("Fiscal Quarter", quarters, index=len(quarters)-1)
    row        = wf_df[wf_df["FISCAL_QUARTER"] == selected_q].iloc[0]
    beg        = float(row["BEGINNING_ARR"]) if pd.notna(row["BEGINNING_ARR"]) else 0.0

    labels  = ["Beginning", "New", "Reactivation", "Expansion", "Contraction", "Churn", "Ending"]
    values  = [beg, float(row["NEW_ARR"]), float(row["REACTIVATION_ARR"]),
               float(row["EXPANSION_ARR"]), float(row["CONTRACTION_ARR"]),
               float(row["CHURN_ARR"]), float(row["ENDING_ARR"])]
    measure = ["absolute","relative","relative","relative","relative","relative","absolute"]

    marker_colors = [BLUE, GREEN, GREEN, GREEN, RED, RED, BLUE]

    fig_wf = go.Figure(go.Waterfall(
        name="ARR Bridge", orientation="v",
        measure=measure, x=labels, y=values,
        connector=dict(line=dict(color="#3d4270", width=1.5, dash="dot")),
        increasing=dict(marker=dict(color=GREEN)),
        decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=BLUE)),
        text=[fmt_arr(v) for v in values],
        textposition="outside",
        textfont=dict(size=12, color="#e8eaf6"),
    ))
    fig_wf.update_layout(
        **PLOTLY_LAYOUT, height=480,
        title=dict(text=f"ARR Bridge — {selected_q}", font=dict(size=18, color="#e8eaf6")),
        yaxis_title="ARR ($)",
        showlegend=False
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # Movement detail table
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("**Movement Detail**")
        mvmt_df = load_movements(selected_q)
        mvmt_df["ARR_DELTA"] = mvmt_df["ARR_DELTA"].apply(fmt_arr)
        st.dataframe(mvmt_df, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("**Key Metrics**")
        c1, c2 = st.columns(2)
        c1.metric("Ending ARR",   fmt_arr(float(row["ENDING_ARR"])))
        c2.metric("Net New ARR",  fmt_arr(float(row["NET_NEW_ARR"])) if pd.notna(row["NET_NEW_ARR"]) else "N/A")
        c1.metric("Churn ARR",    fmt_arr(float(row["CHURN_ARR"])))
        c2.metric("QoQ Growth",   f"{row['QOQ_GROWTH_PCT']:.1f}%" if pd.notna(row["QOQ_GROWTH_PCT"]) else "N/A")

    # All quarters mini-bars for churn
    st.divider()
    st.markdown("**Churn ARR by Quarter (all periods)**")
    fig_churn = go.Figure(go.Bar(
        x=wf_df["FISCAL_QUARTER"],
        y=wf_df["CHURN_ARR"].abs(),
        marker_color=[RED if q == "FY2026-Q3" else "#5c7cfa" for q in wf_df["FISCAL_QUARTER"]],
        text=[fmt_arr(v) for v in wf_df["CHURN_ARR"].abs()],
        textposition="outside"
    ))
    fig_churn.update_layout(
        **PLOTLY_LAYOUT, height=300,
        yaxis_title="Churn ARR ($)",
        annotations=[dict(
            x="FY2026-Q3", y=wf_df[wf_df["FISCAL_QUARTER"]=="FY2026-Q3"]["CHURN_ARR"].abs().values[0] * 1.15,
            text="⚠ Anomaly Quarter", showarrow=False, font=dict(color=AMBER, size=12)
        )]
    )
    st.plotly_chart(fig_churn, use_container_width=True)

# ── Page 3: NRR Cohorts ───────────────────────────────────────────────────────
elif page == "🔄 NRR Cohorts":
    st.markdown('<div class="section-header">Net Revenue Retention — Cohort Analysis</div>',
                unsafe_allow_html=True)
    st.caption("NRR tracks existing customers forward from their signup quarter. New logos excluded. NRR > 100% = existing base is growing.")

    nrr_df = load_nrr()
    pivot  = nrr_df.pivot(index="COHORT_QUARTER", columns="FISCAL_QUARTER", values="NRR_PCT")

    # Heatmap with plotly
    z      = pivot.values
    x_labs = pivot.columns.tolist()
    y_labs = pivot.index.tolist()

    fig_heat = go.Figure(go.Heatmap(
        z=z, x=x_labs, y=y_labs,
        colorscale=[
            [0.00, "#7f1d1d"], [0.40, "#ef5350"],
            [0.50, "#f59e0b"], [0.60, "#fbbf24"],
            [0.63, "#4caf8a"], [1.00, "#166534"],
        ],
        zmin=60, zmax=160,
        text=[[f"{v:.0f}%" if not pd.isna(v) else "" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=12, color="white"),
        hovertemplate="Cohort: %{y}<br>Quarter: %{x}<br>NRR: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            title="NRR %",
            tickvals=[60, 80, 100, 120, 140, 160],
            ticktext=["60%","80%","100%","120%","140%","160%"],
            bgcolor="rgba(0,0,0,0)",
            tickfont=dict(color="#e8eaf6")
        )
    ))
    fig_heat.update_layout(
        **PLOTLY_LAYOUT, height=480,
        title=dict(text="NRR % Heatmap — Red < 80%, Yellow 80-100%, Green > 100%",
                   font=dict(size=16, color="#e8eaf6")),
        xaxis=dict(title="Measurement Quarter", tickangle=-30, gridcolor="#2d3250"),
        yaxis=dict(title="Cohort Quarter", autorange="reversed", gridcolor="#2d3250"),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # Cohort trend line
    st.divider()
    st.markdown("**NRR Trend — Select a Cohort**")
    cohorts         = sorted(nrr_df["COHORT_QUARTER"].unique().tolist())
    selected_cohort = st.selectbox("Cohort", cohorts, index=len(cohorts)//2)
    trend           = nrr_df[nrr_df["COHORT_QUARTER"] == selected_cohort].sort_values("FISCAL_QUARTER")

    fig_trend = go.Figure()
    fig_trend.add_hline(y=100, line_dash="dash", line_color=AMBER,
                         annotation_text="100% baseline", annotation_font_color=AMBER)
    fig_trend.add_trace(go.Scatter(
        x=trend["FISCAL_QUARTER"], y=trend["NRR_PCT"],
        mode="lines+markers",
        line=dict(color=BLUE, width=3),
        marker=dict(size=9,
                    color=[GREEN if v >= 100 else AMBER if v >= 80 else RED
                           for v in trend["NRR_PCT"]]),
        text=[f"{v:.1f}%" for v in trend["NRR_PCT"]],
        textposition="top center",
        fill="tozeroy", fillcolor="rgba(92,124,250,0.08)"
    ))
    fig_trend.update_layout(
        **PLOTLY_LAYOUT, height=300,
        title=dict(text=f"NRR Trend — Cohort {selected_cohort}",
                   font=dict(size=16, color="#e8eaf6")),
        yaxis_title="NRR %", xaxis_title="Fiscal Quarter",
        yaxis=dict(range=[0, max(150, trend["NRR_PCT"].max() * 1.1)], gridcolor="#2d3250")
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Summary stats
    st.divider()
    st.markdown("**Cohort Summary — Latest Quarter NRR**")
    latest_q   = nrr_df["FISCAL_QUARTER"].max()
    latest_nrr = nrr_df[nrr_df["FISCAL_QUARTER"] == latest_q][["COHORT_QUARTER","NRR_PCT"]].copy()
    latest_nrr["Signal"] = latest_nrr["NRR_PCT"].apply(
        lambda v: "🟢 Strong" if v >= 100 else ("🟡 At Risk" if v >= 80 else "🔴 Churning"))
    latest_nrr["NRR_PCT"] = latest_nrr["NRR_PCT"].apply(lambda v: f"{v:.1f}%")
    st.dataframe(latest_nrr.rename(columns={"COHORT_QUARTER":"Cohort","NRR_PCT":"NRR %"}),
                 use_container_width=True, hide_index=True)
