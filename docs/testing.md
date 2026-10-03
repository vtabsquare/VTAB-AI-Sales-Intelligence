# Testing
Backend: `cd backend && python -m pytest tests -q`. Tests use a temporary SQLite database, mock external providers, and never connect to private Graph/SQL Server settings.
Frontend: `cd frontend && npm ci && npx tsc --noEmit && npm run build`.
Migrations: on an isolated empty DB, `alembic upgrade head`, `python -m app.seed`, `alembic check`. PostgreSQL/SQL Server execution still needs environment-specific acceptance.
CI: GitHub Actions additionally runs Docker builds/health checks where Docker is available. CI success is not assumed merely because its configuration exists.

New tests cover supervisor completion/idempotency, failure resume, seven score dimensions, deadline overrides, knowledge approval/withdrawal, upload limits, local OTP and production guard, live demo-seed rejection, country targeting and private-source rejection. Existing tests cover approval, suppression, mocked Graph inbox processing, scheduler history, auth/session and API failures.
