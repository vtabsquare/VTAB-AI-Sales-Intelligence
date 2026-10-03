# VTAB AI Sales Intelligence — Repair and Validation Report

## Acceptance boundary

The complete source package was repaired and exercised using the real Next.js production server, the real FastAPI application, isolated SQLite databases, and explicit offline provider fixtures. This is an executed application/workflow validation, **not a claim of live SQL Server or Microsoft 365 production acceptance**. The requested ZIP filename is a delivery label; the matrix below defines what was verified.

No connection to, deletion of, or recreation of the existing `VTABOpportunityAgent` SQL Server database occurred. The uploaded archive remains intact. Both `backend/.env` and `frontend/.env.local` are byte-for-byte unchanged. No real customer outreach, reply, or OTP email was sent during testing. No secrets are printed in this report or test results.

## Architecture and audit

- Frontend: Next.js App Router, React, TypeScript; 17 application routes including the `/response-center` alias.
- Browser APIs: `/backend-api/...` → Next route handler → FastAPI `/api/...` on port 8001. Frontend runs on port 3000.
- Authentication: configured password → six-digit emailed OTP → hashed SQL challenge with expiry/attempt limit → signed session plus durable database fingerprint → canonical HttpOnly cookie → backend session validation. Customer email and OTP email use separate delivery paths; DEMO_MODE blocks customer delivery, not production OTP delivery.
- Database: 20 SQLAlchemy tables covering opportunities, companies, contacts, drafts, communications, suppression, agent audit, knowledge, inbox sync/response/follow-up state, portfolio, discovery connectors, resources, templates, assets, scheduled workflows/history, OTP challenges, and durable sessions.
- Providers: Microsoft Graph application credentials; optional Serper search and OpenAI template generation. No provider credentials were changed.
- `API-CONTRACT-INVENTORY.md` maps frontend call sites and backend operations. `validation/openapi.json`, `backend-endpoints.json`, and `database-models.json` contain the detailed contracts/models. Dynamic action URLs and their methods are explained in the inventory.

## Repairs

### API contracts and resilience

1. Replaced independent fragile fetch handling with a shared checked client. Successful collections must be arrays of records, with valid IDs, display strings and string-array fields; HTTP errors, malformed JSON, wrong shapes and bad records become visible errors before React state changes. Valid empty arrays remain empty states. Backend error objects are never passed to `.map()` or `.slice()`.
2. Shared error/success surface, retry controls, busy-state cleanup, loading/empty states, and a route error boundary. Dashboard errors are no longer represented as fabricated zero KPIs.
3. Nullable opportunity service matches are handled by the backend serializer. Closing date and qualification rationale use actual backend field names. Dashboard mode reflects backend mode; the dashboard is explicitly dynamic rather than incorrectly prerendered during build.
4. Generic platform PATCH updates only submitted fields. Creation checks names, URLs, template content, action type, timezone, clock time and intervals. Duplicate capability names return 409. Schedules with audit history cannot be deleted; they can be disabled.
5. Registered static outreach provider status before the dynamic draft lookup. Removed the competing rewrite so the route handler consistently owns authentication cookies.
6. Corrected proxy origin checks and middleware redirect host preservation for localhost/127.0.0.1, added request timeouts and rejection of cross-origin mutations, and stopped returning internal proxy/SQL error details.

### Authentication

1. Removed token persistence in localStorage and the compatibility cookie. Existing browser tokens are cleared on successful sign-in.
2. Middleware validates the actual backend session instead of accepting any nonempty cookie. Stale/revoked sessions redirect to login; provider outages produce a retryable unavailable response. `/login` remains reachable, and successful login honors a safe local return path.
3. Cookie: HttpOnly, SameSite=Lax, eight-hour max age, Secure when accessed using HTTPS. Local HTTP development appropriately uses a non-Secure cookie.
4. Added `auth_sessions` with token fingerprints, expiry and revocation. Logout revokes the backend session, including replay of a copied old cookie. Unique token IDs prevent same-second session collisions.
5. Atomic OTP attempt counting and consumption; expiry, five-attempt limit, replay rejection, resend throttling, challenge invalidation when delivery fails, and sanitized failure messages. No new default password/signing secret is hard-coded in production configuration.
6. Schema initialization is disabled by default. `schema_check.py` is read-only unless `--add-auth-session` is explicitly supplied; that option creates only the additive session table if missing.

