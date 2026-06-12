**Revenue Manager Agent for a Hotel General Manager** that uses reservation data to detect what is changing in future business, turn it into clear commercial judgment, and recommend what action to take next.

## Deploy (Part 8)

See [docs/DEPLOY.md](docs/DEPLOY.md) for Render Postgres + Web Service deploy.

Quick start after Render Postgres **External URL** is set:

```powershell
python scripts/load_hosted_db.py
python -m agent.eval "What is our as-of date?"
```

Or use Blueprint: `render.yaml` creates **hotel-db** + **revenue-manager-agent** together.
