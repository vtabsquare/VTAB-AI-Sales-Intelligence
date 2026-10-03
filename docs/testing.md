# Testing
Backend: `cd backend && python -m pytest tests -q`. Tests use a temporary SQLite database, mock external providers, and never connect to private Graph/SQL Server settings.
Frontend: `cd frontend && npm ci && npx tsc --noEmit && npm run build`.

New tests cover supervisor completion/idempotency, failure resume, seven score dimensions, deadline overrides, knowledge approval/withdrawal, upload limits, local OTP and production guard, live demo-seed rejection, country targeting and private-source rejection. Existing tests cover approval, suppression, mocked Graph inbox processing, scheduler history, auth/session and API failures.

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
