"""
FinSignal — Quarterly Revenue Intelligence Platform
Public deployment version (Streamlit Community Cloud)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import snowflake.connector
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PrivateFormat, NoEncryption

st.set_page_config(
    page_title="FinSignal — Revenue Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #f7f8fa; }
    .section-header {
        font-size: 24px;
        font-weight: 700;
        color: #111111;
        margin-bottom: 4px;
    }
    .sub-caption { color: #444444; font-size: 14px; margin-bottom: 20px; }
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 18px 20px;
        margin: 4px 0;
    }
    .metric-label { font-size: 12px; color: #555555; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.04em; }
    .metric-value { font-size: 26px; font-weight: 700; color: #111111; margin-top: 4px; }
    .metric-delta-pos { font-size: 13px; color: #1a7f4e; margin-top: 2px; }
    .metric-delta-neg { font-size: 13px; color: #c0392b; margin-top: 2px; }
    .sidebar-info { background: #eef0f5; border-radius: 8px; padding: 12px;
                    font-size: 12px; color: #444444; margin-top: 8px; }
    h1, h2, h3, p, label { color: #111111 !important; }
</style>
""", unsafe_allow_html=True)

# ── Connection ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    sf = st.secrets["snowflake"]
    private_key = load_pem_private_key(
        sf["private_key"].encode(), password=None
    ).private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    return snowflake.connector.connect(
        account   = sf["account"],
        user      = sf["user"],
        private_key = private_key,
        warehouse = sf["warehouse"],
        database  = sf["database"],
        schema    = sf["schema"],
        role      = sf["role"],
    )

@st.cache_data(ttl=300)
def query(sql):
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)

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
    st.markdown("## 📊 FinSignal")
    st.markdown("**Northwind Cloud | B2B SaaS Analytics**")
    st.divider()
    page = st.radio(
        "Navigate",
        ["📈 Revenue Summary", "🌊 ARR Waterfall", "🔄 NRR Cohorts"],
        label_visibility="collapsed"
    )
    st.markdown("""
    <div class="sidebar-info">
    <b>Data:</b> Synthetic Northwind Cloud<br>
    <b>Period:</b> FY2024 - FY2026<br>
    <b>Fiscal year:</b> Feb 1 start<br>
    <b>Built with:</b> Snowflake Cortex Code + dbt
    </div>
    """, unsafe_allow_html=True)

wf_df = load_waterfall()
quarters = wf_df["FISCAL_QUARTER"].tolist()

# Plotly base layout — light theme
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#f7f8fa",
    font=dict(color="#111111", family="Inter, sans-serif", size=12),
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(gridcolor="#e0e0e0", linecolor="#cccccc", tickfont=dict(color="#111111")),
    yaxis=dict(gridcolor="#e0e0e0", linecolor="#cccccc", tickfont=dict(color="#111111")),
)

GREEN = "#1a7f4e"
RED   = "#c0392b"
BLUE  = "#2563eb"
AMBER = "#d97706"

def fmt(v):
    if v is None or pd.isna(v): return "N/A"
    if abs(v) >= 1_000_000: return f"${v/1_000_000:.2f}M"
    return f"${v/1_000:.0f}K"

def card(label, value, delta=None, pos=True):
    d = ""
    if delta:
        css = "metric-delta-pos" if pos else "metric-delta-neg"
        arrow = "▲" if pos else "▼"
        d = f'<div class="{css}">{arrow} {delta}</div>'
    return f"""<div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>{d}
    </div>"""

