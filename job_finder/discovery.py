from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import Job


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-finder/1.0; +https://github.com/sangee2cu/job-finder)",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_INDEED_SEARCHES = [
    ("Senior Engineering Manager AI", "Raleigh, NC, United States"),
    ("Senior Engineering Manager Cloud Infrastructure", "Raleigh, NC, United States"),
    ("Director Engineering Platform", "Raleigh, NC, United States"),
    ("AI Engineering Manager", "Remote, United States"),
    ("Senior Engineering Manager AI", "Remote, United States"),
    ("Senior Manager Software Engineering Cloud", "Remote, United States"),
    ("Director Platform Engineering", "Remote, United States"),
    ("Engineering Manager AI Infrastructure", "Austin, TX, United States"),
    ("Engineering Manager Cloud Infrastructure", "Nashville, TN, United States"),
]


NON_US_MARKERS = {
    "australia", "austria", "belgium", "brazil", "canada", "china", "france", "germany",
    "india", "ireland", "israel", "italy", "japan", "mexico", "netherlands", "new zealand",
    "poland", "portugal", "singapore", "spain", "sweden", "switzerland", "united kingdom",
    "uk", "england", "scotland", "wales", "london", "toronto", "vancouver", "dublin", "bangalore",
    "bengaluru", "hyderabad", "pune", "gurgaon", "gurugram", "delhi", "mumbai", "chennai",
    "noida", "paris", "berlin", "tokyo", "sydney", "melbourne", "amsterdam", "zurich",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}


def is_us_location(location: str) -> bool:
    """Return True for U.S. locations, including U.S. remote roles."""
    text = re.sub(r"[^a-z0-9]+", " ", (location or "").lower()).strip()
    if not text:
        return False
    if any(marker in text.split() or marker in text for marker in NON_US_MARKERS):
        return False
    if "united states" in text or " usa " in f" {text} " or text.endswith(" usa"):
        return True
    if "remote" in text:
        # A remote posting is accepted only when it explicitly identifies the U.S.
        return "united states" in text or "usa" in text or "us" in text.split()
    return bool(re.search(r"\b[A-Z]{2}\b", location.upper()) and re.search(r"\b(?:" + "|".join(US_STATE_CODES) + r")\b", location.upper()))


def fetch_json(url: str, params: dict | None = None) -> dict:
    response = requests.get(url, params=params, timeout=30, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def greenhouse_jobs(board_token: str, company: str) -> list[Job]:
    """Fetch published jobs from a Greenhouse public job board."""
    data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs", {"content": "true"})
    jobs = []
    for item in data.get("jobs", []):
        location = (item.get("location") or {}).get("name", "")
        if not is_us_location(location):
            continue
        jobs.append(Job(
            title=item.get("title", ""), company=company, location=location,
            url=item.get("absolute_url", ""), description=item.get("content", ""),
            source="greenhouse", published_at=item.get("updated_at"),
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
        if not is_us_location(location):
            continue
        description = item.get("descriptionPlain") or item.get("description") or ""
        jobs.append(Job(
            title=item.get("text", ""), company=company, location=location,
            url=item.get("hostedUrl") or item.get("applyUrl") or "",
            description=description, source="lever", published_at=None,
        ))
    return jobs


def indeed_jobs(query: str, location: str = "", limit: int = 25) -> list[Job]:
    """Discover U.S. jobs from Indeed's public search results, best-effort."""
    url = "https://www.indeed.com/jobs"
    params = {"q": query}
    if location:
        params["l"] = location
    try:
        response = requests.get(url, params=params, timeout=30, headers=HEADERS)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Indeed search failed for '{query}' / '{location}': {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs: list[Job] = []
    seen: set[str] = set()

    for card in soup.select("div.job_seen_beacon, div.cardOutline, div[data-jk]"):
        link = card.select_one("a.jcs-JobTitle, h2.jobTitle a, a[data-jk]")
        if not link:
            continue
        job_key = link.get("data-jk") or card.get("data-jk")
        href = link.get("href", "")
        if not job_key:
            match = re.search(r"[?&]jk=([A-Za-z0-9]+)", href)
            job_key = match.group(1) if match else href
        if not job_key or job_key in seen:
            continue
        seen.add(job_key)

        title = link.get_text(" ", strip=True)
        company_node = card.select_one("span.companyName, [data-testid='company-name']")
        location_node = card.select_one("div.companyLocation, [data-testid='text-location']")
        snippet_node = card.select_one("div.job-snippet, div.job-snippet-container, td.resultContent")
        company = company_node.get_text(" ", strip=True) if company_node else "Indeed"
        job_location = location_node.get_text(" ", strip=True) if location_node else location
        description = snippet_node.get_text(" ", strip=True) if snippet_node else card.get_text(" ", strip=True)

        if not is_us_location(job_location):
            continue

        job_url = href if href.startswith("http") else urljoin("https://www.indeed.com", href or f"/viewjob?jk={job_key}")
        jobs.append(Job(title=title, company=company, location=job_location, url=job_url,
                        description=description, source="indeed"))
        if len(jobs) >= limit:
            break

    return jobs


def discover(config: dict) -> list[Job]:
    jobs = []
    for source in config.get("greenhouse", []):
        jobs.extend(greenhouse_jobs(source["board_token"], source["company"]))
    for source in config.get("lever", []):
        jobs.extend(lever_jobs(source["site"], source["company"]))

    indeed_sources = config.get("indeed") or [
        {"query": query, "location": location, "limit": 25}
        for query, location in DEFAULT_INDEED_SEARCHES
    ]
    for source in indeed_sources:
        jobs.extend(indeed_jobs(source["query"], source.get("location", ""), int(source.get("limit", 25))))
    return jobs
