"""
Sends a daily email reminder to fill the expense form.
Runs via GitHub Actions at 6 PM IST every day.
"""

import os
import smtplib
from email.mime.text import MIMEText

FORM_LINK = os.environ.get("FORM_LINK", "")


def send_email(subject: str, body: str):
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("REPORT_EMAIL_TO", user)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())


def main():
    body = "Reminder: fill today's expense entry."
    if FORM_LINK:
        body += f"\n{FORM_LINK}"
    send_email("Daily expense reminder", body)
    print("Reminder email sent.")


if __name__ == "__main__":
    main()
