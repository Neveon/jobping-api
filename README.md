# jobping-api

FastAPI backend for **JobPing** — daily LLM-curated job digest emails.

**Live**: [jobping-web.vercel.app](https://jobping-web.vercel.app) · Frontend repo: [`jobping-web`](https://github.com/Neveon/jobping-web)

## What it does

| Endpoint | Purpose |
|---|---|
| `POST /signup` | Accepts email + PDF resume (multipart). Extracts text via pdfplumber, inserts into Supabase, sends a Resend confirmation email. Rate-limited to 5 signups per IP per hour. |
| `GET /unsubscribe?token=...` | Flips `active=false` for the matching user. 302-redirects to the frontend confirmation page. |
| `POST /admin/trigger-digest` | Gated by `x-admin-token` header. Runs the full daily pipeline on demand. |
| `GET /health` | Uptime check for Railway. |

Each day, a GitHub Actions cron (`.github/workflows/daily-digest.yml`) fires at 14:00 UTC (9am Central) and hits `/admin/trigger-digest`, which:

1. Scrapes ~20 Austin-area software roles from Indeed via [JobSpy](https://github.com/Bunsly/JobSpy)
2. For each active user, asks **Claude Haiku** to pick the 5 best fits from those 20 with one-sentence reasoning
3. Sends the digest via Resend and logs to `sent_digests`

Per-user failures (bad resume, LLM timeout, bounce) don't kill the cron for everyone else — each user is try/excepted independently.

## Architecture

```
  Browser                Vercel             Railway (FastAPI)         Supabase
     │                    │                   │                        │
     ├─ POST /signup ─────►│ (static site)    │                        │
     │                    └── form POST ──────►│                        │
     │                                        ├── pdfplumber extract   │
     │                                        ├── insert user ─────────►│
     │                                        └── Resend confirm ──┐    │
                                                                   │    │
  GitHub Actions ── cron 14:00 UTC ──────────► POST /admin/trigger │    │
                                                │                  │    │
                                                ├── JobSpy scrape  │    │
                                                ├── Anthropic match│    │
                                                ├── Resend digest ◄┘    │
                                                └── log digest ─────────►│
```

## Stack

- **FastAPI** + uvicorn (hosted on Railway)
- **Supabase Postgres** — two tables: `users`, `sent_digests`
- **Anthropic Claude Haiku** (`claude-haiku-4-5`) for job-to-resume matching
- **JobSpy** (`python-jobspy`) for Indeed scraping
- **Resend** for transactional email
- **pdfplumber** for resume PDF parsing
- **GitHub Actions** for the daily cron (Railway cron service would require splitting config across two services; GHA is simpler)

## Local dev

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload
```

## Deploy

Auto-deploys to Railway on push to `main`. All secrets live in Railway's Variables tab; see `.env.example` for the required list.

## Notes and scope

Built as a 48-hour MVP. Explicitly out of scope: auth, dashboards, job deduplication across days, vector search, multi-city selection. The LLM does fit judgment end-to-end — no keyword or rules filter.
