from __future__ import annotations

import os
import re

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from cron import run_digest
from db import create_user, deactivate_by_token
from emailer import send_confirmation
from pdf_parser import extract_text
from rate_limit import check_and_record

MAX_PDF_BYTES = 5 * 1024 * 1024
MIN_RESUME_CHARS = 100
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = FastAPI(title="JobPing API")

origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "").split(",") if o.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/")
def root():
    return {"service": "jobping-api", "ok": True}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    resume: UploadFile = File(...),
):
    ip = _client_ip(request)
    if not check_and_record(ip):
        raise HTTPException(429, "Too many signups from this IP. Try again later.")

    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")

    if resume.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(400, "Resume must be a PDF file.")

    pdf_bytes = await resume.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(400, "Resume file is empty.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(400, "Resume too large (max 5MB).")

    try:
        resume_text = extract_text(pdf_bytes)
    except Exception as exc:
        print(f"[signup] pdf parse failed for {email}: {exc}", flush=True)
        raise HTTPException(400, "We couldn't read that PDF. Try re-exporting it.")

    if len(resume_text) < MIN_RESUME_CHARS:
        raise HTTPException(
            400,
            "That resume looks empty — make sure it's a real PDF with selectable text.",
        )

    try:
        user = create_user(email=email, resume_text=resume_text)
    except Exception as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            raise HTTPException(409, "That email is already signed up.")
        print(f"[signup] db insert failed for {email}: {exc}", flush=True)
        raise HTTPException(500, "Signup failed. Please try again in a minute.")

    try:
        send_confirmation(email=email, unsubscribe_token=user["unsubscribe_token"])
    except Exception as exc:
        print(f"[signup] confirmation email failed for {email}: {exc}", flush=True)

    return {"ok": True, "email": email}


@app.post("/admin/trigger-digest")
def trigger_digest(request: Request):
    expected = os.environ.get("ADMIN_TOKEN", "")
    token = request.headers.get("x-admin-token", "")
    if not expected or token != expected:
        raise HTTPException(401, "Unauthorized")
    return run_digest()


def _frontend_base() -> str:
    return origins[0].rstrip("/") if origins and origins[0] != "*" else ""


@app.get("/unsubscribe")
def unsubscribe(token: str = ""):
    target_base = _frontend_base() or "https://jobping.dev"
    if not token:
        return RedirectResponse(f"{target_base}/unsubscribe?status=invalid", 302)
    try:
        ok = deactivate_by_token(token)
    except Exception as exc:
        print(f"[unsubscribe] db error: {exc}", flush=True)
        return RedirectResponse(f"{target_base}/unsubscribe?status=error", 302)
    status = "ok" if ok else "invalid"
    return RedirectResponse(f"{target_base}/unsubscribe?status={status}", 302)
