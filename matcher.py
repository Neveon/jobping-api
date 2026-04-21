"""Claude Haiku matcher: resume + jobs -> top 5 with reasoning."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_DESCRIPTION_CHARS = 600
MAX_RESUME_CHARS = 6000

SYSTEM_PROMPT = (
    "You are a job-matching assistant. Given a candidate's resume and a list of "
    "job postings, pick the 5 jobs that best fit the candidate's experience, "
    "skills, and seniority. Return JSON of the form: "
    '{"matches": [{"index": <int>, "reasoning": "<one sentence why this matches>"}]}. '
    "Do not include any other text."
)


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # remove opening fence line
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        # remove closing fence
        if t.endswith("```"):
            t = t[: -3]
        t = t.strip()
    return t


def _format_jobs(jobs: list[dict[str, Any]]) -> str:
    lines = []
    for i, job in enumerate(jobs):
        desc = (job.get("description") or "")[:MAX_DESCRIPTION_CHARS]
        lines.append(
            f"[{i}] {job.get('title', '')} at {job.get('company', '')} "
            f"({job.get('location', '')})\n{desc}"
        )
    return "\n\n".join(lines)


def match_jobs(
    resume_text: str, jobs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Returns [{job: <dict>, reasoning: <str>}, ...] with up to 5 items.

    Empty list on any failure (LLM error, bad JSON, invalid indices).
    """
    if not jobs:
        return []

    resume_snippet = (resume_text or "").strip()[:MAX_RESUME_CHARS]
    user_msg = (
        f"Resume:\n{resume_snippet}\n\n---\n\n"
        f"Job postings ({len(jobs)} total):\n{_format_jobs(jobs)}"
    )

    try:
        resp = _client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as exc:
        logger.warning("anthropic call failed: %s", exc)
        return []

    try:
        raw = resp.content[0].text
    except Exception as exc:
        logger.warning("unexpected anthropic response shape: %s", exc)
        return []

    try:
        data = json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError as exc:
        logger.warning("matcher returned non-JSON: %s | raw=%s", exc, raw[:500])
        return []

    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for m in data.get("matches", [])[:5]:
        idx = m.get("index")
        if not isinstance(idx, int) or idx in seen or not (0 <= idx < len(jobs)):
            continue
        seen.add(idx)
        out.append(
            {
                "job": jobs[idx],
                "reasoning": (m.get("reasoning") or "").strip(),
            }
        )
    return out
