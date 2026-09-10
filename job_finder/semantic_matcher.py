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
    if nphrase in ntext:
        return True
    words = [w for w in nphrase.split() if w not in {"of", "the", "and", "in", "for", "a"}]
    return bool(words) and all(word in _tokens(ntext) for word in words)


def _title_match(title: str, target: str) -> bool:
    """Match common title variants, including reordered words."""
    t = _norm(title)
    x = _norm(target)
    if not x:
        return False
    if x in t:
        return True
    target_words = set(x.split()) - {"of", "the", "and", "in", "for", "a"}
    title_words = set(t.split())
    return bool(target_words) and len(target_words & title_words) >= max(2, len(target_words) - 1)


def _group_score(hits: list[str]) -> float:
    """Reward multiple independent signals without requiring every keyword."""
    if not hits:
        return 0.0
    if len(hits) == 1:
        return 0.72
    if len(hits) == 2:
        return 0.90
    return 1.0


def semantic_score(job: Job, profile: dict[str, Any]) -> tuple[int, str]:
    """Score a job against the user's leadership + technical profile."""
    title = job.title or ""
    description = job.description or ""
    text = f"{title} {description}"
    weights = profile.get("match_weights", {})
    evidence: list[str] = []
    total = 0.0

    seniority_signals = [
        "senior engineering manager", "engineering manager", "software engineering manager",
        "senior manager", "director of engineering", "engineering director", "director",
        "head of engineering", "head of platform", "head of software", "ai engineering manager",
        "genai engineering manager", "software engineering director", "platform engineering manager",
        "senior director", "engineering leader", "technical director",
    ]
    title_terms = profile.get("titles", [])
    title_hits = [x for x in title_terms if _title_match(title, x)]
    seniority_hits = [x for x in seniority_signals if _hit(title, x)]

    # Leadership title is the strongest signal for this user's target roles.
    title_weight = max(35.0, float(weights.get("title_seniority", 20)))
    if title_hits or seniority_hits:
        total += title_weight
        evidence.append(f"title: {(title_hits or seniority_hits)[0]}")
    else:
        technical_title = {"staff", "principal", "lead", "architect"}
        if any(word in _tokens(title) for word in technical_title):
            total += 8
            evidence.append("title: technical leadership")

    groups = {
        "leadership": profile.get("leadership", []) + [
            "people management", "engineering management", "technical leadership",
            "team leadership", "manage engineers", "lead engineers", "engineering team",
            "technical strategy", "engineering strategy", "roadmap", "cross-functional",
            "manager", "mentoring", "career development", "hiring", "org leadership",
        ],
        "cloud_platform": profile.get("platforms", []) + profile.get("core_domains", []) + [
            "cloud platform", "cloud infrastructure", "platform engineering", "cloud services",
            "hybrid cloud", "private cloud", "edge computing", "cloud-native", "cloud native",
            "infrastructure platform", "developer platform",
        ],
        "distributed_systems": [
            "Distributed Systems", "High Availability", "Microservices", "Scalability",
            "distributed architecture", "large scale systems", "large-scale systems",
            "backend systems", "fault tolerant", "reliability engineering",
        ],
        "ai_agentic": profile.get("ai_agentic", []) + [
            "AI", "Artificial Intelligence", "Generative AI", "GenAI", "LLM", "AI agents",
            "agentic", "machine learning", "AI platform", "AI infrastructure", "AI/ML",
        ],
        "kubernetes_containers": ["Kubernetes", "Docker", "Containers", "Helm", "Cloud Native"],
        "devops_automation": [
            "CI/CD", "Terraform", "Ansible", "Infrastructure as Code", "Automated Testing",
            "DevOps", "automation", "continuous integration", "continuous delivery", "deployment",
        ],
        "infrastructure": profile.get("infrastructure", []) + [
            "compute", "GPU", "networking", "storage", "bare metal", "infrastructure",
            "servers", "hardware", "data center", "datacenter", "edge",
        ],
        "observability_security": [
            "Observability", "Prometheus", "Grafana", "Security", "Compliance", "FedRAMP",
            "monitoring", "logging", "security engineering", "reliability", "SRE",
        ],
    }

    for key, terms in groups.items():
        weight = float(weights.get(key, 0))
        hits: list[str] = []
        seen: set[str] = set()
        for term in terms:
            if term and term.lower() not in seen and _hit(text, term):
                hits.append(term)
                seen.add(term.lower())
        if hits and weight:
            total += weight * _group_score(hits)
            evidence.append(f"{key}: {', '.join(hits[:4])}")

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
