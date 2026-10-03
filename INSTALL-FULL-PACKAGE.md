# VTAB Global Opportunity Agent — Full Fixed Package

This is a complete replacement package built from the original Windows/SQL Server project plus the completed Step 9–13 changes.

## Fixes included

- Correct model imports: `app.models.entities` (no `app.models.tables`).
- `main.py` imports the new SQLAlchemy models before `Base.metadata.create_all()`.
- Existing core API and new sales-intelligence API are both registered.
- CORS accepts both `localhost:3000` and `127.0.0.1:3000`.
- Send Center API uses the existing `Opportunity`, `Contact`, and `OutreachDraft` models.
- Email verification service is included.
- Secure outbound sender / Demo Mode is included.
- Response tracking, follow-up queue, and pipeline endpoints are included.
- Premium Send Center, Response Center, Pipeline, and sidebar UI are included.
- Frontend API base URL is fixed to `http://127.0.0.1:8000`.
- Safe Microsoft Graph settings are included, but no credentials are embedded.

## Before replacing your project

Keep a copy of your existing `backend/.env`. It contains your local settings and must not be lost.

## Recommended install

1. Stop backend and frontend.
2. Back up your current project folder.
3. Replace the project files with this package.
4. If you already have a working `backend/.env`, copy it back into `backend/.env`.
5. Make sure it contains:

```env
APP_ENV=development
DEMO_MODE=true
```

Do not set `DEMO_MODE=false` until Microsoft Graph is deliberately configured and tested.

## Backend

From the package root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If your existing `.venv` is already healthy, you do not need to recreate it; activate it and run `pip install -r requirements.txt`.

Test:
- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api/outreach/send-center

Expected Swagger includes both existing endpoints and:
- POST `/api/responses/sync`
- GET `/api/responses`
- GET `/api/follow-ups`
- POST `/api/follow-ups/{task_id}/approve`
- POST `/api/follow-ups/{task_id}/dismiss`
- GET `/api/pipeline`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:
- http://localhost:3000/outreach
- http://localhost:3000/responses
- http://localhost:3000/pipeline

## Microsoft Graph

The package remains safe in `DEMO_MODE=true`. Real outbound sending and inbox synchronization require your Entra app values in `backend/.env`:

```env
MICROSOFT_TENANT_ID=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_SENDER_EMAIL=Contactsales@vtabsquare.com
```

Do not place those secrets in the frontend.

## Database

On local development startup, `Base.metadata.create_all()` creates the new tables if they do not already exist:
- `mail_sync_states`
- `inbound_responses`
- `follow_up_tasks`

Existing opportunity/contact/outreach data is not intentionally deleted or reset by this package.
