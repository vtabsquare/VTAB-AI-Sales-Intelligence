# Neon PostgreSQL switch — 2026-10-03

Authorized cloud target: Neon PostgreSQL + native Render Python/Next.js, with no Docker.

- Created Neon project `VTAB-AI-Sales-Intelligence` (`floral-scene-95441480`), production branch, PostgreSQL 18, Singapore, Free plan.
- All 37 existing backend tests passed using isolated SQLite fixtures; no live mailbox calls.
- All three Alembic migrations executed successfully against an ephemeral PGlite PostgreSQL WASM engine through Psycopg 3, ending at `0003_countries`.
- PostgreSQL required-table/column reflection passed.
- Five database-backed checks passed: supervisor through human approval, approved knowledge retrieval, country query generation, expiry hard rejection, and resuming a failed workflow without repeating qualification.
- Render Blueprint validated against Render's official JSON schema.

PGlite is an embedded PostgreSQL build, not the provisioned Neon service. Its protocol multiplexing differs from a normal server. These checks do not prove live Neon TLS/connectivity, multi-client concurrency, Render deployment, or complete live mailbox sync.

Cloud application deployment remains pending: the intended Render account has no GitHub deployment credential; Google rejected the GitHub sign-in for this cloud browser. No Render application services were created. Set Neon `DATABASE_URL` securely in Render, connect only the intended repository, and deploy the Blueprint. Never share database passwords in chat.

Microsoft 365 token authentication and real Inbox read previously returned HTTP 200. Customer email was never sent. Customer outreach stays simulated and scheduler disabled during acceptance.
