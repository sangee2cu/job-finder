import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from .db import connect, save_job
from .discovery import discover
from .emailer import send_report
from .notifier import notify
from .semantic_matcher import semantic_score


def load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def recommendation(score: int) -> str:
    if score >= 85:
        return "APPLY"
    if score >= 80:
        return "REVIEW"
    if score >= 70:
        return "STRETCH"
    return "SKIP"


def write_report(jobs, path="reports/latest.md"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    selected = [j for j in jobs if j.score >= 70]
    selected.sort(key=lambda j: j.score, reverse=True)
    lines = [
        "# Job Finder Report", "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Discovered: {len(jobs)} | Ranked >= 70: {len(selected)}", "",
        "| Score | Action | Role | Company | Location | Source | Apply |",
        "|---:|---|---|---|---|---|---|",
    ]
    for j in selected[:50]:
        lines.append(
            f"| {j.score} | **{recommendation(j.score)}** | {j.title} | {j.company} | "
            f"{j.location} | {j.source} | [Apply]({j.url}) |"
        )
        lines.extend(["", f"> {j.explanation}", ""])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run(jobs=None):
    load_dotenv()
    profile = load_yaml("config/resume_profile.yaml")
    settings = load_yaml("config/profile.yaml")
    db = connect(os.getenv("DATABASE_PATH", "data/jobs.db"))

    if jobs is None:
        jobs = discover(load_yaml("config/sources.yaml"))

    ranked = []
    minimum = int(settings.get("minimum_match_score", 80))
    notify_score = int(settings.get("notification_score", 85))

    for job in jobs:
        job.score, job.explanation = semantic_score(job, {**profile, **settings})
        ranked.append(job)
        if job.score >= minimum and save_job(db, job) and job.score >= notify_score:
            notify(job)

    write_report(ranked)
    send_report("reports/latest.md")
    ranked.sort(key=lambda j: j.score, reverse=True)
    print(f"Discovered {len(jobs)} jobs; {len([j for j in ranked if j.score >= minimum])} meet the match threshold.")
    for job in ranked[:20]:
        print(f"{job.score}/100 | {recommendation(job.score)} | {job.title} | {job.company} | {job.location} | {job.url}")
    return ranked


if __name__ == "__main__":
    run()
