"""
Run from GitHub Actions on a schedule.
Usage: python send_report.py weekly
       python send_report.py monthly

Required environment variables (GitHub Actions secrets):
  GOOGLE_SERVICE_ACCOUNT_JSON  - service account key JSON (raw text)
  SHEET_ID                     - Google Sheet ID

  GMAIL_USER                   - your gmail address
  GMAIL_APP_PASSWORD           - gmail app password
  REPORT_EMAIL_TO              - where to send the report
                                  (comma-separate multiple addresses if needed,
                                  e.g. "you@gmail.com,friend@gmail.com")
"""

import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze import load_data, weekly_summary, monthly_summary


def build_weekly_message(w):
    lines = [
        f"Weekly expense report ({w['this_week_range'][0]} to {w['this_week_range'][1]})",
        f"This week total: Rs.{w['this_week_total']:.0f}",
        f"Last week total: Rs.{w['last_week_total']:.0f}",
        f"Top category: {w['top_category']} (Rs.{w['top_category_amount']:.0f})",
        "",
        "By category (this week):",
    ]
    for cat, amt in w["this_week_by_category"].items():
        lines.append(f"  {cat}: Rs.{amt:.0f}")
    return "\n".join(lines)


def build_monthly_message(m):
    lines = [
        f"Monthly expense report ({m['current_month']})",
        f"This month total: Rs.{m['this_month_total']:.0f}",
        f"Last month ({m['prev_month']}) total: Rs.{m['last_month_total']:.0f}",
        f"Top category: {m['top_category']} (Rs.{m['top_category_amount']:.0f})",
        "",
        "By category (this month):",
    ]
    for cat, amt in m["this_month_by_category"].items():
        lines.append(f"  {cat}: Rs.{amt:.0f}")
    return "\n".join(lines)


def make_chart(by_category, title: str, out_path: str):
    if by_category.empty:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    by_category.plot(kind="bar", ax=ax, color="#0F6E56")
    ax.set_title(title)
    ax.set_ylabel("Amount (Rs.)")
    ax.set_xlabel("")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def send_email(subject: str, body: str, chart_path: str | None):
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to_field = os.environ.get("REPORT_EMAIL_TO", user)
    recipients = [addr.strip() for addr in to_field.split(",") if addr.strip()]

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_field
    msg.attach(MIMEText(body, "plain"))

    if chart_path and os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-Disposition", "attachment", filename="chart.png")
            msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())


def main():
    period = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    sheet_id = os.environ["SHEET_ID"]
    df = load_data(sheet_id)

    if df.empty:
        print("No data yet, skipping report.")
        return

    if period == "monthly":
        m = monthly_summary(df)
        body = build_monthly_message(m)
        subject = "Monthly expense report"
        chart_path = make_chart(m["this_month_by_category"], f"Spend by category - {m['current_month']}", "chart.png")
    else:
        w = weekly_summary(df)
        body = build_weekly_message(w)
        subject = "Weekly expense report"
        chart_path = make_chart(w["this_week_by_category"], f"Spend by category ({w['this_week_range'][0]} to {w['this_week_range'][1]})", "chart.png")

    print(body)
    send_email(subject, body, chart_path)


if __name__ == "__main__":
    main()
