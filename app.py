"""
Streamlit dashboard - deploy free on Streamlit Community Cloud.
Set SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON in Streamlit Cloud secrets.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from analyze import load_data, weekly_summary, monthly_summary

st.set_page_config(page_title="Expense Dashboard", layout="wide")

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
st.header("This week vs last week")
w = weekly_summary(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("This week total", f"₹{w['this_week_total']:.0f}")
col2.metric("Last week total", f"₹{w['last_week_total']:.0f}",
            delta=f"{w['this_week_total'] - w['last_week_total']:.0f}")
col3.metric("Week range", f"{w['this_week_range'][0]} to {w['this_week_range'][1]}")
col4.metric("Top category", w["top_category"] or "—", f"₹{w['top_category_amount']:.0f}")

c1, c2 = st.columns(2)
with c1:
    if not w["this_week_by_category"].empty:
        fig = px.pie(w["this_week_by_category"], values=w["this_week_by_category"].values,
                      names=w["this_week_by_category"].index, title="This week by category")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    compare = pd.DataFrame({
        "This week": w["this_week_by_category"],
        "Last week": w["last_week_by_category"],
    }).fillna(0)
    fig2 = px.bar(compare, barmode="group", title="Category comparison")
    st.plotly_chart(fig2, use_container_width=True)

# ---- Monthly section ----
st.header("Monthly overview")
m = monthly_summary(df)

col5, col6, col7 = st.columns(3)
col5.metric(f"{m['current_month']} total", f"₹{m['this_month_total']:.0f}")
col6.metric(f"{m['prev_month']} total", f"₹{m['last_month_total']:.0f}")
col7.metric("Top category", m["top_category"] or "—", f"₹{m['top_category_amount']:.0f}")

if not m["daily_trend"].empty:
    fig3 = px.line(m["daily_trend"], title="Daily spend trend (this month)")
    st.plotly_chart(fig3, use_container_width=True)

if not m["this_month_by_category"].empty:
    fig4 = px.bar(m["this_month_by_category"], title="This month by category")
    st.plotly_chart(fig4, use_container_width=True)

# ---- Raw data ----
with st.expander("Raw data"):
    st.dataframe(df.sort_values("Timestamp", ascending=False))
