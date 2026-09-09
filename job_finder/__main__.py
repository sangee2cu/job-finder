import os
import yaml
from dotenv import load_dotenv
from .db import connect, save_job
from .discovery import discover
from .matcher import score_job
from .notifier import notify


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(jobs=None):
    load_dotenv()
    profile = load_yaml("config/profile.yaml")
    db = connect(os.getenv("DATABASE_PATH", "data/jobs.db"))

    if jobs is None:
        jobs = discover(load_yaml("config/sources.yaml"))

    matches = []
    for job in jobs:
        job.score, job.explanation = score_job(
            job, profile["titles"], profile["locations"], profile["skills"]
        )
        if job.score >= int(profile.get("minimum_match_score", 80)):
            if save_job(db, job):
                matches.append(job)
                if job.score >= int(profile.get("notification_score", 85)):
                    notify(job)

    print(f"Discovered {len(jobs)} jobs; saved {len(matches)} new matches.")
    for job in sorted(matches, key=lambda item: item.score, reverse=True)[:20]:
        print(f"{job.score}/100 | {job.title} | {job.company} | {job.location}\n{job.url}\n")
    return matches


if __name__ == "__main__":
    run()
