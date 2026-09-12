"""
Streamlit dashboard - deploy free on Streamlit Community Cloud.
Set SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON in Streamlit Cloud secrets.

Grafana-style dark theme.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analyze import load_data, weekly_summary, monthly_summary

st.set_page_config(page_title="Expense Dashboard", layout="wide", page_icon="\U0001F4CA")

# ---------------- Grafana-style palette ----------------
BG = "#0b0d10"
PANEL = "#181b1f"
BORDER = "#2c3235"
TEXT = "#d8d9da"
MUTED = "#8e9297"
PALETTE = ["#73BF69", "#FF780A", "#5794F2", "#B877D9", "#F2495C", "#FADE2A", "#8AB8FF", "#FFB357"]

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; color: {TEXT}; }}
    h1, h2, h3, h4 {{ color: #ffffff !important; font-weight: 600 !important; }}
    p, span, label {{ color: {TEXT}; }}

    div[data-testid="stMetric"] {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 16px;
    }}
    div[data-testid="stMetricLabel"] {{ color: {MUTED} !important; }}
    div[data-testid="stMetricValue"] {{ color: #ffffff !important; }}
    div[data-testid="stMetricDelta"] {{ font-weight: 600; }}

    div[data-testid="stPlotlyChart"] {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 10px;
    }}

    div[data-testid="stExpander"] {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
    }}

    div[data-testid="stDataFrame"] {{ border-radius: 8px; overflow: hidden; }}

    .section-tag {{
        display: inline-block;
        background: {PANEL};
        border: 1px solid {BORDER};
        border-left: 3px solid {PALETTE[0]};
        border-radius: 6px;
        padding: 4px 12px;
        color: {MUTED};
        font-size: 13px;
        margin-bottom: 8px;
    }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig, height=360):
    """Apply the Grafana dark look to a plotly figure so it blends into its panel."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT,
        title_font_color="#ffffff",
        legend_font_color=TEXT,
        margin=dict(l=10, r=10, t=45, b=10),
        height=height,
        colorway=PALETTE,
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


# Pull secrets into env vars so analyze.py's get_client() picks them up
if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]

SHEET_ID = st.secrets.get("SHEET_ID", os.environ.get("SHEET_ID", ""))

st.title("My expense dashboard")

if not SHEET_ID:
    st.error("SHEET_ID not set. Add it in Streamlit Cloud secrets.")
    st.stop()

with st.spinner("Loading data from Google Sheet..."):
    df = load_data(SHEET_ID)

if df.empty:
    st.warning("No data yet. Fill the Google Form to see your dashboard.")
    st.stop()

# ---- Weekly section ----
st.markdown('<div class="section-tag">WEEKLY</div>', unsafe_allow_html=True)
st.header("This week vs last week")
w = weekly_summary(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("This week total", f"\u20b9{w['this_week_total']:.0f}")
col2.metric("Last week total", f"\u20b9{w['last_week_total']:.0f}",
            delta=f"{w['this_week_total'] - w['last_week_total']:.0f}")
col3.metric("Week range", f"{w['this_week_range'][0]} to {w['this_week_range'][1]}")
col4.metric("Top category", w["top_category"] or "\u2014", f"\u20b9{w['top_category_amount']:.0f}")

c1, c2 = st.columns(2)
with c1:
    if not w["this_week_by_category"].empty:
        fig = px.pie(w["this_week_by_category"], values=w["this_week_by_category"].values,
                      names=w["this_week_by_category"].index, title="This week by category",
                      color_discrete_sequence=PALETTE, hole=0.45)
        fig.update_traces(textfont_color="#ffffff")
        st.plotly_chart(style_fig(fig), use_container_width=True)
with c2:
    compare = pd.DataFrame({
        "This week": w["this_week_by_category"],
        "Last week": w["last_week_by_category"],
    }).fillna(0)
    fig2 = px.bar(compare, barmode="group", title="Category comparison",
                  color_discrete_sequence=[PALETTE[0], PALETTE[2]])
    st.plotly_chart(style_fig(fig2), use_container_width=True)

# ---- Monthly section ----
st.markdown('<div class="section-tag">MONTHLY</div>', unsafe_allow_html=True)
st.header("Monthly overview")
m = monthly_summary(df)

col5, col6, col7 = st.columns(3)
col5.metric(f"{m['current_month']} total", f"\u20b9{m['this_month_total']:.0f}")
col6.metric(f"{m['prev_month']} total", f"\u20b9{m['last_month_total']:.0f}")
col7.metric("Top category", m["top_category"] or "\u2014", f"\u20b9{m['top_category_amount']:.0f}")

c3, c4 = st.columns(2)
with c3:
    if not m["daily_trend"].empty:
        fig3 = px.area(m["daily_trend"], title="Daily spend trend (this month)",
                        color_discrete_sequence=[PALETTE[1]])
        fig3.update_traces(line=dict(width=2), fillcolor="rgba(255,120,10,0.15)")
        st.plotly_chart(style_fig(fig3), use_container_width=True)
with c4:
    if not m["this_month_by_category"].empty:
        fig4 = px.bar(m["this_month_by_category"], title="This month by category",
                       color=m["this_month_by_category"].index,
                       color_discrete_sequence=PALETTE)
        fig4.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig4), use_container_width=True)

# ---- Raw data ----
with st.expander("Raw data"):
    st.dataframe(df.sort_values("Timestamp", ascending=False), use_container_width=True)
