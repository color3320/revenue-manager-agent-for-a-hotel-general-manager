# Deploy with Render Postgres + Render Web Service

Everything runs on Render — no Supabase required.

## Architecture

| Component | Render resource | Notes |
|-----------|-----------------|-------|
| Postgres | **PostgreSQL** database | Hotel data + LangGraph checkpoints |
| Agent + UI | **Web Service** (Docker, Starter plan) | FastAPI + chat UI |

The web service must be **Starter ($7/mo) or higher** so graders don't hit a cold/sleeping instance. The Postgres DB can be **Free** for the hackathon (upgrade if you want always-on DB).

---

## Option A — Blueprint (recommended)

1. Push this repo to GitHub.
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect repo → Render reads [`render.yaml`](../render.yaml) and creates **hotel-db** + **revenue-manager-agent**.
4. When prompted, set secrets:
   - `ANTHROPIC_API_KEY`
   - `BASIC_AUTH_USER` (e.g. `grader`)
   - `BASIC_AUTH_PASS` (strong password)
5. Wait for both resources to finish creating.

### Load data (one-time, from your machine)

Render Postgres is empty until you load it. Use the **External Database URL**:

1. Render → **hotel-db** → **Connections** → copy **External Database URL**.
2. From your project folder:

```powershell
$env:DATABASE_URL = "postgresql://hotel_hackathon:...@...render.com/hotel_hackathon"
python scripts/load_hosted_db.py
```

Confirm output ends with **`VERIFY PASSED`** and `dataset_metadata.as_of_date = 2026-06-11`.

3. Update local `.env` with the same `DATABASE_URL` (External URL is fine for local eval too).

The web service already has `DATABASE_URL` wired via Blueprint (`fromDatabase`). Redeploy is not required after loading data.

---

## Option B — Manual setup

### 1. Create Postgres

1. Render → **New** → **PostgreSQL**.
2. Name: `hotel-db`, database: `hotel_hackathon`, user: `hotel_hackathon`.
3. Plan: **Free** (or Basic for production).
4. Create → copy **External Database URL** (for ETL from laptop).

### 2. Load schema + data (one-time)

```powershell
$env:DATABASE_URL = "postgresql://..."   # External URL from step 1
python scripts/load_hosted_db.py
```

### 3. Create Web Service

1. Render → **New** → **Web Service** → connect GitHub repo, branch `dev`.
2. **Environment:** Docker.
3. **Plan:** **Starter** (not Free).
4. **Health check path:** `/health`
5. Environment variables:

| Key | Value |
|-----|-------|
| `ENV` | `production` |
| `DATABASE_URL` | **Internal Database URL** from Postgres (same region as web service) |
| `ANTHROPIC_API_KEY` | your key |
| `AGENT_MODEL` | `anthropic:claude-sonnet-4-6` |
| `BASIC_AUTH_USER` | grader username |
| `BASIC_AUTH_PASS` | strong password |

Use **Internal URL** on the web service (Render private network). Use **External URL** only when running ETL/eval from your laptop.

---

## Smoke test

```powershell
$env:DATABASE_URL = "..."   # Render External URL
python -m agent.eval "What is our as-of date?"
```

Expect: **June 11, 2026**, tool `describe_dataset`.

Open the live web service URL in **incognito** → Basic Auth prompt → ask a question → confirm activity panel shows **Planning**, **Skill**, **Tool** (and **Subagent** when delegated).

---

## Submit

- Live agent URL (auth-protected)
- Username + password via **LinkedIn DM only** (not in repo)
- Repo link: https://github.com/color3320/revenue-manager-agent-for-a-hotel-general-manager
- Leave **Starter** web service running through the evaluation window
