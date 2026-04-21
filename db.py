"""Supabase data access. All writes use service-role key — bypasses RLS."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def create_user(email: str, resume_text: str) -> dict[str, Any]:
    """Insert a new user. Raises on duplicate email (unique constraint)."""
    res = (
        get_client()
        .table("users")
        .insert({"email": email, "resume_text": resume_text})
        .execute()
    )
    return res.data[0]


def get_user_by_email(email: str) -> dict[str, Any] | None:
    res = (
        get_client()
        .table("users")
        .select("*")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def list_active_users() -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("users")
        .select("*")
        .eq("active", True)
        .execute()
    )
    return res.data or []


def deactivate_by_token(token: str) -> bool:
    """Flip active=false for the user with this unsubscribe_token. Returns True if updated."""
    res = (
        get_client()
        .table("users")
        .update({"active": False})
        .eq("unsubscribe_token", token)
        .execute()
    )
    return bool(res.data)


def log_digest(user_id: str, job_count: int) -> None:
    get_client().table("sent_digests").insert(
        {"user_id": user_id, "job_count": job_count}
    ).execute()
