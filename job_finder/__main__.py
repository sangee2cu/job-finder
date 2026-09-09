import os
import yaml
from dotenv import load_dotenv
from .db import connect, save_job
from .matcher import score_job
from .notifier import notify


def load_profile(path="config/profile.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(jobs=None):
    load_dotenv()
    profile = load_profile()
    db = connect(os.getenv("DATABASE_PATH", "data/jobs.db"))
    for job in jobs or []:
        job.score, job.explanation = score_job(job, profile["titles"], profile["locations"], profile["skills"])
        if job.score >= int(profile.get("minimum_match_score", 80)) and save_job(db, job):
            if job.score >= int(profile.get("notification_score", 85)):
                notify(job)


if __name__ == "__main__":
    print("Job Finder initialized. Connect an allowed job feed in job_finder/sources.py.")
