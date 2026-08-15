# Expense dashboard — setup guide

Flow: Google Form → Google Sheet → Python analysis → Streamlit dashboard (live link)
→ Daily email reminder (6 PM) → Weekly/Monthly report by email (with chart image).
Everything free.

---

## Step 1 — Create the Google Form

Fields (in this exact order):
1. **Category** (dropdown) — use these 21:
   House Rent, Milk, Electricity Bill, Gas Bill, Water Bill, Grocery, Snacks,
   Medicine, Petrol, Chit Fund, Shopping, Mobile/Internet Recharge, Transport,
   EMI/Loan, Eating Out, Subscriptions, Salon/Personal Care, Job Hunting,
   Gifts/Donations, Maintenance/Repairs, Others
2. **Amount** (short answer, number)
3. **Payment Mode** (dropdown) — Cash, UPI, Card
4. **Notes** (short answer, optional)

Google Forms auto-adds a **Timestamp** column when linked to a Sheet.

Link the form to a Sheet: Form → Responses tab → click the green Sheets icon.
Note the **Sheet ID** from the Sheet's URL:
`https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`

Also copy the **form's shareable link** (Send button → link icon) — used in
the daily reminder email.

---

## Step 2 — Google service account (so Python can read the Sheet)

1. [Google Cloud Console](https://console.cloud.google.com/) → new project (free).
2. Enable **Google Sheets API** and **Google Drive API**.
3. IAM & Admin → Service Accounts → Create service account → Create key → JSON.
   A `.json` file downloads — never commit this to GitHub.
4. Open the JSON, copy the `client_email`.
5. Open your Google Sheet → Share → paste that email → **Viewer** access.

---

## Step 3 — Gmail app password (for sending reports and reminders)

1. Turn on 2-Step Verification on your Google account.
2. Google Account → Security → App passwords → generate one for "Mail".
3. Copy the 16-character password — this is `GMAIL_APP_PASSWORD`.

---

## Step 4 — Push this project to GitHub

```bash
cd expense_dashboard
git init
git add .
git commit -m "expense dashboard"
git remote add origin https://github.com/YOUR_USERNAME/expense-dashboard.git
git push -u origin main
```

`service_account.json` should never be committed — it's git-ignored already.
Production reads credentials from secrets, not from a file.

---

## Step 5 — Add GitHub Actions secrets

Repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret name | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | entire content of the service account JSON file |
| `SHEET_ID` | your Google Sheet ID |
| `GMAIL_USER` | your gmail address |
| `GMAIL_APP_PASSWORD` | 16-char app password from Step 3 |
| `REPORT_EMAIL_TO` | email(s) to receive reports — one address, or comma-separated for more than one, e.g. `you@gmail.com,friend@gmail.com` |
| `FORM_LINK` | the Google Form shareable link (used in the daily reminder) |

Three workflows now run automatically:
- **`daily_reminder.yml`** — every day 6:00 PM IST → short reminder email
- **`weekly_report.yml`** — every Monday 8:30 AM IST → summary + chart image
- **`monthly_report.yml`** — 1st of month 8:30 AM IST → summary + chart image

You can also trigger any of them manually: Actions tab → pick workflow → Run workflow.

---

## Step 6 — Deploy the dashboard (Streamlit Community Cloud, free, live link)

1. [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub.
2. New app → this repo → main file: `app.py` → Deploy.
3. App settings → Secrets:
```toml
SHEET_ID = "your_sheet_id"
GOOGLE_SERVICE_ACCOUNT_JSON = '''paste entire JSON content here'''
```
4. You get a permanent public URL — open it anytime to see the live dashboard
   (it reads the Sheet fresh on every load, so today's entries show up right away).

---

## Testing locally (optional)

```bash
pip install -r requirements.txt
# place the downloaded service_account.json in this folder
export SHEET_ID="your_sheet_id"
streamlit run app.py
```

To test scripts locally, export all env vars from Step 5 in your terminal:
```bash
python daily_reminder.py
python send_report.py weekly
python send_report.py monthly
```
