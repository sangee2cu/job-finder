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

# These are the ONLY geographic targets for the job finder.
TARGET_CITY_STATES = {
    "raleigh, nc", "durham, nc", "cary, nc",
    "austin, tx", "nashville, tn",
}

# Indeed is a useful broad source, but GitHub Actions may receive anti-bot
# responses. Keep multiple queries so the agent still finds roles when some
# searches return no cards.
DEFAULT_INDEED_SEARCHES = [
    ("Senior Engineering Manager", "Raleigh, NC, United States"),
    ("Senior Software Engineering Manager", "Raleigh, NC, United States"),
    ("Engineering Manager", "Raleigh, NC, United States"),
    ("Director Software Engineering", "Raleigh, NC, United States"),
    ("Platform Engineering Manager", "Raleigh, NC, United States"),
    ("AI Engineering Manager", "Raleigh, NC, United States"),
    ("Cloud Engineering Manager", "Raleigh, NC, United States"),
    ("Senior Engineering Manager", "Durham, NC, United States"),
    ("Senior Software Engineering Manager", "Durham, NC, United States"),
    ("Engineering Manager", "Durham, NC, United States"),
    ("Director Software Engineering", "Durham, NC, United States"),
    ("Platform Engineering Manager", "Durham, NC, United States"),
    ("AI Engineering Manager", "Durham, NC, United States"),
    ("Cloud Engineering Manager", "Durham, NC, United States"),
    ("Senior Engineering Manager", "Cary, NC, United States"),
    ("Engineering Manager", "Cary, NC, United States"),
    ("Director Software Engineering", "Cary, NC, United States"),
    ("Senior Engineering Manager", "Austin, TX, United States"),
    ("Engineering Manager AI Infrastructure", "Austin, TX, United States"),
    ("Director Platform Engineering", "Austin, TX, United States"),
    ("Senior Engineering Manager", "Nashville, TN, United States"),
    ("Engineering Manager Cloud Infrastructure", "Nashville, TN, United States"),
    ("Director Platform Engineering", "Nashville, TN, United States"),
    ("Senior Engineering Manager", "Remote, United States"),
    ("Senior Software Engineering Manager", "Remote, United States"),
    ("Engineering Manager AI", "Remote, United States"),
    ("Director Platform Engineering", "Remote, United States"),
]

# Direct public Lever boards are more reliable than Indeed in CI. These are
# defaults so an empty sources.yaml still discovers relevant NC roles.
DEFAULT_LEVER_SOURCES = [
    {"company": "Versana", "site": "Versana"},
    {"company": "Protolabs", "site": "protolabs"},
]

NON_US_MARKERS = {
    "australia", "austria", "belgium", "brazil", "canada", "china", "france", "germany",
    "india", "ireland", "israel", "italy", "japan", "mexico", "netherlands", "new zealand",
    "poland", "portugal", "singapore", "spain", "sweden", "switzerland", "united kingdom",
    "uk", "england", "scotland", "wales", "london", "toronto", "vancouver", "dublin", "bangalore",
    "bengaluru", "hyderabad", "pune", "gurgaon", "gurugram", "delhi", "mumbai", "chennai",
    "noida", "paris", "berlin", "tokyo", "sydney", "melbourne", "amsterdam", "zurich",
}


def _normalized_location(location: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (location or "").lower()).strip()


def is_target_location(location: str, allow_remote: bool = True) -> bool:
    """Return True only for the five target cities or U.S. remote roles."""
    text = _normalized_location(location)
    if not text:
        return False

    if any(marker in text.split() or marker in text for marker in NON_US_MARKERS):
        return False

    if "remote" in text:
        return allow_remote and (
            "united states" in text or " usa " in f" {text} " or text.endswith(" usa") or " us " in f" {text} "
        )

    for target in TARGET_CITY_STATES:
        city, state = target.split(", ")
        if re.search(rf"\b{re.escape(city)}\b", text) and re.search(rf"\b{re.escape(state)}\b", text):
            return True

    state_names = {"nc": "north carolina", "tx": "texas", "tn": "tennessee"}
    for target in TARGET_CITY_STATES:
        city, state = target.split(", ")
        if re.search(rf"\b{re.escape(city)}\b", text) and re.search(rf"\b{re.escape(state_names[state])}\b", text):
            return True

    return False


def fetch_json(url: str, params: dict | None = None):
    response = requests.get(url, params=params, timeout=30, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def greenhouse_jobs(board_token: str, company: str) -> list[Job]:
    data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs", {"content": "true"})
    jobs = []
    for item in data.get("jobs", []):
        location = (item.get("location") or {}).get("name", "")
        if not is_target_location(location):
            continue
        jobs.append(Job(
            title=item.get("title", ""), company=company, location=location,
            url=item.get("absolute_url", ""), description=item.get("content", ""),
            source="greenhouse", published_at=item.get("updated_at"),
        ))
    return jobs


def lever_jobs(site: str, company: str) -> list[Job]:
    data = fetch_json(f"https://api.lever.co/v0/postings/{site}", {"mode": "json"})
    jobs = []
    for item in data if isinstance(data, list) else []:
        categories = item.get("categories") or {}
        location = categories.get("location", "")
        all_locations = categories.get("allLocations") or []
        if all_locations:
            location = ", ".join(dict.fromkeys([location, *all_locations]))
        if not is_target_location(location):
            continue
        description = item.get("descriptionPlain") or item.get("description") or ""
        jobs.append(Job(
            title=item.get("text", ""), company=company, location=location,
            url=item.get("hostedUrl") or item.get("applyUrl") or "",
            description=description, source="lever", published_at=None,
        ))
    return jobs


def indeed_jobs(query: str, location: str = "", limit: int = 25) -> list[Job]:
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
    search_is_us_remote = _normalized_location(location) in {"remote united states", "remote usa", "remote us"}

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

        if not is_target_location(job_location, allow_remote=search_is_us_remote):
            continue

        job_url = href if href.startswith("http") else urljoin("https://www.indeed.com", href or f"/viewjob?jk={job_key}")
        jobs.append(Job(title=title, company=company, location=job_location,
                        url=job_url, description=description, source="indeed"))
        if len(jobs) >= limit:
            break

    return jobs


def discover(config: dict) -> list[Job]:
    jobs = []
    for source in config.get("greenhouse", []):
        jobs.extend(greenhouse_jobs(source["board_token"], source["company"]))

    lever_sources = config.get("lever") or DEFAULT_LEVER_SOURCES
    for source in lever_sources:
        try:
            jobs.extend(lever_jobs(source["site"], source["company"]))
        except requests.RequestException as exc:
            print(f"Lever source failed for {source.get('company')}: {exc}")

    indeed_sources = config.get("indeed") or [
        {"query": query, "location": location, "limit": 25}
        for query, location in DEFAULT_INDEED_SEARCHES
    ]
    for source in indeed_sources:
        jobs.extend(indeed_jobs(source["query"], source.get("location", ""), int(source.get("limit", 25))))
    return jobs
