# Expense dashboard — requirements document

## 1. Overview
A personal daily expense tracker that auto-analyzes spending from a Google Form
and shares weekly/monthly summaries automatically, with zero hosting cost.

---

## 2. Data collection — Google Form

| Field | Type | Notes |
|---|---|---|
| Timestamp | Auto | Added automatically by Google Forms |
| Category | Dropdown | 21 fixed categories (see below) |
| Amount | Number | Required |
| Payment Mode | Dropdown | Cash, UPI, Card |
| Notes | Short text | Optional |

**Categories (21):**
House Rent, Milk, Electricity Bill, Gas Bill, Water Bill, Grocery, Snacks,
Medicine, Petrol, Chit Fund, Shopping, Mobile/Internet Recharge, Transport,
EMI/Loan, Eating Out, Subscriptions, Salon/Personal Care, Job Hunting,
Gifts/Donations, Maintenance/Repairs, Others

Form responses feed directly into a linked Google Sheet (single source of truth).

---

## 3. Daily reminder

- **Channel:** Email
- **Time:** 6:00 PM IST, every day
- **Content:** short nudge to fill today's expense entry, with the form link
- **Delivery:** free, via Gmail SMTP, triggered by a GitHub Actions cron job
- **Note:** WhatsApp (via CallMeBot) and Telegram were both considered, but
  the requirement was simplified to email-only for reliability and simplicity.

---

## 4. Analysis requirements

The system computes, from the raw Sheet data:

- **Week-wise:** this week's total vs last week's total
- **Month-wise:** this month's total vs last month's total
- **Category-wise:** spend broken down by category, for both week and month views
- **Top contributing category:** the single highest-spend category, shown for
  both the current week and current month
- **Daily trend:** day-by-day spend line for the current month

No budget/limit alerts in this version (explicitly out of scope for now).

---

## 5. Dashboard

- **Platform:** Streamlit (Python), deployed on Streamlit Community Cloud
- **Access:** a single permanent public link — opens anytime, always reflects
  live Sheet data (no manual refresh/export step)
- **Views:**
  - This week vs last week — totals, category pie chart, category comparison bar chart
  - Monthly overview — totals, daily trend line, category-wise bar chart
  - Top category highlighted as a metric, for both week and month
  - Raw data table (expandable, for reference)

---

## 6. Weekly & monthly reports

| Aspect | Detail |
|---|---|
| Frequency | Weekly (every Monday), Monthly (1st of month) |
| Channel | Email only |
| Recipient(s) | One or more email addresses (comma-separated) |
| Content | Text summary (total, comparison, top category, category-wise breakdown) **plus a chart image attachment** |
| Delivery mechanism | GitHub Actions scheduled workflow (cron), free |

---

## 7. Explicitly out of scope (for this version)

- Budget/spending limit alerts
- Multi-user / family shared tracking (single user: Abu only)
- Paid hosting or paid APIs — everything must run on free tiers

---

## 8. Technical stack (all free tier)

| Component | Tool |
|---|---|
| Data entry | Google Forms |
| Data storage | Google Sheets |
| Data access | Python (gspread + Google service account) |
| Analysis | Python (pandas) |
| Dashboard | Streamlit, hosted on Streamlit Community Cloud |
| Scheduling | GitHub Actions (cron workflows) |
| Email delivery | Gmail SMTP (app password) |

---

## 9. Deliverables (already built)

- `analyze.py` — data loading + week/month/category/top-category analysis
- `app.py` — Streamlit dashboard
- `send_report.py` — weekly/monthly report generator (email + 2x WhatsApp)
- `daily_reminder.py` — daily WhatsApp reminder script
- `.github/workflows/daily_reminder.yml` — 6 PM daily cron
- `.github/workflows/weekly_report.yml` — Monday cron
- `.github/workflows/monthly_report.yml` — 1st-of-month cron
- `requirements.txt` — Python dependencies
- `README.md` — full setup walkthrough
- `.gitignore` — prevents committing credentials
