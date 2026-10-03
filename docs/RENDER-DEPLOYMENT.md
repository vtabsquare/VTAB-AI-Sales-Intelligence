# Render + Neon PostgreSQL

The cloud deployment uses Neon PostgreSQL and two free native Render services in Singapore. No Docker or paid resources are declared. SQL Server remains an optional legacy connection; the current cloud target is PostgreSQL.

1. Sign in to Neon, create a Free project named `VTAB-AI-Sales-Intelligence`, and choose Singapore if available. Keep the Free plan and default generated database credentials.
2. Copy the connection URL directly into Render's secret `DATABASE_URL` field. Never commit or paste credentials in chat. Both standard `postgresql://` and `postgresql+psycopg://` URLs work. Neon connections enforce TLS certificate verification; idle connections are closed so compute can sleep.
3. In the supplied Render account, connect GitHub and authorize this repository. Create a Blueprint from `main` using `render.yaml`.
4. Set application `LOGIN_EMAIL`, `LOGIN_PASSWORD` and Microsoft Graph credentials securely in Render. The Render account password is separate from the application's login password.
5. Set frontend `API_BASE_URL` to the API service's HTTPS URL without a trailing slash. Deploy both services.

The API runs `alembic upgrade head` before startup. This initializes the NEW Neon database with versioned migrations. Do not point it at an unrelated existing database. No demo records or customer data are imported automatically. `INITIALIZE_SCHEMA=false` prevents ad hoc schema creation.

Customer outreach remains simulated (`DEMO_MODE=true`), real OTP remains required (`DEMO_AUTH=false`), and scheduled work stays disabled until acceptance. Free Render services sleep and have cold starts; Neon also has free usage limits. This is an acceptance deployment, not an always-on production SLA.

Acceptance: API health returns 200, unauthenticated navigation redirects to login, real OTP succeeds, and database-backed screens plus Inbox import/deduplication work. Process health alone does not prove database or mailbox access. Use `python validate_live.py` for read-only schema and Graph checks.
