import os
import requests
from .models import Job


def notify(job: Job) -> bool:
    webhook = os.getenv("NOTIFY_WEBHOOK_URL", "").strip()
    if not webhook:
        print(f"MATCH {job.score}/100 | {job.title} | {job.company} | {job.location}\n{job.explanation}\n{job.url}\n")
        return False
    payload = {"text": f"Job match {job.score}/100: {job.title} — {job.company} ({job.location})\n{job.explanation}\n{job.url}"}
    response = requests.post(webhook, json=payload, timeout=15)
    response.raise_for_status()
    return True
