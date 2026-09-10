"""Resume-aware job matching without requiring an LLM API key."""
from __future__ import annotations

import re
from typing import Any

from .models import Job


def _norm(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"[^a-z0-9+#./-]+", " ", text.lower())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#./-]+", _norm(text)))


def _hit(text: str, phrase: str) -> bool:
    ntext = _norm(text)
    nphrase = _norm(phrase)
    if not nphrase:
        return False
    return nphrase in ntext or all(word in _tokens(ntext) for word in nphrase.split())


def _title_match(title: str, target: str) -> bool:
    """Match common title variants, including reordered words."""
    t = _norm(title)
    x = _norm(target)
    if not x:
        return False
    if x in t:
        return True
    target_words = set(x.split())
    title_words = set(t.split())
    meaningful = target_words - {"of", "the", "and", "in", "for"}
    return bool(meaningful) and len(meaningful & title_words) >= max(2, len(meaningful) - 1)


def _group_score(hits: list[str]) -> float:
    """Convert evidence count to 0..1 without requiring every keyword."""
    if not hits:
        return 0.0
    if len(hits) == 1:
        return 0.60
    if len(hits) == 2:
        return 0.80
    return 1.0


def semantic_score(job: Job, profile: dict[str, Any]) -> tuple[int, str]:
    """Score a job using weighted resume evidence.

    This intentionally rewards strong evidence instead of requiring exact keyword
    matches. A job can score highly when it matches the user's leadership level,
    technical domain, and AI/platform background even if the employer uses different
    terminology from the resume.
    """
    title = job.title or ""
    description = job.description or ""
    text = f"{title} {description}"
    weights = profile.get("match_weights", {})
    evidence: list[str] = []

    seniority_signals = [
        "senior engineering manager", "engineering manager", "software engineering manager",
        "senior manager", "director of engineering", "engineering director", "director",
        "head of engineering", "head of platform", "head of software", "ai engineering manager",
        "genai engineering manager", "software engineering director", "platform engineering manager",
    ]
    title_terms = profile.get("titles", [])
    title_hits = [x for x in title_terms if _title_match(title, x)]
    seniority_hits = [x for x in seniority_signals if _hit(title, x)]

    total = 0.0
    title_weight = float(weights.get("title_seniority", 20))
    if title_hits or seniority_hits:
        total += title_weight
        evidence.append(f"title: {(title_hits or seniority_hits)[0]}")

    groups = {
        "leadership": profile.get("leadership", []) + [
            "people management", "engineering management", "technical leadership",
            "team leadership", "manage engineers", "lead engineers", "engineering team",
            "technical strategy", "roadmap", "cross-functional",
        ],
        "cloud_platform": profile.get("platforms", []) + profile.get("core_domains", []) + [
            "cloud platform", "cloud infrastructure", "platform engineering", "cloud services",
            "hybrid cloud", "private cloud", "edge computing",
        ],
        "distributed_systems": [
            "Distributed Systems", "High Availability", "Microservices", "Scalability",
            "distributed architecture", "large scale systems", "backend systems",
        ],
        "ai_agentic": profile.get("ai_agentic", []) + [
            "AI", "Artificial Intelligence", "Generative AI", "GenAI", "LLM", "AI agents",
            "agentic", "machine learning", "AI platform", "AI infrastructure",
        ],
        "kubernetes_containers": ["Kubernetes", "Docker", "Containers", "Helm", "Cloud Native"],
        "devops_automation": [
            "CI/CD", "Terraform", "Ansible", "Infrastructure as Code", "Automated Testing",
            "DevOps", "automation", "continuous integration", "continuous delivery",
        ],
        "infrastructure": profile.get("infrastructure", []) + [
            "compute", "GPU", "networking", "storage", "bare metal", "infrastructure",
            "servers", "hardware", "data center", "datacenter",
        ],
        "observability_security": [
            "Observability", "Prometheus", "Grafana", "Security", "Compliance", "FedRAMP",
            "monitoring", "logging", "security engineering", "reliability",
        ],
    }

    for key, terms in groups.items():
        weight = float(weights.get(key, 0))
        hits = []
        seen = set()
        for term in terms:
            if term and term.lower() not in seen and _hit(text, term):
                hits.append(term)
                seen.add(term.lower())
        if hits and weight:
            total += weight * _group_score(hits)
            evidence.append(f"{key}: {', '.join(hits[:4])}")

    # Location is a small positive signal. Remote jobs should match Remote even when
    # the ATS also includes a city or a broad US location.
    locations = profile.get("locations", [])
    location_hits = [x for x in locations if x and _hit(job.location, x)]
    if location_hits or _hit(job.location, "remote"):
        total += 5
        evidence.append(f"location: {', '.join(location_hits[:2]) or 'Remote'}")

    total = min(100, round(total))
    if total >= 85:
        label = "Strong match"
    elif total >= 70:
        label = "Good match"
    elif total >= 55:
        label = "Stretch match"
    else:
        label = "Low match"

    return total, label + (" — " + "; ".join(evidence[:6]) if evidence else "")