### Business workflow

1. Added opportunity actions for qualification, source research, contact discovery and draft generation; added editable approval/reject controls. Approval itself sends nothing.
2. Research/contact discovery use source evidence with explicit unavailable fallbacks. A single published email may be proposed as UNVERIFIED; ambiguous candidates require human selection. Email addresses are not invented. These are source extraction/rule-based workflows, not a claim of autonomous external company verification.
3. Outstanding WAITING_APPROVAL/APPROVED/SENDING drafts are reused to prevent duplicates. Discovery URL deduplication remains in place.
4. Backend send requires approval, recipient verification, suppression checks and `{confirmed:true}`. Atomic claim prevents two requests sending the same approved draft. A provider failure leaves SEND_FAILED for human investigation rather than permitting a blind retry.
5. TEST_VERIFIED is accepted only in demo mode. Added an explicit human recipient evidence review and audit note; HUMAN_VERIFIED records a human attestation of the source, **not SMTP proof that the mailbox exists**. Domain/MX validation alone still does not declare a mailbox verified.
6. Reply matching normalizes contact email case and avoids matching arbitrary senders solely by a copied subject. Classification updates matched opportunity state, creates one pending recommendation per response, and respects unsubscribe suppression.
7. Follow-up approval sends nothing. Preparing an approved recommendation creates a WAITING_APPROVAL outreach draft. It must pass the same human approval and final send controls. Follow-up draft content is visible before approval.
8. Scheduler calculation uses the supplied UTC time and respects weekly intervals. Failed jobs roll back the work transaction and retain failure history. Scheduler shuts down cleanly. Windows timezone data is included.

### Build and setup

- Updated vulnerable Next.js/React dependencies to Next.js 15.5.27 / React 19.0.8 and locked PostCSS 8.5.28 through an override. Final production dependency audit reports zero known findings; this is not a penetration-test certification.
- Windows scripts use backend port 8001, quoted working directories and lockfile installation. Docker definitions no longer provision a conflicting PostgreSQL database; optional containers still need a reachable SQL Server and installed ODBC driver and were not validated here.
- Historical implementation-status documents are marked as superseded by this report.

