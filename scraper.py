"""Scrapes Austin-area software engineering jobs via JobSpy.

Simplified from github.com/neveon/job-alerter for MVP:
- Single broad JobSpy query instead of per-company (latency-sensitive in cron).
- No SQLite persistence (fresh scrape each day).
- No rule-based filtering (the matcher LLM does fit judgment).
"""
from __future__ import annotations

import logging
from typing import Any

from jobspy import scrape_jobs as _jobspy_scrape

logger = logging.getLogger(__name__)

DEFAULT_LOCATION = "Austin, TX"
DEFAULT_SEARCH_TERMS = ["software engineer", "backend engineer"]


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any] | None:
    title = (row.get("title") or "").strip()
    company = (row.get("company") or "").strip()
    url = (row.get("job_url") or "").strip()
    if not (title and company and url):
        return None
    location = (row.get("location") or "").strip()
    description = (row.get("description") or "").strip()
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
    }


def scrape_austin_jobs(
    *,
    search_terms: list[str] | None = None,
    location: str = DEFAULT_LOCATION,
    hours_old: int = 168,
    radius_miles: int = 50,
    results_per_term: int = 30,
    max_total: int = 20,
) -> list[dict[str, Any]]:
    """Returns up to `max_total` unique jobs. Failures in one term don't kill others."""
    terms = search_terms or DEFAULT_SEARCH_TERMS
    seen_urls: set[str] = set()
    jobs: list[dict[str, Any]] = []

    for term in terms:
        try:
            df = _jobspy_scrape(
                site_name="indeed",
                search_term=term,
                location=location,
                results_wanted=results_per_term,
                hours_old=hours_old,
                distance=radius_miles,
                country_indeed="USA",
                verbose=False,
            )
        except Exception as exc:
            logger.warning("jobspy failed for term %r: %s", term, exc)
            continue

        if df is None or df.empty:
            continue

        for _, row in df.iterrows():
            job = _row_to_dict(row.to_dict())
            if not job or job["url"] in seen_urls:
                continue
            seen_urls.add(job["url"])
            jobs.append(job)
            if len(jobs) >= max_total:
                return jobs

    return jobs
