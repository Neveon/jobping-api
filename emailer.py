"""Resend email sender. Phase 2 = confirmation only; Phase 3 will add digest."""
from __future__ import annotations

import os

import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")


def _from_email() -> str:
    return os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")


def _api_base() -> str:
    return os.environ.get("API_BASE_URL", "").rstrip("/")


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
