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

# ---- Grafana-style palette (matches the Streamlit dashboard) ----
BG = "#0b0d10"
PANEL = "#181b1f"
BORDER = "#2c3235"
TEXT = "#d8d9da"
MUTED = "#8e9297"
PALETTE = ["#73BF69", "#FF780A", "#5794F2", "#B877D9", "#F2495C", "#FADE2A", "#8AB8FF", "#FFB357"]


# ---------- plain-text fallback (for clients that can't render HTML) ----------

def build_weekly_text(w):
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


def build_monthly_text(m):
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


# ---------- HTML version (Grafana dark card style) ----------

def _category_rows(series):
    rows = ""
    total = series.sum() if not series.empty else 0
    for i, (cat, amt) in enumerate(series.items()):
        pct = (amt / total * 100) if total else 0
        dot = PALETTE[i % len(PALETTE)]
        rows += f"""
        <tr>
          <td style="padding:8px 10px;border-bottom:1px solid {BORDER};color:{TEXT};font-size:14px;">
            <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{dot};margin-right:8px;"></span>{cat}
          </td>
          <td style="padding:8px 10px;border-bottom:1px solid {BORDER};text-align:right;color:#ffffff;font-weight:600;font-size:14px;">Rs.{amt:,.0f}</td>
          <td style="padding:8px 10px;border-bottom:1px solid {BORDER};text-align:right;color:{MUTED};font-size:13px;">{pct:.0f}%</td>
        </tr>"""
    return rows


def _stat_card(label, value, accent):
    return f"""
        <td style="padding:0 6px;">
          <table bgcolor="{PANEL}" style="background-color:{PANEL};border:1px solid {BORDER};border-radius:10px;border-top:3px solid {accent};" width="100%" cellpadding="0" cellspacing="0">
            <tr><td style="padding:12px 16px;">
              <div style="font-size:12px;color:{MUTED};font-family:Arial,Helvetica,sans-serif;">{label}</div>
              <div style="font-size:21px;font-weight:700;color:#ffffff;font-family:Arial,Helvetica,sans-serif;margin-top:2px;">{value}</div>
            </td></tr>
          </table>
        </td>"""


def _wrap_html(title, subtitle, stat_cards, category_series, chart_cid):
    cards_html = "".join(_stat_card(label, value, PALETTE[i % len(PALETTE)]) for i, (label, value) in enumerate(stat_cards))

    chart_html = (
        f'<tr><td style="padding-top:18px;"><img src="cid:{chart_cid}" alt="Spend by category" width="600" style="max-width:100%;border-radius:10px;border:1px solid {BORDER};display:block;"></td></tr>'
        if chart_cid else ""
    )

    return f"""\
<html>
  <body bgcolor="{BG}" style="background-color:{BG};margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" bgcolor="{BG}" style="background-color:{BG};" cellpadding="0" cellspacing="0">
      <tr><td align="center">
        <table width="620" style="max-width:620px;" cellpadding="0" cellspacing="0">
          <tr><td style="padding:24px 8px 4px 8px;">
            <div style="width:3px;height:3px;"></div>
            <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:{PALETTE[0]};margin-right:8px;"></span>
            <span style="color:{MUTED};font-size:12px;letter-spacing:1px;">EXPENSE DASHBOARD</span>
            <h2 style="color:#ffffff;margin:8px 0 2px 0;font-size:22px;">{title}</h2>
            <p style="color:{MUTED};margin:0 0 16px 0;font-size:13px;">{subtitle}</p>
          </td></tr>

          <tr><td>
            <table width="100%" cellpadding="0" cellspacing="0"><tr>{cards_html}</tr></table>
          </td></tr>

          <tr><td style="padding-top:20px;">
            <table bgcolor="{PANEL}" width="100%" style="background-color:{PANEL};border:1px solid {BORDER};border-radius:10px;" cellpadding="0" cellspacing="0">
              <tr><td style="padding:14px 16px 4px 16px;color:#ffffff;font-size:14px;font-weight:600;">By category</td></tr>
              <tr><td style="padding:0 10px 10px 10px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  {_category_rows(category_series)}
                </table>
              </td></tr>
            </table>
          </td></tr>

          {chart_html}

          <tr><td style="padding:20px 8px 24px 8px;color:{MUTED};font-size:11px;">Sent automatically by your expense dashboard.</td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
"""


def build_weekly_html(w, chart_cid):
    stat_cards = [
        ("This week", f"Rs.{w['this_week_total']:,.0f}"),
        ("Last week", f"Rs.{w['last_week_total']:,.0f}"),
        ("Top category", f"{w['top_category'] or '-'}"),
    ]
    subtitle = f"{w['this_week_range'][0]} to {w['this_week_range'][1]}"
    return _wrap_html("Weekly expense report", subtitle, stat_cards, w["this_week_by_category"], chart_cid)


def build_monthly_html(m, chart_cid):
    stat_cards = [
        (f"{m['current_month']}", f"Rs.{m['this_month_total']:,.0f}"),
        (f"{m['prev_month']}", f"Rs.{m['last_month_total']:,.0f}"),
        ("Top category", f"{m['top_category'] or '-'}"),
    ]
    return _wrap_html("Monthly expense report", m["current_month"], stat_cards, m["this_month_by_category"], chart_cid)


# ---------- chart (matplotlib, dark theme to match) ----------

def make_chart(by_category, title: str, out_path: str):
    if by_category.empty:
        return None

    fig, ax = plt.subplots(figsize=(6.4, 4), facecolor=PANEL)
    ax.set_facecolor(PANEL)

    colors = [PALETTE[i % len(PALETTE)] for i in range(len(by_category))]
    by_category.plot(kind="bar", ax=ax, color=colors, edgecolor="none")

    ax.set_title(title, color="#ffffff", fontsize=12, pad=12)
    ax.set_ylabel("Amount (Rs.)", color=TEXT, fontsize=10)
    ax.set_xlabel("")
    ax.tick_params(colors=TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER)
    ax.grid(axis="y", color=BORDER, linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(out_path, dpi=130, facecolor=PANEL)
    plt.close(fig)
    return out_path


# ---------- email ----------

def send_email(subject: str, text_body: str, html_body: str, chart_path: str | None):
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to_field = os.environ.get("REPORT_EMAIL_TO", user)
    recipients = [addr.strip() for addr in to_field.split(",") if addr.strip()]

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_field

    # "alternative" part: plain text first, HTML second (clients render the last part they support)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text_body, "plain"))
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    if chart_path and os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", "<chart>")
            img.add_header("Content-Disposition", "inline", filename="chart.png")
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
        text_body = build_monthly_text(m)
        chart_path = make_chart(m["this_month_by_category"], f"Spend by category - {m['current_month']}", "chart.png")
        html_body = build_monthly_html(m, "chart" if chart_path else None)
        subject = "Monthly expense report"
    else:
        w = weekly_summary(df)
        text_body = build_weekly_text(w)
        chart_path = make_chart(w["this_week_by_category"], f"Spend by category ({w['this_week_range'][0]} to {w['this_week_range'][1]})", "chart.png")
        html_body = build_weekly_html(w, "chart" if chart_path else None)
        subject = "Weekly expense report"

    print(text_body)
    send_email(subject, text_body, html_body, chart_path)


if __name__ == "__main__":
    main()
