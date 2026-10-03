# Native Render deployment

`render.yaml` defines separate native Python API and Next.js web services on free plans in Singapore. It uses your existing remote SQL Server. No Docker or PostgreSQL is needed.

If no remote server exists, Azure SQL Database's free offer is a compatible option. It requires an Azure account/subscription. Apply the free offer and choose **Auto-pause the database until next month** when the monthly free allowance is exhausted; do not choose additional paid usage. See Microsoft's current [free offer documentation](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-offer?view=azuresql). Provisioning, credentials and firewall access must be completed before application deployment. Render's free managed PostgreSQL expires after 30 days and is not part of this SQL Server configuration.

## Required setup

1. In the intended Render account, connect GitHub and authorize only `vtabsquare/VTAB-AI-Sales-Intelligence`.
2. Create a Blueprint from this repository and select `main`.
3. Set `DATABASE_URL` securely in Render using SQL authentication:
   `mssql+pymssql://USER:URL_ENCODED_PASSWORD@SERVER:1433/DATABASE`.
   The cloud driver requires encrypted connections. The server must be reachable from the service; scope firewall access to Render's documented outbound IP ranges. Windows trusted authentication and `localhost` do not work from Render.
4. Set application `LOGIN_EMAIL`/`LOGIN_PASSWORD` and Microsoft application credentials in Render. The Render account password is unrelated to the application's login password. Never commit credentials.
5. Set the frontend `API_BASE_URL` to the API service's HTTPS URL (without trailing slash), then deploy both services.

Existing database schema is never created or migrated automatically. Run the read-only validator against the remote SQL Server before applying reviewed migrations. Microsoft credentials require mailbox access and OTP sending permission. Demo mode simulates customer outreach but retains real login/OTP authentication.

## Acceptance

- API `/api/health` returns 200; this is process health, not proof of database connectivity.
- Open the frontend URL: an unauthenticated request redirects to `/login`.
- Complete real login and OTP, then verify database-backed screens and Inbox sync/deduplication.
- Customer outbound mail remains simulated (`DEMO_MODE=true`) and scheduler stays disabled during acceptance.

Free services can sleep and have cold starts; this is an initial acceptance deployment. Do not treat it as an always-on scheduled production service. No paid resources are declared.
