# VTAB Global Opportunity Agent

Runnable Phase-1 implementation of VTAB's agentic opportunity intelligence platform.

## Architecture
Next.js UI -> FastAPI API -> deterministic workflow/services + specialized agent run log -> PostgreSQL. Redis is included for production background-job evolution. External search, OpenAI, Entra and Microsoft Graph are adapter boundaries; Demo Mode works without credentials.

## Run
```bash
docker compose up --build
```
Open http://localhost:3000 and API docs at http://localhost:8000/docs.

Seed opportunities:
```bash
curl -X POST http://localhost:8000/api/opportunities/discover
```
Then qualify/research/find-contact/generate outreach using Swagger or REST endpoints.

## Test
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Safety
`DEMO_MODE=true` never sends real email. Outreach send requires `APPROVED`. Contacts have verification state; the demo contact intentionally has no invented email. Production credentials are environment-only.

## Phase 1 scope
Implemented: opportunity persistence, demo discovery, URL deduplication, deterministic qualification dimensions, research trace, contact safety, capability match, outreach generation, approval queue, simulated sending, response simulation, dashboard and agent logs.

Production enablement still requires Entra auth/RBAC enforcement, Alembic-managed schema rollout, live permitted search adapters, OpenAI provider calls, pgvector ingestion, Microsoft Graph, Celery schedules, compliance rules by jurisdiction, and full observability.
