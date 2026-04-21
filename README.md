# jobping-api

FastAPI backend for [JobPing](https://jobping.dev) — daily LLM-curated job digest emails.

Pairs with [`jobping-web`](https://github.com/neveon/jobping-web) (Next.js landing page).

## Stack
- FastAPI + uvicorn
- Supabase Postgres
- Anthropic Claude Haiku (matching)
- Resend (email)
- JobSpy + Levels.fyi scraper (job sourcing)
- Railway (hosting + daily cron)

## Local dev
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys
uvicorn main:app --reload
```

## Deploy
Auto-deploys to Railway on push to `main`.
