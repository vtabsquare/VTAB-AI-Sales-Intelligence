# VTAB AI Sales Intelligence — Workflow Center + Smart Inbound Upgrade

This package preserves the working Microsoft Graph integration and adds the intelligence/workflow layer requested.

## Added
- Workflow Center at `/workflow` with direct shortcuts to every major workspace.
- Sidebar shortcut: Workflow Center.
- Response Center `Reprocess Intelligence` action.
- Database-only reprocessing of already synchronized messages.
- Smart categories: CUSTOMER response intents, PROCUREMENT_UPDATE, AUTOMATED_NOTIFICATION, BOUNCE_NDR, INTERNAL, NEWSLETTER_MARKETING.
- Procurement notifications are classified before generic no-reply automation rules.
- Outreach/contact/subject matching.
- Stale pending/approved AI follow-ups are suppressed when reprocessing determines a message is non-actionable.
- Qualified response vs raw inbox KPIs.
- Human approval remains mandatory; reprocessing and inbox sync do not send mail.

## Upgrade safety
1. Keep/copy your existing `backend/.env`. Do not share the client secret.
2. Keep `DEMO_MODE=true` during validation.
3. Start backend and frontend normally.
4. Admin -> Test Microsoft Connection.
5. Response Center -> Reprocess Intelligence ONCE for existing records.
6. Use Sync Microsoft 365 for new mail.
7. Workflow Center is available at `http://localhost:3000/workflow`.

## Run
Backend:
`cd backend`
`python -m venv .venv` (first run only)
`.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt` (first run only)
`.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001`

Frontend:
`cd frontend`
`npm install` (first run only)
`npm run dev`

Compatibility shortcut: `/response-center` redirects to `/responses`.
