import requests
from .models import Job


def fetch_json(url: str, params: dict | None = None) -> dict:
    response = requests.get(url, params=params, timeout=30, headers={"User-Agent": "job-finder/0.1"})
    response.raise_for_status()
    return response.json()


def greenhouse_jobs(board_token: str, company: str) -> list[Job]:
    """Fetch published jobs from a Greenhouse public job board."""
    data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs", {"content": "true"})
    jobs = []
    for item in data.get("jobs", []):
        location = (item.get("location") or {}).get("name", "")
        jobs.append(Job(
            title=item.get("title", ""),
            company=company,
            location=location,
            url=item.get("absolute_url", ""),
            description=item.get("content", ""),
            source="greenhouse",
            published_at=item.get("updated_at"),
        ))
    return jobs


def lever_jobs(site: str, company: str) -> list[Job]:
    """Fetch published jobs from Lever's public postings API."""
    data = fetch_json(f"https://api.lever.co/v0/postings/{site}", {"mode": "json"})
    jobs = []
    for item in data if isinstance(data, list) else []:
        categories = item.get("categories") or {}
        location = categories.get("location", "")
        all_locations = categories.get("allLocations") or []
        if all_locations:
            location = ", ".join(dict.fromkeys([location, *all_locations]))
        description = (item.get("descriptionPlain") or item.get("description") or "")
        jobs.append(Job(
            title=item.get("text", ""),
            company=company,
            location=location,
            url=(item.get("hostedUrl") or item.get("applyUrl") or ""),
            description=description,
            source="lever",
            published_at=None,
        ))
    return jobs


def discover(config: dict) -> list[Job]:
    jobs = []
    for source in config.get("greenhouse", []):
        jobs.extend(greenhouse_jobs(source["board_token"], source["company"]))
    for source in config.get("lever", []):
        jobs.extend(lever_jobs(source["site"], source["company"]))
    return jobs
