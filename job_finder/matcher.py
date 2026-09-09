import re
from typing import Iterable
from .models import Job


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def score_job(job: Job, titles: Iterable[str], locations: Iterable[str], skills: Iterable[str]) -> tuple[int, str]:
    title_text = job.title.lower()
    location_text = job.location.lower()
    body = f"{job.title} {job.description}".lower()

    title_hits = [t for t in titles if t.lower() in title_text]
    location_hits = [l for l in locations if l.lower() in location_text]
    skill_hits = [s for s in skills if _tokens(s) <= _tokens(body)]

    title_score = min(40, 40 if title_hits else 0)
    location_score = min(20, 20 if location_hits else 0)
    skill_score = min(40, round(40 * len(skill_hits) / max(1, len(list(skills)))))
    score = min(100, title_score + location_score + skill_score)

    reasons = []
    if title_hits: reasons.append(f"title: {', '.join(title_hits[:2])}")
    if location_hits: reasons.append(f"location: {', '.join(location_hits[:2])}")
    if skill_hits: reasons.append(f"skills: {', '.join(skill_hits[:5])}")
    return score, ("Strong match — " + "; ".join(reasons)) if reasons else "Limited profile overlap"
