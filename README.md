**Revenue Manager Agent for a Hotel General Manager** that uses reservation data to detect what is changing in future business, turn it into clear commercial judgment, and recommend what action to take next.

## Deploy (Part 8)

See [docs/DEPLOY.md](docs/DEPLOY.md) for Supabase load, Render deploy, and submission checklist.

Quick start after Supabase `DATABASE_URL` is set:

```powershell
python scripts/load_hosted_db.py
python -m agent.eval "What is our as-of date?"
```

Live service: Docker on Render (Starter+ plan), Basic Auth, SSE chat UI at `/`.
