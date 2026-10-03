# VTAB AI Sales Intelligence

VTAB Global Opportunity Intelligence for VTAB Square Private Limited. Phase 1 of the attached master build prompt is implemented on top of the existing reviewed application.

## Run the local demo
Requires Docker Desktop/Engine with Compose v2 and Python 3.12.
```
python scripts/configure-demo.py
docker compose up --build -d
```
Open http://localhost:3000/login. Read the generated root .env for LOGIN_EMAIL and LOGIN_PASSWORD; enter development OTP **123456**. This local demo does not send customer email.

Go to Discovery Engine → Run Discovery Now → Opportunities → select a record → Run / resume to approval → inspect seven-dimensional qualification/evidence → review the draft in Approval Queue. Knowledge Base manages approved capability evidence; Discovery Engine manages country targets. Opportunity search, country/stage filters, pagination and CSV export are available.

## Architecture and setup
- [Architecture and assumptions](docs/phase-1-design.md), [architecture](docs/architecture.md), [agent design](docs/agent-design.md)
- [Database and migrations](docs/database-schema.md), [API](docs/api.md)
- [Local development](docs/local-development.md), [environment variables](docs/environment-variables.md), [deployment](docs/deployment.md)
- [Security](docs/security.md), [tests](docs/testing.md), [current validation](docs/PHASE-1-VALIDATION.md)
- [Master requirements](docs/MASTER-BUILD-PROMPT.txt) and [implementation boundary](docs/requirements-status.md)
- [Existing Microsoft Graph setup](MICROSOFT-OUTLOOK-CONNECTION.md)

Backend: Python/FastAPI/SQLAlchemy. Frontend: Next.js/React/TypeScript. New Docker default: PostgreSQL; existing SQL Server deployments remain configurable. Alembic manages schema upgrades explicitly. A separate scheduler worker runs discovery/inbox/reprocessing; Redis is provisioned for future queue migration.

## Native commands
From backend: install requirements.txt into a virtual environment; configure environment; `alembic upgrade head`; `python -m app.seed`; `uvicorn app.main:app --host 127.0.0.1 --port 8001`. Worker: `python -m app.worker` in a separate terminal. Frontend: `npm ci`, `npm run dev`. See local-development.md for required settings.

Tests: `cd backend && python -m pytest tests -q`; frontend: `npx tsc --noEmit && npm run build`.

## AI and external integrations
Demo/local qualification is a labeled deterministic rule engine. Live semantic qualification and outreach use AI_PROVIDER=openai (or azure), a compatible OPENAI_MODEL, OPENAI_API_KEY and AI_ENDPOINT. Only approved knowledge can substantiate capability claims. SERPER_API_KEY enables live web search; public RSS/website connectors remain pluggable. Graph credentials are configured locally and never committed.

## Release boundary
This is the Phase 1 implementation, not certification of the entire 80-section production vision. Entra SSO/RBAC, pgvector embeddings, advanced reports, distributed queues, full semantic deduplication and optional Phase 4 modules remain future work. Live Microsoft 365/SQL Server acceptance remains pending. Existing human approval, recipient evidence/verification, suppression and final-send confirmation controls remain enforced. See the validation report for what ran here and what did not.
