# VTAB Microsoft 365 Inbox Sync + Response Center

This package enables a **read-only** Microsoft 365 inbox synchronization while `DEMO_MODE=true`.

## Safety behavior
- Reads the configured `MICROSOFT_SENDER_EMAIL` Inbox through Microsoft Graph.
- Does not send, reply, delete, move, mark-read, or modify email during sync.
- Deduplicates imported Graph messages in `inbound_responses`.
- Classifies replies and creates human-review follow-up tasks.
- Outbound email remains blocked by `DEMO_MODE=true`.

## Backend .env
Keep your real client secret only in `backend/.env`; it is intentionally NOT included in this ZIP.

```env
APP_ENV=development
DEMO_MODE=true
MICROSOFT_TENANT_ID=<your tenant id>
MICROSOFT_CLIENT_ID=<your client id>
MICROSOFT_CLIENT_SECRET=<your current secret VALUE>
MICROSOFT_SENDER_EMAIL=Contactsales@vtabsquare.com
```

## Install / update
Copy the package over your current project, preserving your local `backend/.env`.

Backend:
```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Frontend (second terminal):
```powershell
cd frontend
npm install
npm run dev
```

## Validation
1. Open `http://127.0.0.1:8001/api/health` and confirm `{"status":"ok"}`.
2. Open `http://localhost:3000/admin` and run **Test Microsoft Connection**.
3. Open **Response Center**.
4. Click **Sync Microsoft 365**.
5. Imported Inbox replies should appear under **Customer Responses**.
6. Recommended follow-ups appear in **Follow-up Queue** and require human approval.

## API endpoints
- `GET /api/integrations/microsoft/status`
- `POST /api/integrations/microsoft/test`
- `POST /api/responses/sync`
- `GET /api/responses`
- `GET /api/follow-ups`
- `POST /api/follow-ups/{id}/approve`
- `POST /api/follow-ups/{id}/dismiss`
- `GET /api/pipeline`

## Important
The first sync can import existing Inbox messages because it establishes the initial Graph delta state. Subsequent syncs use the stored delta link and deduplicate messages.
