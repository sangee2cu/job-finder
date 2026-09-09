from typing import Iterable
from .models import Job


def from_json(items: Iterable[dict], source: str = "feed") -> list[Job]:
    """Normalize dictionaries from an allowed API/RSS/public feed."""
    jobs = []
    for item in items:
        jobs.append(Job(
            title=item.get("title", "").strip(),
            company=item.get("company", "").strip(),
            location=item.get("location", "").strip(),
            url=item.get("url", "").strip(),
            description=item.get("description", "") or "",
            source=source,
            published_at=item.get("published_at"),
        ))
    return jobs
