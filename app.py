import os

import streamlit as st

from job_finder.__main__ import load_yaml, recommendation, run
from job_finder.db import connect, list_jobs

st.set_page_config(page_title="Job Finder", page_icon="💼", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1400px; padding-top: 2rem;}
.job-card {padding: 1rem 1.1rem; border: 1px solid #ddd; border-radius: 12px; margin-bottom: .8rem;}
.score {font-size: 1.5rem; font-weight: 700;}
.small {color: #666; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

profile = load_yaml("config/profile.yaml")
minimum = int(profile.get("minimum_match_score", 80))

st.title("💼 Job Finder")
st.caption("Resume-aware U.S. job search • Human-controlled applications")

if "jobs" not in st.session_state:
    try:
        db = connect(os.getenv("DATABASE_PATH", "data/jobs.db"))
        st.session_state.jobs = list_jobs(db, 70)
    except Exception:
        st.session_state.jobs = []

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    run_now = st.button("🔎 Run Job Finder", type="primary", use_container_width=True)
with col2:
    refresh = st.button("↻ Refresh", use_container_width=True)

if run_now:
    with st.spinner("Searching U.S. jobs and ranking against your resume..."):
        st.session_state.jobs = run()
    st.success(f"Search complete — {len(st.session_state.jobs)} jobs discovered.")

if refresh:
    db = connect(os.getenv("DATABASE_PATH", "data/jobs.db"))
    st.session_state.jobs = list_jobs(db, 70)

jobs = st.session_state.jobs

st.divider()

# Filters
with st.expander("🔧 Filters", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        locations = sorted({j.location for j in jobs if j.location})
        selected_locations = st.multiselect("Location", locations)
    with f2:
        companies = sorted({j.company for j in jobs if j.company})
        selected_companies = st.multiselect("Company", companies)
    with f3:
        min_score = st.slider("Minimum match", 70, 100, max(70, minimum), 1)
    with f4:
        actions = st.multiselect("Recommendation", ["APPLY", "REVIEW", "STRETCH"], default=["APPLY", "REVIEW"])

filtered = []
for job in jobs:
    action = recommendation(job.score)
    if job.score < min_score:
        continue
    if selected_locations and job.location not in selected_locations:
        continue
    if selected_companies and job.company not in selected_companies:
        continue
    if actions and action not in actions:
        continue
    filtered.append(job)

m1, m2, m3 = st.columns(3)
m1.metric("Matching jobs", len(filtered))
m2.metric("Strong matches", sum(j.score >= 85 for j in filtered))
m3.metric("Locations", len({j.location for j in filtered}))

st.subheader(f"Jobs ({len(filtered)})")

if not filtered:
    st.info("No jobs match the current filters. Click **Run Job Finder** to search for fresh postings.")

for job in filtered:
    action = recommendation(job.score)
    with st.container(border=True):
        left, middle, right = st.columns([1.1, 5.2, 1.4])
        with left:
            st.markdown(f"<div class='score'>{job.score}/100</div>", unsafe_allow_html=True)
            st.caption(action)
        with middle:
            st.markdown(f"### {job.title}")
            st.write(f"**{job.company}**  •  {job.location}")
            if job.explanation:
                st.caption(job.explanation)
            if job.source:
                st.caption(f"Source: {job.source}")
        with right:
            st.link_button("🚀 Easy Apply", job.url, use_container_width=True)
            if st.button("Details", key=f"details-{job.key}", use_container_width=True):
                st.session_state[f"show-{job.key}"] = not st.session_state.get(f"show-{job.key}", False)
        if st.session_state.get(f"show-{job.key}", False):
            st.markdown("**Job description**")
            st.write(job.description or "No description available.")

st.divider()
st.caption("Easy Apply opens the employer's application page. The agent does not submit applications automatically.")
