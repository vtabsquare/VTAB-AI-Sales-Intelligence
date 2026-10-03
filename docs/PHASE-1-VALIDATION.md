# Phase 1 validation — 3 October 2026

## Passed in this workspace
- **37 backend tests**, including the original authentication/approval/suppression/mocked Graph/scheduler tests and new knowledge, workflow, country, structured-provider and CRUD tests.
- **25 Chromium browser checks** on a clean Next.js production build. Password + development OTP → knowledge create/approve/search → demo discovery → country configuration → opportunity filtering → keyboard detail → resumable supervisor → seven score dimensions → Approval Queue → CSV download → logout.
- No browser JavaScript errors. No horizontal document overflow on new screens at 1280×720, 768×480 and 390×844.
- TypeScript `tsc --noEmit` and Next.js production build.
- Ruff critical syntax/undefined-name checks (`E9,F63,F7,F82`).
- Fresh isolated SQLite database: all three Alembic revisions → explicit demo seed → `alembic check`: no new upgrade operations detected.
- Compose YAML service/dependency/environment checks. API startup on a migrated schema with INITIALIZE_SCHEMA=false.

Browser acceptance creates its own temporary database and launches both real servers; it does not use the live mailbox, customer database or provider API. Demo fixtures are labeled. Live AI qualification was exercised with a mocked structured provider, not a billed live model call.

## Environment limits
Docker Engine/Desktop is absent here. The Dockerfiles, Compose stack and GitHub Actions container acceptance job are committed, but a successful container build/start is **not claimed**. PostgreSQL and existing SQL Server migration execution must be validated in their configured environments. Live Microsoft Graph mailbox sync, live provider AI, Entra SSO, RBAC and production security acceptance remain outside this checkpoint.

A stale incremental Next.js output was detected during browser testing. The final browser result comes from a clean production build. Docker builds start from source without the local .next cache.

## Evidence
- validation/phase1-browser-results.json
- validation/phase1_browser.py (repeatable acceptance harness; install Playwright and its Chromium headless shell)
- validation/phase1-pytest-output.txt
- validation/phase1-build-output.txt

## Run and next acceptance step
From a fresh checkout: `python scripts/configure-demo.py`, then `docker compose up --build -d`. Follow README/local-development.md for credentials and demo OTP. Review `docker compose ps` and CI/container results before treating Docker execution as accepted.
Next: validate that stack against PostgreSQL, then perform the separately configured Microsoft 365 read-only inbox acceptance and existing SQL Server baseline comparison. Do not enable live outbound outreach as part of these checks.