# ── Page 1: Revenue Summary ───────────────────────────────────────────────────
if page == "📈 Revenue Summary":
    st.markdown('<div class="section-header">Revenue Summary</div>', unsafe_allow_html=True)

    selected_q = st.selectbox("Fiscal Quarter", quarters, index=len(quarters)-1)
    row = wf_df[wf_df["FISCAL_QUARTER"] == selected_q].iloc[0]

    end  = float(row["ENDING_ARR"])
    nna  = float(row["NET_NEW_ARR"])  if pd.notna(row["NET_NEW_ARR"])  else None
    qoq  = float(row["QOQ_GROWTH_PCT"]) if pd.notna(row["QOQ_GROWTH_PCT"]) else None
    churn = float(row["CHURN_ARR"])
    exp   = float(row["EXPANSION_ARR"])

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(card("Ending ARR",    fmt(end),
        f"{qoq:.1f}% QoQ" if qoq else None, (qoq or 0) > 0), unsafe_allow_html=True)
    with c2: st.markdown(card("Net New ARR",   fmt(nna)), unsafe_allow_html=True)
    with c3: st.markdown(card("Churn ARR",     fmt(churn),
        "Spike quarter" if selected_q == "FY2026-Q3" else None, False), unsafe_allow_html=True)
    with c4: st.markdown(card("Expansion ARR", fmt(exp)), unsafe_allow_html=True)

    st.divider()

    # ARR trend
    st.markdown("**Ending ARR Trend**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=wf_df["FISCAL_QUARTER"], y=wf_df["ENDING_ARR"],
        mode="lines+markers+text",
        line=dict(color=BLUE, width=3),
        marker=dict(size=8, color=BLUE),
        text=[fmt(v) for v in wf_df["ENDING_ARR"]],
        textposition="top center",
        textfont=dict(size=11, color="#111111"),
        name="Ending ARR"
    ))
    bq = wf_df[wf_df["FISCAL_QUARTER"] == "FY2026-Q3"]
    if not bq.empty:
        fig.add_trace(go.Scatter(
            x=["FY2026-Q3"], y=[float(bq["ENDING_ARR"].values[0])],
            mode="markers", marker=dict(size=14, color=RED, symbol="circle"),
            name="FY2026-Q3 anomaly"
        ))
    fig.update_layout(**PL, height=320,
        title=dict(text="ARR by Fiscal Quarter", font=dict(color="#111111", size=15)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#111111")))
    st.plotly_chart(fig, use_container_width=True)

    # QoQ bars
    st.markdown("**QoQ Growth %**")
    qoq_df = wf_df.dropna(subset=["QOQ_GROWTH_PCT"]).copy()
    fig2 = go.Figure(go.Bar(
        x=qoq_df["FISCAL_QUARTER"],
        y=qoq_df["QOQ_GROWTH_PCT"],
        marker_color=[RED if v < 0 else GREEN for v in qoq_df["QOQ_GROWTH_PCT"]],
        text=[f"{v:.1f}%" for v in qoq_df["QOQ_GROWTH_PCT"]],
        textposition="outside",
        textfont=dict(color="#111111")
    ))
    fig2.update_layout(**PL, height=260,
        title=dict(text="Quarter-over-Quarter Growth", font=dict(color="#111111", size=15)),
        yaxis_title="QoQ Growth (%)")
    st.plotly_chart(fig2, use_container_width=True)

# ── Page 2: ARR Waterfall ─────────────────────────────────────────────────────
elif page == "🌊 ARR Waterfall":
    st.markdown('<div class="section-header">ARR Waterfall Bridge</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-caption">How ARR changed from beginning to end of the fiscal quarter.</div>',
                unsafe_allow_html=True)

    selected_q = st.selectbox("Fiscal Quarter", quarters, index=len(quarters)-1)
    row = wf_df[wf_df["FISCAL_QUARTER"] == selected_q].iloc[0]
    beg = float(row["BEGINNING_ARR"]) if pd.notna(row["BEGINNING_ARR"]) else 0.0

    labels  = ["Beginning", "New", "Reactivation", "Expansion", "Contraction", "Churn", "Ending"]
    values  = [beg, float(row["NEW_ARR"]), float(row["REACTIVATION_ARR"]),
               float(row["EXPANSION_ARR"]), float(row["CONTRACTION_ARR"]),
               float(row["CHURN_ARR"]), float(row["ENDING_ARR"])]
    measure = ["absolute","relative","relative","relative","relative","relative","absolute"]

    fig = go.Figure(go.Waterfall(
        name="ARR Bridge", orientation="v",
        measure=measure, x=labels, y=values,
        connector=dict(line=dict(color="#cccccc", width=1.5, dash="dot")),
        increasing=dict(marker=dict(color=GREEN)),
        decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=BLUE)),
        text=[fmt(v) for v in values],
        textposition="outside",
        textfont=dict(size=12, color="#111111"),
    ))
    fig.update_layout(
        **PL, height=460, showlegend=False,
        title=dict(text=f"ARR Bridge - {selected_q}", font=dict(color="#111111", size=16))
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("**Movement Detail**")
        mv = load_movements(selected_q)
        mv["ARR_DELTA"] = mv["ARR_DELTA"].apply(lambda v: fmt(float(v)))
        st.dataframe(mv, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("**Quarter Metrics**")
        st.metric("Ending ARR",  fmt(float(row["ENDING_ARR"])))
        st.metric("Churn ARR",   fmt(float(row["CHURN_ARR"])))
        st.metric("QoQ Growth",  f"{row['QOQ_GROWTH_PCT']:.1f}%" if pd.notna(row["QOQ_GROWTH_PCT"]) else "N/A")

    st.divider()
    st.markdown("**Churn ARR by Quarter**")
    fig3 = go.Figure(go.Bar(
        x=wf_df["FISCAL_QUARTER"],
        y=wf_df["CHURN_ARR"].abs(),
        marker_color=[RED if q == "FY2026-Q3" else BLUE for q in wf_df["FISCAL_QUARTER"]],
        text=[fmt(float(v)) for v in wf_df["CHURN_ARR"].abs()],
        textposition="outside",
        textfont=dict(color="#111111")
    ))
    fig3.update_layout(**PL, height=280,
        title=dict(text="Churn ARR by Quarter (red = anomaly)", font=dict(color="#111111", size=15)),
        yaxis_title="Churn ARR ($)")
    st.plotly_chart(fig3, use_container_width=True)

# ── Page 3: NRR Cohorts ───────────────────────────────────────────────────────
elif page == "🔄 NRR Cohorts":
    st.markdown('<div class="section-header">Net Revenue Retention - Cohort Analysis</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sub-caption">NRR tracks existing customers forward from their signup quarter. New logos excluded. NRR above 100% means existing base is growing.</div>',
                unsafe_allow_html=True)

    nrr_df = load_nrr()
    pivot  = nrr_df.pivot(index="COHORT_QUARTER", columns="FISCAL_QUARTER", values="NRR_PCT")

    z      = [[float(v) if not pd.isna(v) else None for v in row] for _, row in pivot.iterrows()]
    x_labs = list(pivot.columns)
    y_labs = list(pivot.index)

    text_vals = [[f"{float(v):.0f}%" if v is not None else "" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z, x=x_labs, y=y_labs,
        colorscale=[
            [0.0,  "#fde8e8"],
            [0.45, "#f87171"],
            [0.50, "#fef9c3"],
            [0.55, "#fde68a"],
            [0.63, "#bbf7d0"],
            [1.0,  "#15803d"],
        ],
        zmin=60, zmax=160,
        text=text_vals,
        texttemplate="%{text}",
        textfont=dict(size=12, color="#111111"),
        hovertemplate="Cohort: %{y}<br>Quarter: %{x}<br>NRR: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            title=dict(text="NRR %", font=dict(color="#111111")),
            tickvals=[60, 80, 100, 120, 140, 160],
            ticktext=["60%","80%","100%","120%","140%","160%"],
            tickfont=dict(color="#111111")
        )
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f7f8fa",
        font=dict(color="#111111", family="Inter, sans-serif", size=12),
        margin=dict(l=20, r=20, t=50, b=20),
        height=460,
        title=dict(text="NRR % by Cohort (Red under 80%, Yellow 80-100%, Green above 100%)",
                   font=dict(color="#111111", size=15)),
        xaxis=dict(title="Measurement Quarter", tickangle=-30,
                   gridcolor="#e0e0e0", tickfont=dict(color="#111111"),
                   title_font=dict(color="#111111")),
        yaxis=dict(title="Cohort Quarter", autorange="reversed",
                   gridcolor="#e0e0e0", tickfont=dict(color="#111111"),
                   title_font=dict(color="#111111")),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("**NRR Trend - Select a Cohort**")
    cohorts         = sorted(nrr_df["COHORT_QUARTER"].unique().tolist())
    selected_cohort = st.selectbox("Cohort", cohorts, index=len(cohorts)//2)
    trend           = nrr_df[nrr_df["COHORT_QUARTER"] == selected_cohort].sort_values("FISCAL_QUARTER")

    fig4 = go.Figure()
    fig4.add_hline(y=100, line_dash="dash", line_color=AMBER,
                   annotation_text="100% baseline",
                   annotation_font_color=AMBER)
    fig4.add_trace(go.Scatter(
        x=trend["FISCAL_QUARTER"],
        y=trend["NRR_PCT"].astype(float),
        mode="lines+markers",
        line=dict(color=BLUE, width=3),
        marker=dict(size=9,
            color=[GREEN if float(v) >= 100 else AMBER if float(v) >= 80 else RED
                   for v in trend["NRR_PCT"]]),
        text=[f"{float(v):.1f}%" for v in trend["NRR_PCT"]],
        textposition="top center",
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.08)"
    ))
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f7f8fa",
        font=dict(color="#111111", family="Inter, sans-serif", size=12),
        margin=dict(l=20, r=20, t=50, b=20),
        height=300,
        title=dict(text=f"NRR Trend - Cohort {selected_cohort}",
                   font=dict(color="#111111", size=15)),
        xaxis=dict(title="Fiscal Quarter", gridcolor="#e0e0e0",
                   tickfont=dict(color="#111111"), title_font=dict(color="#111111")),
        yaxis=dict(title="NRR %", gridcolor="#e0e0e0",
                   range=[0, max(150, float(trend["NRR_PCT"].max()) * 1.1)],
                   tickfont=dict(color="#111111"), title_font=dict(color="#111111")),
    )
    st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.markdown("**Latest Quarter Summary**")
    latest_q   = nrr_df["FISCAL_QUARTER"].max()
    latest_nrr = nrr_df[nrr_df["FISCAL_QUARTER"] == latest_q][["COHORT_QUARTER","NRR_PCT"]].copy()
    latest_nrr["Signal"] = latest_nrr["NRR_PCT"].apply(
        lambda v: "Strong" if float(v) >= 100 else ("At Risk" if float(v) >= 80 else "Churning"))
    latest_nrr["NRR %"] = latest_nrr["NRR_PCT"].apply(lambda v: f"{float(v):.1f}%")
    st.dataframe(
        latest_nrr[["COHORT_QUARTER","NRR %","Signal"]].rename(
            columns={"COHORT_QUARTER":"Cohort"}),
        use_container_width=True, hide_index=True)
