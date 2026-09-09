"""Resume-aware job matching without requiring an LLM API key."""
from __future__ import annotations

import re
from typing import Any

from .models import Job


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+#./-]+", " ", text.lower())


def _hit(text: str, phrase: str) -> bool:
    return _norm(phrase) in _norm(text)


def _title_match(title: str, target: str) -> bool:
    """Allow natural variants such as Director of Engineering / Engineering Director."""
    t = _norm(title)
    x = _norm(target)
    if not x:
        return False
    if x in t:
        return True
    words = [w for w in re.split(r"\s+", x) if w]
    return len(words) >= 2 and sum(w in t for w in words) >= max(2, len(words) - 1)


def semantic_score(job: Job, profile: dict[str, Any]) -> tuple[int, str]:
    """Score a job against the structured resume profile.

    The scorer is deterministic, free to run in GitHub Actions, and intentionally
    tolerant of common title/keyword variations in ATS descriptions.
    """
    text = f"{job.title} {job.description}"
    weights = profile.get("match_weights", {})

    title_terms = profile.get("titles", [])
    title_hits = [x for x in title_terms if x and _title_match(job.title, x)]

    # Broad leadership seniority signals are important because many companies use
    # titles such as Director of Engineering, Engineering Manager, or Head of Platform.
    seniority_signals = [
        "senior engineering manager", "engineering manager", "software engineering manager",
        "senior manager", "director of engineering", "engineering director", "director",
        "head of engineering", "head of platform", "ai engineering manager", "genai engineering manager",
    ]
    seniority_hits = [x for x in seniority_signals if _hit(job.title, x)]

    total = 0
    evidence: list[str] = []

    title_weight = int(weights.get("title_seniority", 20))
    if title_hits or seniority_hits:
        total += title_weight
        evidence.append(f"title: {', '.join((title_hits or seniority_hits)[:2])}")

    groups = {
        "leadership": profile.get("leadership", []),
        "cloud_platform": profile.get("platforms", []) + profile.get("core_domains", []),
        "distributed_systems": ["Distributed Systems", "High Availability", "Microservices"],
        "ai_agentic": profile.get("ai_agentic", []),
        "kubernetes_containers": ["Kubernetes", "Docker", "Containers", "Helm"],
        "devops_automation": ["CI/CD", "Terraform", "Ansible", "Infrastructure as Code", "Automated Testing"],
        "infrastructure": profile.get("infrastructure", []),
        "observability_security": ["Observability", "Prometheus", "Grafana", "Security", "Compliance", "FedRAMP"],
    }

    for key, terms in groups.items():
        weight = int(weights.get(key, 0))
        hits = [term for term in terms if term and _hit(text, term)]
        if hits and weight:
            # One strong hit gets substantial credit; additional evidence increases it.
            fraction = min(1.0, 0.45 + 0.20 * (len(hits) - 1))
            contribution = round(weight * fraction)
            total += contribution
            evidence.append(f"{key}: {', '.join(hits[:4])}")

    # Location is a useful filter, but not a hard requirement because Remote roles
    # can appear with inconsistent ATS location strings.
    locations = profile.get("locations", [])
    location_hits = [x for x in locations if x and _hit(job.location, x)]
    if location_hits:
        total += 5
        evidence.append(f"location: {', '.join(location_hits[:2])}")

    total = min(100, total)
    if total >= 85:
        label = "Strong match"
    elif total >= 70:
        label = "Good match"
    elif total >= 55:
        label = "Stretch match"
    else:
        label = "Low match"

    return total, label + (" — " + "; ".join(evidence[:6]) if evidence else "")
