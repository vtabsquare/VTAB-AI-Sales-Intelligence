> Historical source-package notes. Superseded by VALIDATION-REPORT.md. Historical verification labels are not current acceptance results.

# VTAB AI Sales Intelligence — Enterprise UX, Authentication & Automation Upgrade

## Included in this build
- Advanced two-factor login: password + mandatory Microsoft 365 email OTP.
- Optional face-recognition/Windows Hello slot surfaced in Security Center for future WebAuthn/passkey enrollment.
- Session cookie and backend signed-token validation.
- Email Experience Studio with rich editor, HTML mode, preview, logo URL, signature, footer, CTA/divider/link tools, personalization tokens, template library and AI content generation.
- AI template generation uses the OpenAI Responses API when `OPENAI_API_KEY` is configured; otherwise a local starter draft is returned.
- Customer Response detail modal showing complete stored message body, sender, received time, classification, sentiment, confidence, AI summary, suggested action and suggested reply.
- Opportunity row action arrows now open the source URL when one is available.
- Scheduler adds timezone and preferred local run time.
- Job Monitor page with run status, history, duration, result/error and 30-second refresh.
- SQL Server-safe explicit lengths for all new indexed/key string columns.
- Restrained 5–10px corner radius across controls/cards instead of pill-heavy geometry.

## Authentication
Development credentials requested for this build:
- Email: `contactsales@vtabsquare.com`
- Password: `12345`

The second factor is mandatory. A six-digit OTP is sent to the same mailbox through Microsoft Graph and expires after 10 minutes. The existing Microsoft Graph application therefore needs working `Mail.Send` application permission and valid tenant/client/secret/sender configuration.

For production, change `LOGIN_PASSWORD`, rotate `JWT_SECRET`, rotate any exposed Microsoft application secret, and preferably move primary identity to Microsoft Entra ID / WebAuthn.

## New/updated routes
- `/login`
- `/templates`
- `/responses`
- `/schedulers`
- `/job-monitor`
- `/security`

## Scheduler behavior
The scheduler can run `DISCOVERY`, `INBOX_SYNC`, and `REPROCESS`. It does not schedule outbound customer email. Each execution creates a `workflow_run_history` record.

## Existing database compatibility
Startup non-destructively adds `timezone` and `run_at_time` to an existing `scheduled_workflows` table when missing. No existing opportunity or response tables are dropped.

## Start
Backend:
`C:\VTAB\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001`

Frontend:
`npm install`
`npm run dev`
