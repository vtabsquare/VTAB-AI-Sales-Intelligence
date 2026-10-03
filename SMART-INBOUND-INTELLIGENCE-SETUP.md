# VTAB Smart Inbound Intelligence Upgrade

This package preserves the working Microsoft Graph read-only integration and adds:

- smart inbound filtering: CUSTOMER / PROCUREMENT / AUTOMATED / BOUNCE-NDR / INTERNAL / MARKETING
- contact + normalized subject/thread matching to existing outreach
- qualified customer-response KPIs separate from raw inbox volume
- safe suggested replies for interested / needs-info / follow-up-later cases
- human approval queue; approval does not send email
- reprocess endpoint/button to clean up messages imported by the previous package
- Microsoft 365 delta sync and duplicate prevention remain intact

## Upgrade existing installation

1. Back up the existing project and database.
2. Replace application files with this package, but KEEP your existing `backend/.env`.
3. Do not copy a client secret into source control.
4. Backend: create `.venv` if needed, install `requirements.txt`, run Uvicorn on 8001.
5. Frontend: `npm install`, then `npm run dev`.
6. Open Admin and confirm Microsoft connection.
7. Open Response Center and click **Reprocess Intelligence** once. This reclassifies the messages already imported by the previous package without rereading or modifying Outlook.
8. Click **Sync Microsoft 365** for new messages.

## Safety

Keep `DEMO_MODE=true` during validation. Inbox sync is read-only. Reprocessing only updates the local VTAB database. Follow-up approval does not send email. No message is deleted, moved, marked read, or replied to by the sync process.
