# Phase 1 validation — 3 October 2026

## Passed in this workspace
- **37 backend tests**, including the original authentication/approval/suppression/mocked Graph/scheduler tests and new knowledge, workflow, country, structured-provider and CRUD tests.
- **25 Chromium browser checks** on a clean Next.js production build. Password + development OTP → knowledge create/approve/search → demo discovery → country configuration → opportunity filtering → keyboard detail → resumable supervisor → seven score dimensions → Approval Queue → CSV download → logout.
- No browser JavaScript errors. No horizontal document overflow on new screens at 1280×720, 768×480 and 390×844.
- TypeScript `tsc --noEmit` and Next.js production build.
- Ruff critical syntax/undefined-name checks (`E9,F63,F7,F82`).
- Fresh isolated SQLite database: all three Alembic revisions → explicit demo seed → `alembic check`: no new upgrade operations detected.

Browser acceptance creates its own temporary database and launches both real servers; it does not use the live mailbox, customer database or provider API. Demo fixtures are labeled. Live AI qualification was exercised with a mocked structured provider, not a billed live model call.

## Environment limits


## Evidence
- validation/phase1-browser-results.json
- validation/phase1_browser.py (repeatable acceptance harness; install Playwright and its Chromium headless shell)
- validation/phase1-pytest-output.txt
- validation/phase1-build-output.txt

## Run and next acceptance step

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
