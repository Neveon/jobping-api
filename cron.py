"""Daily digest: scrape once, match per user, email each. Tolerates per-user failures."""
from __future__ import annotations

import logging
import sys
from typing import Any

from db import list_active_users, log_digest
from emailer import send_digest
from matcher import match_jobs
from scraper import scrape_austin_jobs

log = logging.getLogger("cron")


def run_digest() -> dict[str, Any]:
    users = list_active_users()
    log.info("active users: %d", len(users))

    summary: dict[str, Any] = {
        "active_users": len(users),
        "jobs_scraped": 0,
        "sent": 0,
        "no_matches": 0,
        "errors": 0,
    }

    if not users:
        return summary

    log.info("scraping jobs...")
    try:
        jobs = scrape_austin_jobs()
    except Exception as exc:
        log.exception("scraper crashed: %s", exc)
        summary["errors"] += 1
        return summary

    summary["jobs_scraped"] = len(jobs)
    log.info("scraped %d jobs", len(jobs))
    if not jobs:
        log.warning("zero jobs scraped — skipping digest run")
        return summary

    for user in users:
        email = user.get("email", "?")
        try:
            matches = match_jobs(user["resume_text"], jobs)
            if not matches:
                log.warning("no matches for %s", email)
                summary["no_matches"] += 1
                continue
            send_digest(
                email=email,
                matches=matches,
                unsubscribe_token=user["unsubscribe_token"],
            )
            log_digest(user["id"], len(matches))
            summary["sent"] += 1
            log.info("sent digest to %s (%d matches)", email, len(matches))
        except Exception as exc:
            summary["errors"] += 1
            log.exception("digest failed for %s: %s", email, exc)

    log.info("done: %s", summary)
    return summary


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    summary = run_digest()
    # Non-zero exit if no digests went out (alerts Railway cron)
    return 0 if summary["sent"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
