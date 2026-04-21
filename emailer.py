"""Resend email sender: confirmation + daily digest."""
from __future__ import annotations

import html as html_escape
import os
from datetime import datetime
from typing import Any

import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")


def _from_email() -> str:
    return os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")


def _api_base() -> str:
    return os.environ.get("API_BASE_URL", "").rstrip("/")


def _esc(s: str) -> str:
    return html_escape.escape(s or "", quote=True)


def send_confirmation(*, email: str, unsubscribe_token: str) -> None:
    """Fires a 'you're signed up' email. Raises on Resend API failure."""
    unsub_url = f"{_api_base()}/unsubscribe?token={unsubscribe_token}"
    html = f"""<!DOCTYPE html>
<html>
  <body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:560px;margin:40px auto;padding:0 16px;color:#111;line-height:1.5;">
    <h2 style="margin:0 0 16px;">You're signed up for JobPing.</h2>
    <p>Starting tomorrow, you'll get the 5 best-matched jobs in your inbox every morning at 9am Central.</p>
    <p>We'll match roles against your resume using Claude — no dashboards, no spam, just one clean email a day.</p>
    <p style="color:#666;font-size:13px;margin-top:32px;">
      Changed your mind? <a href="{unsub_url}" style="color:#666;">Unsubscribe</a> — one click, no questions.
    </p>
  </body>
</html>"""
    resend.Emails.send(
        {
            "from": _from_email(),
            "to": email,
            "subject": "You're in — JobPing signup confirmed",
            "html": html,
        }
    )


def _match_card(match: dict[str, Any]) -> str:
    job = match["job"]
    title = _esc(job.get("title", ""))
    company = _esc(job.get("company", ""))
    location = _esc(job.get("location", ""))
    url = _esc(job.get("url", ""))
    reasoning = _esc(match.get("reasoning", ""))
    return f"""
    <div style="border:1px solid #e5e5e5;border-radius:8px;padding:16px;margin:12px 0;">
      <div style="font-size:16px;font-weight:600;color:#111;">{title}</div>
      <div style="font-size:14px;color:#555;margin-top:2px;">{company} &middot; {location}</div>
      <div style="font-size:14px;color:#333;margin-top:10px;line-height:1.5;">
        <span style="color:#888;">Why:</span> {reasoning}
      </div>
      <div style="margin-top:14px;">
        <a href="{url}" style="display:inline-block;background:#111;color:#fff;text-decoration:none;padding:8px 14px;border-radius:6px;font-size:13px;">Apply &rarr;</a>
      </div>
    </div>
    """


def send_digest(
    *,
    email: str,
    matches: list[dict[str, Any]],
    unsubscribe_token: str,
) -> None:
    """Send the daily 5-job digest. Raises on Resend API failure."""
    unsub_url = f"{_api_base()}/unsubscribe?token={unsubscribe_token}"
    today = datetime.now().strftime("%A, %B %-d")
    cards = "".join(_match_card(m) for m in matches)
    count = len(matches)

    html = f"""<!DOCTYPE html>
<html>
  <body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:32px auto;padding:0 16px;color:#111;line-height:1.5;background:#fff;">
    <div style="border-bottom:1px solid #eee;padding-bottom:12px;margin-bottom:8px;">
      <div style="font-size:20px;font-weight:600;">JobPing</div>
      <div style="font-size:13px;color:#888;">{today} &middot; {count} pick{'s' if count != 1 else ''} for you</div>
    </div>
    {cards}
    <p style="color:#888;font-size:12px;margin-top:32px;text-align:center;">
      <a href="{_esc(unsub_url)}" style="color:#888;">Unsubscribe</a> &middot; one click, no questions
    </p>
  </body>
</html>"""

    resend.Emails.send(
        {
            "from": _from_email(),
            "to": email,
            "subject": f"Your JobPing picks for {today}",
            "html": html,
        }
    )
