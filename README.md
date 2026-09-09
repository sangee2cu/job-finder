# Job Finder Agent

A lightweight Python agent that discovers public job postings, scores them against a configurable career profile, deduplicates matches in SQLite, and sends notifications for high-confidence matches.

## What it does

1. Pulls published jobs from public Greenhouse and Lever ATS endpoints.
2. Normalizes postings into one `Job` model.
3. Scores each job from 0–100 using title, location and skills.
4. Stores new matches in SQLite so the same posting is not repeatedly reported.
5. Prints high-quality matches and optionally sends webhook notifications.
6. Runs automatically through GitHub Actions on weekdays.

## Current profile

Target roles include Senior Engineering Manager, Senior Manager Engineering, Director Engineering, Director Cloud Infrastructure, Director Platform Engineering, AI Engineering Manager and GenAI Engineering Manager.

Target locations include Raleigh, Durham, Cary, Remote, Austin and Nashville.

Core skills include cloud infrastructure, OCI, Kubernetes, distributed systems, platform engineering, AI/GenAI, DevOps, CI/CD, observability and engineering leadership.

## Job sources

`config/sources.yaml` contains public ATS sources. The repository currently includes Greenhouse boards for Cloudflare, Datadog and Coinbase. Add additional companies by adding their public Greenhouse board token or Lever site slug.

No job-board login or application credentials are used for discovery.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m job_finder
```

## Notifications

Set `NOTIFY_WEBHOOK_URL` in `.env` to enable webhook notifications. Without it, matches are printed to the console.

## Important design choice

The agent does **not** automatically submit applications. It finds, ranks and explains strong matches so applications can remain human-reviewed and tailored.

## Roadmap

- Better semantic/LLM matching
- Resume-aware match explanations
- Company priority scoring
- Remote/hybrid/onsite preference scoring
- Salary filtering when compensation is published
- Daily digest notifications
- Optional MCP/LangGraph orchestration
