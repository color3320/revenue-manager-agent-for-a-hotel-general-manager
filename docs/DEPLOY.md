# Hosted DB setup (one-time, from your machine)

Requires: Supabase account, `supabase` CLI logged in (`supabase login`).

## 1. Create Supabase project

```powershell
supabase projects create revenue-manager-hotel --org-id YOUR_ORG_ID --region us-east-1
```

Or create at https://supabase.com/dashboard → New project.

## 2. Get connection string

Project Settings → Database → URI (Session mode, port 5432).

## 3. Apply schema + load data

```powershell
$env:DATABASE_URL = "postgresql://postgres.[ref]:[password]@...pooler.supabase.com:5432/postgres"

# Apply schema (use Supabase SQL Editor if psql is not installed)
Get-Content schema.sql | supabase db execute --db-url $env:DATABASE_URL

# Or paste schema.sql into Supabase SQL Editor and run.

python -m etl.run_etl --from-cache
```

Confirm output ends with `VERIFY PASSED` and `dataset_metadata.as_of_date = 2026-06-11`.

## 4. Render deploy

1. Push repo to GitHub.
2. Render Dashboard → New Web Service → Docker → connect repo.
3. Plan: **Starter** ($7/mo) — not Free.
4. Health check: `/health`
5. Environment variables:

| Key | Value |
|-----|-------|
| ENV | production |
| DATABASE_URL | (Supabase URI) |
| ANTHROPIC_API_KEY | (your key) |
| AGENT_MODEL | anthropic:claude-sonnet-4-6 |
| BASIC_AUTH_USER | (grader username) |
| BASIC_AUTH_PASS | (strong password) |

Or use Blueprint: `render.yaml` in repo root.

## 5. Smoke test

```powershell
$env:DATABASE_URL = "..."  # Supabase
python -m agent.eval "What is our as-of date?"
```

Open live URL in incognito; confirm Basic Auth + streaming activity panel.

## 6. Submit

- Live URL (public)
- Username + password via LinkedIn DM only
- Link to your repo: https://github.com/color3320/revenue-manager-agent-for-a-hotel-general-manager
- Leave service running on paid instance
