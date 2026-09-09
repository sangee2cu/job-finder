"""Email the generated Markdown job report via SMTP."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_report(path: str = "reports/latest.md") -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    recipient = os.getenv("EMAIL_TO", "").strip()
    sender = os.getenv("EMAIL_FROM", username).strip()

    if not all((host, username, password, recipient)):
        print("Email not configured; skipping email delivery.")
        return False

    body = Path(path).read_text(encoding="utf-8")
    msg = EmailMessage()
    msg["Subject"] = "Job Finder — Daily Matches"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)

    print(f"Job report emailed to {recipient}")
    return True


if __name__ == "__main__":
    send_report()
