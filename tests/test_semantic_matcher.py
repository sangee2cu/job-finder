from job_finder.models import Job
from job_finder.semantic_matcher import semantic_score


def test_resume_aware_match():
    profile = {
        "titles": ["Senior Engineering Manager", "Director Engineering"],
        "seniority": {"current_level": "Software Development Senior Manager"},
        "leadership": ["Engineering leadership", "Cross-functional leadership"],
        "platforms": ["Oracle Cloud Infrastructure (OCI)", "Cloud@Customer"],
        "core_domains": ["Cloud Infrastructure", "Platform Engineering"],
        "ai_agentic": ["Model Context Protocol (MCP)", "Multi-agent AI workflows"],
        "infrastructure": ["GPU Platforms", "Networking"],
        "match_weights": {
            "leadership": 25,
            "title_seniority": 20,
            "cloud_platform": 15,
            "distributed_systems": 10,
            "ai_agentic": 10,
            "kubernetes_containers": 5,
            "devops_automation": 5,
            "infrastructure": 5,
            "observability_security": 5,
        },
    }
    job = Job(
        title="Senior Engineering Manager, Cloud Platform",
        company="Example",
        location="Raleigh, NC",
        url="https://example.com/job/1",
        description=(
            "Lead cloud infrastructure and platform engineering teams. "
            "Build distributed systems, Kubernetes, GPU infrastructure and "
            "AI agent workflows using MCP."
        ),
    )
    score, explanation = semantic_score(job, profile)
    assert score >= 70
    assert "Strong match" in explanation or "Good match" in explanation
