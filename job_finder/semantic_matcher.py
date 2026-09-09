"""Resume-aware job matching without requiring an LLM API key."""
from __future__ import annotations

import re
from typing import Any

from .models import Job


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9+#./-]+", " ", text.lower())


def _hit(text: str, phrase: str) -> bool:
    return _norm(phrase) in _norm(text)


def semantic_score(job: Job, profile: dict[str, Any]) -> tuple[int, str]:
    """Score a job against the structured resume profile.

    This is intentionally deterministic and free to run in GitHub Actions.
    """
    text = f"{job.title} {job.description}"
    weights = profile.get("match_weights", {})
    parts: list[tuple[str, int, list[str]]] = []

    title_terms = profile.get("titles", []) + [profile.get("seniority", {}).get("current_level", "")]
    title_hits = [x for x in title_terms if x and _hit(job.title, x)]
    parts.append(("title_seniority", int(weights.get("title_seniority", 20)), title_hits))

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

    total = 0
    evidence: list[str] = []
    for key, terms in groups.items():
        weight = int(weights.get(key, 0))
        hits = [term for term in terms if term and _hit(text, term)]
        contribution = round(weight * min(1.0, len(hits) / 3)) if hits else 0
        total += contribution
        if hits:
            evidence.append(f"{key}: {', '.join(hits[:4])}")

    # Strong title alignment should not be lost among technical keywords.
    if title_hits:
        total += int(weights.get("title_seniority", 20))
        evidence.insert(0, f"title: {', '.join(title_hits[:2])}")

    total = min(100, total)
    if total >= 85:
        label = "Strong match"
    elif total >= 70:
        label = "Good match"
    elif total >= 55:
        label = "Stretch match"
    else:
        label = "Low match"

    return total, label + (" — " + "; ".join(evidence[:5]) if evidence else "")
