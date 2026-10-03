> Historical UI checkpoint. Current Phase 1 implementation results are in docs/PHASE-1-VALIDATION.md.

# VTAB AI Sales Intelligence — UI repair validation, 3 October 2026

## Outcome

The updated source passes 23 backend tests, 76 automated browser checks, TypeScript validation, and the production frontend build. Browser errors: zero. Tests use an isolated SQLite database and mocked Microsoft Graph; they do not certify the user's live SQL Server or tenant.

## Changes

- Navigation has its own scrollable area; brand and sign-out stay reachable. Short desktop screens hide decorative status/footer content. Mobile navigation respects viewport height.
- Improved narrow-screen cards, integration grids, wrapping, focus outlines and reduced-motion support.
- Every protected page shows the backend's operating mode. Failed status retrieval shows MODE UNKNOWN, not a presumed LIVE or DEMO state. The banner refreshes on focus and on request.
- Dashboard metric chips reflect demo mode; removed the unsupported static claim that the agent is online.
- Admin distinguishes configured credentials from tested access, reports status failures with retry, and links directly to Discovery, Portfolio and Response Center.
- Response cards can be opened using Enter or Space; navigation exposes the active page and sign-out has a clear accessible name.
- New scripts/start-acceptance-windows.bat forces DEMO_MODE=true and SCHEDULER_ENABLED=false. It checks listening ports before starting, without killing other processes.
- Strengthened .gitignore to exclude frontend private environment files, logs, caches and generated folders. Added a non-secret frontend environment example.

No SQL database was deleted or recreated. Private environment files were not changed; they are excluded from the repository-ready ZIP. Human approval, recipient checks, suppression and final confirmation still govern sends.

## Current validation matrix

| Area | Result | Executed evidence |
|---|---|---|
| TypeScript | PASS | tsc --noEmit |
| Production frontend | PASS | npm run build, all application routes compiled |
| Backend | PASS | pytest: 23 tests, isolated test database |
| All 17 application routes | PASS | Authenticated desktop traversal and mobile traversal |
| Navigation and mode | PASS | 1280x720, 1024x600, 960x480, 768x650 and 390x844: Admin/sign-out reachable, scrolling and no admin horizontal overflow |
| Mobile layout | PASS | All 17 routes at 390x844: no document horizontal overflow |
| Authentication | PASS | Password rejection, OTP fixture, HttpOnly cookie, refresh, clean restart, logout/revoked-cookie rejection |
| Discovery and opportunities | PASS | Add connector, discover/deduplicate, qualify, research fallback, contact review and draft generation |
| Templates/resources/portfolio | PASS | Save/edit/preview and resource/capability creation |
| Send workflow | PASS | Human approval, recipient verification, separate final confirmation and simulated delivery |
| Inbox sync and follow-up | PASS, MOCKED | Graph sync, reply matching/details/filters, classification, approval, draft preparation/rejection |
| Microsoft connection UI | PASS, MOCKED | Connection test and refresh using Graph fixture |
| Error resilience | PASS | Malformed collection responses, backend failure, operating status unavailable/unknown |
| Schedules/logs/pipeline | PASS | Schedule run, job history, refresh and search |
| Browser runtime/console | PASS | Zero exceptions in the completed run |
| Live SQL Server | PENDING LOCAL ACCEPTANCE | This runtime cannot access the user's Windows SQL Server; no live schema/data check executed |
| Live Microsoft 365 OTP/inbox | PENDING LOCAL ACCEPTANCE | Actual tenant credentials and mailbox reads not executed here |
| Windows launcher | REVIEWED, NOT EXECUTED | Windows batch reviewed; host is Linux |
| GitHub push | PENDING REPOSITORY CREATION | GitHub connector supports writing existing repositories, not creating a new repository |

The reduced desktop viewports approximate the available CSS space at browser zoom. Native Edge zoom on the user's Windows machine was not executed. Route layout checks do not prove every possible dataset or long string layout.

## Windows acceptance

1. Extract into a new folder, preserving the currently running version as backup.
2. Copy the current private backend/.env and frontend/.env.local into the corresponding folders. Do not upload them to GitHub.
3. From the project root, run scripts\setup-windows.bat.
4. In the backend folder, run .venv\Scripts\python.exe schema_check.py. Review findings; do not recreate the database.
5. Stop the old frontend/backend terminals, then run scripts\start-acceptance-windows.bat from the root.
6. Open http://localhost:3000/login and verify a fresh real OTP. Confirm the DEMO MODE banner.
7. Admin: Test Microsoft Connection. Response Center: Sync Microsoft 365. Check the actual messages and repeat sync to verify no duplicates. No customer send is needed.
8. Check navigation at 125%, 150% and 200% zoom; sign-out and Admin must remain reachable. Log out, then open a protected route and confirm redirect to login.

If DEMO MODE is not shown, refresh mode and inspect the running backend; do not infer mode merely from a successful login. Changing DEMO_MODE requires restarting the backend.

## Reproduce automated checks

Backend: python -m pytest -q from backend with requirements installed.
Frontend: npm ci, npx tsc --noEmit, npm run build from frontend.
Browser: install Python Playwright and Chromium, then python validation/browser_smoke.py from root. Ports 8001 and 3000 must be free. The fixture sends no customer email.

Current browser evidence: validation/browser-results.json. Prior audit details: docs/VALIDATION-REPORT-2026-10-02.md (historical).

## Feature boundaries

LinkedIn-specific custom queries, domain filters and country selection were discussed but not implemented in this UI repair. Discovery continues to read configured sources and existing generated search intents. Rule-based qualification/classification are unchanged. Live provider capabilities must be tested separately.
