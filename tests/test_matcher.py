from job_finder.models import Job
from job_finder.matcher import score_job


def test_strong_match():
    job = Job(
        title="Senior Engineering Manager, Cloud Infrastructure",
        company="Example",
        location="Raleigh, NC",
        url="https://example.com/job/1",
        description="Lead Kubernetes platform engineering, distributed systems, OCI and DevOps teams."
    )
    score, explanation = score_job(
        job,
        ["Senior Engineering Manager"],
        ["Raleigh"],
        ["Cloud Infrastructure", "Kubernetes", "Distributed Systems", "OCI"]
    )
    assert score >= 80
    assert "title:" in explanation