Primary dependency references: [Next.js security update](https://nextjs.org/blog/security-update-2025-12-11), [PostCSS source-map advisory](https://github.com/postcss/postcss/security/advisories/GHSA-r28c-9q8g-f849). Installed versions and audit output are recorded in the lockfile and `validation/dependency-audit.json`.

## Automated execution results

The final backend suite runs against fresh temporary SQLite databases. Its fixture refuses to reset any other database. Tests override external integration settings and mock provider calls.

- Backend: **23 tests passed**. Password failure, OTP storage/expiry/attempt/replay/delivery failure, auth protection/session/logout, collection contracts, malformed inputs, PATCH preservation, duplicate capabilities/outstanding drafts, discovery extraction/deduplication, qualification/research/contact evidence, approved simulated send, suppression, explicit send confirmation, Graph OTP request, paginated/duplicate inbox sync, reply matching/classification/follow-up/pipeline, scheduler success/failure/history, nullable records, HTML/RSS parsing, sanitized backend failures, and SQL Server DDL compilation.
- TypeScript: `npx tsc --noEmit` passed. A second independent check of the clean exported source, with no .next/cache folder, also passed using `tsc --noEmit --incremental false`. The generated .next reference is omitted from the exported next-env.d.ts so a fresh checkout can be checked.
- Production frontend: `npm run build` passed, including all routes.
- FastAPI: startup/import, health, docs/OpenAPI and API execution passed under isolated database settings. SQL Server DDL compilation passed for all models; this is not a live schema comparison.
- Browser: **53 checks passed**; see the executed matrix and `validation/browser-results.json`. The harness starts backend and production frontend together, starts at `/login`, exercises the complete governed workflow, injects wrong-shape/500 responses, then restarts both processes and tests durable session/logout behavior.
- Python 3.12, Node 24, Chromium 134 were used in this environment. Python library deprecation warnings remain; they are recorded in the test count and are not runtime failures. Expected 401/403/500 test requests are intentional. Failed-resource console messages from those deliberate errors are excluded from runtime/hydration exception reporting.

## Executed page/workflow matrix

All page PASS entries below mean **executed with isolated data/offline providers**. They do not imply live mailbox or SQL Server certification.

| Page/workflow | Status | What was actually executed |
|---|---|---|
| Login/authentication | PASS | Wrong password, OTP request/verification through proxy, HttpOnly cookie, return path, refresh, stale cookie, logout; backend expiry/replay/attempt tests |
| Dashboard `/` | PASS | Authenticated production render, real test-database KPIs, actual browser refresh |
| Discovery | PASS | Connector creation, offline feed discovery, query/counter rendering, URL deduplication; skipped search connector error surfaced |
| Opportunities | PASS | Table/detail review, qualify, research fallback, contact review, draft generation; malformed list error |
| Approval Queue | PASS | Empty and populated states, subject/body editing, approval, follow-up rejection; no implicit send |
| Send Center | PASS | Manual recipient, test verification, final confirmation, simulated send; human evidence review and readiness without automatic send |
| Workflow Center | PASS | Workflow/shortcut rendering and navigation |
| Response Center | PASS | Mocked Graph sync, matching reply details, filter buttons, reprocess, follow-up approval and draft preparation |
| Response Center alias | PASS | `/response-center` redirects to `/responses` |
| Pipeline | PASS | Stage/classification objects, metrics, refresh after response processing |
| AI Agent Logs | PASS | Recorded activity and search filter |
| Templates | PASS | Empty/list states, save, select library entry, HTML/preview tabs, sandbox preview, local generation; malformed/500 responses |
| Portfolio | PASS | Seeded capabilities, form creation, list update; malformed response |
| Resources | PASS | Resource link creation and list; malformed response |
| Schedulers | PASS | Create hourly reprocess job, manual run; backend validates intervals/timezones, failed execution and history preservation |
| Job Monitor | PASS | Execution history and refresh; malformed response |
| Security | PASS | Session/configuration display and optional-factor unavailable state |
| Admin/Integrations | PASS | Status, mocked Graph connection check, refresh |
| Full governed journey | PASS | Discovery → qualification/research/contact → draft/edit/approval → verified recipient → confirmed simulated send → mock inbox → classification/matching → follow-up approval/draft → pipeline/audit |
| Failure resilience | PASS | Wrong-shape successful JSON on 11 list pages; server 500 shown as error; no React runtime/hydration exceptions |
| Restart/session lifecycle | PASS | Clean launch from login; restart backend and frontend; persisted session remains usable; logout revokes restored old cookie |
| Live SQL Server schema/data | INTENTIONALLY UNAVAILABLE | The supplied target is outside this runtime. Importing pyodbc here fails because libodbc.so.2 is absent. No live SQL was executed |
| Live OTP delivery | INTENTIONALLY UNAVAILABLE | Graph request contract and challenge behavior tested using mocks; actual recipient mailbox delivery not tested |
| Live Graph mailbox/token/permissions | INTENTIONALLY UNAVAILABLE | Mocked token/read/pagination executed; actual tenant permissions and mailbox access still need local acceptance |
| Real customer delivery/replies | INTENTIONALLY UNAVAILABLE | All customer sends were simulated; live send and delivered-message verification intentionally not performed |
| Serper/live source coverage | INTENTIONALLY UNAVAILABLE | No live search was used; deterministic feed and HTML/RSS parsers tested |
| OpenAI provider generation | INTENTIONALLY UNAVAILABLE | Local fallback executed; real model/API output not tested |
| Face recognition/WebAuthn | INTENTIONALLY UNAVAILABLE | Existing optional factor remains explicitly unconfigured |
| Template file attachments | INTENTIONALLY UNAVAILABLE | Existing editor selects local filenames only; no file upload/transmission feature is claimed |
| Docker/Windows execution here | INTENTIONALLY UNAVAILABLE | Windows instructions/scripts reviewed; this Linux run does not certify native Windows/ODBC or container execution |

## Remaining limits and local acceptance

- This is a single configured-user application. It does not implement a full multi-user identity/role-management system.
- Qualification and reply classification use rules. Source-based research and contact extraction require human validation of buyer identity, source reliability and mailbox ownership. Serper/OpenAI live behaviors need your configured environment.
- A Graph 202 result means accepted for processing, not proven delivery. SEND_FAILED requires investigation: a timeout can be ambiguous. Do not blindly recreate/resend an uncertain message.
- Existing SQL Server table/column types, nullability, indexes, foreign keys and record compatibility must be checked locally using the schema report. No destructive migration is included or authorized. Setting INITIALIZE_SCHEMA=true can perform additive initialization; it is unnecessary for the existing database and should not be used to resolve unknown schema differences without review.
- The supplied private environment files include legacy/unrelated keys; they were preserved exactly rather than reconstructed. Use configured credentials locally and do not paste them into screenshots or logs.
- Old session cookies will require fresh sign-in after adopting database-backed sessions. The auth_sessions table must exist before verification can establish a session.
- Browser provider fixtures are in `validation/serve_fixture.py` and never imported by the production application. Do not run that harness as the live server.

## Exact Windows startup — use a NEW folder

1. Keep the current running project as your backup. Extract the ZIP into a separate folder, for example:

   `C:\VTAB\VTAB-AI-Sales-Intelligence-END-TO-END-VERIFIED`

2. Prerequisites: Python 3.11/3.12, Node.js 22 or 24, Microsoft ODBC Driver 18 for SQL Server, and access to the existing `VTABOpportunityAgent` instance. Both original private env files are included unchanged. If your running version has newer private configuration, copy those two files into this new folder locally; do not overwrite them with examples.

3. Open Command Prompt:

```bat
cd /d "C:\VTAB\VTAB-AI-Sales-Intelligence-END-TO-END-VERIFIED"
scripts\setup-windows.bat
```

4. Check the existing database and add ONLY the durable session table if missing:

```bat
cd /d "C:\VTAB\VTAB-AI-Sales-Intelligence-END-TO-END-VERIFIED\backend"
.venv\Scripts\python.exe schema_check.py --add-auth-session
```

This command does not create/recreate the database or reset data. If it reports missing tables/columns, stop and review the differences; do not run `create-database.sql` or delete tables. To inspect without adding anything, omit `--add-auth-session`.

5. For the first local acceptance run, keep customer delivery simulated and schedules paused without editing private configuration:

```bat
cd /d "C:\VTAB\VTAB-AI-Sales-Intelligence-END-TO-END-VERIFIED"
set DEMO_MODE=true
set SCHEDULER_ENABLED=false
scripts\start-windows.bat
```

The two windows start FastAPI at `http://127.0.0.1:8001` and Next.js at `http://localhost:3000`. Open `http://localhost:3000/login`. Use the configured email/password and the actual OTP arriving in the configured mailbox. Wait one minute between OTP requests. Check `http://127.0.0.1:8001/api/health` and `/docs`.

For manual startup, use separate Command Prompt windows:

```bat
cd /d "C:\VTAB\VTAB-AI-Sales-Intelligence-END-TO-END-VERIFIED\backend"
set DEMO_MODE=true
set SCHEDULER_ENABLED=false
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

```bat
cd /d "C:\VTAB\VTAB-AI-Sales-Intelligence-END-TO-END-VERIFIED\frontend"
npm run dev -- --port 3000
```

Production build validation, in the frontend folder:

```bat
npx tsc --noEmit
npm run build
npm run start -- --port 3000
```

Stop the development frontend first so port 3000 is free. Start the backend before navigating protected production pages.

6. Local live acceptance checklist: schema check passes; password and real Graph OTP delivery work; refresh preserves session; logout revokes it; Microsoft connection test succeeds; read-only inbox sync works; traverse the same matrix with your existing records. Keep DEMO_MODE=true while checking outreach. Enable real customer sending only when a human explicitly approves a real draft, validates recipient evidence, and confirms the final send.

## Reproduce automated checks

```bat
cd backend
.venv\Scripts\python.exe -m pytest -q --disable-warnings
cd ..\frontend
npx tsc --noEmit
npm run build
npm audit --omit=dev
```

Optional automated browser suite after the production build:

```bat
cd ..
backend\.venv\Scripts\python.exe -m pip install playwright==1.51.0
backend\.venv\Scripts\python.exe -m playwright install chromium
backend\.venv\Scripts\python.exe validation\browser_smoke.py
```

The browser runner owns ports 8001/3000 for its temporary test processes. Stop other processes using those ports before running it. It uses temporary test databases and mocked providers, not your SQL Server or live mail settings.

## Included evidence

`validation/backend-test-results.txt`, `typescript-results.txt`, `frontend-build-results.txt`, `dependency-audit.json`, `browser-results.json`, `browser-run-output.txt`, `environment-preservation.json`, API inventories and model snapshots. The package excludes node_modules, .next, virtual environments, Python caches, TypeScript build info, test databases and generated caches.
