import sqlite3
from pathlib import Path
from .models import Job


def connect(path: str = "data/jobs.db"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        job_key TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
        url TEXT, description TEXT, source TEXT, published_at TEXT,
        score INTEGER, explanation TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    return db


def save_job(db, job: Job) -> bool:
    cur = db.execute("""INSERT OR IGNORE INTO jobs
        (job_key,title,company,location,url,description,source,published_at,score,explanation)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", (job.key, job.title, job.company, job.location,
        job.url, job.description, job.source, job.published_at, job.score, job.explanation))
    db.commit()
    return cur.rowcount == 1
