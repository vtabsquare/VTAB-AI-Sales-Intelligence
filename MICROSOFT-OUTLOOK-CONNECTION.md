# Microsoft Outlook / Microsoft Graph Connection — User Action Module

The application code is already wired for Microsoft Graph in two places:

1. **Outbound:** approved + verified outreach -> Microsoft Graph `sendMail`.
2. **Inbound:** Response Center sync -> Microsoft Graph Inbox delta query -> response classification -> follow-up task.

## What you need to provide/configure

Create or use a Microsoft Entra application registration in the tenant that owns the sender mailbox.

### Application permissions
Grant Microsoft Graph **Application** permissions:
- `Mail.Send`
- `Mail.Read`

Then grant **Admin consent** for the tenant. For production, restrict the application's mailbox access to the intended VTAB mailbox using your Microsoft 365 / Exchange application-access controls.

### Client credential
Create a client secret (or replace it later with a certificate/managed identity for stronger production security). Copy the secret **value at creation time** and store it only in `backend/.env` or a secret store.

### backend/.env
```env
APP_ENV=development
DEMO_MODE=true
MICROSOFT_TENANT_ID=<Directory/Tenant ID>
MICROSOFT_CLIENT_ID=<Application/Client ID>
MICROSOFT_CLIENT_SECRET=<Client secret VALUE>
MICROSOFT_SENDER_EMAIL=Contactsales@vtabsquare.com
GRAPH_TIMEOUT_SECONDS=30
```

Keep `DEMO_MODE=true` while testing the rest of the application. After the Admin page's **Test Microsoft Connection** succeeds and you intentionally want real email/inbox sync, set:

```env
DEMO_MODE=false
```

Restart FastAPI after every `.env` change.

## Validate in the UI
1. Open **Admin**.
2. Review **Outlook / Microsoft Graph** status.
3. Click **Test Microsoft Connection**.
4. Confirm the configured mailbox is returned.
5. Open **Send Center**. Real delivery remains subject to approval + verified recipient + DNC check + final human confirmation.
6. Open **Response Center** and run inbox sync to ingest replies.

## Security
- Never paste the Microsoft client secret into chat, screenshots, Git, frontend `.env.local`, or browser code.
- Do not grant broader Graph permissions than needed.
- Production should use mailbox scoping and preferably a certificate or managed identity instead of a long-lived client secret.
