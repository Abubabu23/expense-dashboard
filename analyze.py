"""
Core logic: pull expense data from Google Sheet and compute
weekly / monthly summaries. Used by both app.py (Streamlit) and
send_report.py (GitHub Actions cron).
"""

import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_client():
    """
    Auth using a Google service account.
    Credentials JSON comes from an env var (GitHub Actions secret / Streamlit secret)
    or a local file for testing.
    """
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        # local fallback: place service_account.json next to this file (do NOT commit it)
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return gspread.authorize(creds)


def load_data(sheet_id: str, worksheet_name: str = "Form Responses 1") -> pd.DataFrame:
    """
    Expected sheet columns (from the Google Form):
    Timestamp | Category | Amount | Payment Mode | Notes
    """
    client = get_client()
    sh = client.open_by_key(sheet_id)
    ws = sh.worksheet(worksheet_name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        return df

    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Timestamp"])
    df["Date"] = df["Timestamp"].dt.date
    df["Week"] = df["Timestamp"].dt.isocalendar().week
    df["Year"] = df["Timestamp"].dt.isocalendar().year
    df["Month"] = df["Timestamp"].dt.to_period("M").astype(str)
    return df


def week_bounds(df: pd.DataFrame, weeks_ago: int = 0):
    """Return (start_date, end_date, subset_df) for the Nth week back from today."""
    today = pd.Timestamp.today().normalize()
    start = today - pd.Timedelta(days=today.weekday() + 7 * weeks_ago)
    end = start + pd.Timedelta(days=6)
    mask = (df["Timestamp"] >= start) & (df["Timestamp"] <= end + pd.Timedelta(days=1))
    return start.date(), end.date(), df[mask]


def weekly_summary(df: pd.DataFrame) -> dict:
    this_start, this_end, this_week = week_bounds(df, 0)
    last_start, last_end, last_week = week_bounds(df, 1)

    this_week_by_category = this_week.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    top_category = this_week_by_category.index[0] if not this_week_by_category.empty else None
    top_category_amount = this_week_by_category.iloc[0] if not this_week_by_category.empty else 0

    return {
        "this_week_range": (this_start, this_end),
        "last_week_range": (last_start, last_end),
        "this_week_total": round(this_week["Amount"].sum(), 2),
        "last_week_total": round(last_week["Amount"].sum(), 2),
        "this_week_by_category": this_week_by_category,
        "last_week_by_category": last_week.groupby("Category")["Amount"].sum().sort_values(ascending=False),
        "top_category": top_category,
        "top_category_amount": round(top_category_amount, 2),
    }


def monthly_summary(df: pd.DataFrame) -> dict:
    current_month = pd.Timestamp.today().to_period("M").strftime("%Y-%m")
    prev_month = (pd.Timestamp.today().to_period("M") - 1).strftime("%Y-%m")

    this_month_df = df[df["Month"] == current_month]
    last_month_df = df[df["Month"] == prev_month]

    this_month_by_category = this_month_df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    top_category = this_month_by_category.index[0] if not this_month_by_category.empty else None
    top_category_amount = this_month_by_category.iloc[0] if not this_month_by_category.empty else 0

    return {
        "current_month": current_month,
        "prev_month": prev_month,
        "this_month_total": round(this_month_df["Amount"].sum(), 2),
        "last_month_total": round(last_month_df["Amount"].sum(), 2),
        "this_month_by_category": this_month_by_category,
        "daily_trend": this_month_df.groupby("Date")["Amount"].sum(),
        "top_category": top_category,
        "top_category_amount": round(top_category_amount, 2),
    }
