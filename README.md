# VTAB AI Sales Intelligence

VTAB Global Opportunity Intelligence for VTAB Square Private Limited. **Native Python + Next.js on Render with Neon PostgreSQL** is the current cloud deployment. No Docker is required. See [Render + Neon deployment](docs/RENDER-DEPLOYMENT.md). The Windows/SQL Server instructions below remain available for legacy local setups.

## Setup
Install Python 3.12, Node.js 22, SQL Server and Microsoft ODBC Driver 18 for SQL Server. From the repository folder:
```
scripts\setup-windows.bat
```
Preserve your working private backend/.env and frontend/.env.local. Configure DATABASE_URL for your existing SQL Server, LOGIN_EMAIL, LOGIN_PASSWORD, JWT_SECRET and Microsoft Graph credentials. Never commit these files.

## Database migration
Back up the database first. For an existing application database, from backend:
```
.venv\Scripts\python.exe adopt_baseline.py
```
Only after the comparison reports a match and the backup has been reviewed:
```
.venv\Scripts\python.exe adopt_baseline.py --stamp-reviewed-baseline
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe schema_check.py
```
If the schema differs, stop and review the differences; do not recreate customer tables or blindly stamp. For a new empty SQL Server database, run alembic upgrade head directly. Keep INITIALIZE_SCHEMA=false.

## Start
```
scripts\start-acceptance-windows.bat
```
Open http://localhost:3000/login. This launcher forces DEMO_MODE=true and disables scheduled jobs. Microsoft OTP delivery remains real when DEMO_AUTH=false. Customer sends are simulated. Existing configured Microsoft inbox sync remains read-only.
For an isolated offline demo, explicitly set DEMO_AUTH=true in development only; default demo OTP is 123456. Seed labeled demo records with `python -m app.seed` or Run Discovery Now. Keep demo fixtures separate from your customer database.

## Workflow
Discovery → Opportunities → select a record → Run / resume to approval → inspect seven qualification dimensions and approved knowledge → Approval Queue. Knowledge Base manages factual evidence. Country targets, opportunity search, country/stage filters, pagination and CSV export are available.

## Validation and release boundary
37 backend tests, 25 clean-build browser checks, TypeScript and production build passed. Microsoft 365 authentication and Inbox read access passed. Full Inbox import acceptance remains pending. Neon PostgreSQL is now the authorized cloud database; live Neon and Render acceptance are pending.
See [validation](docs/PHASE-1-VALIDATION.md), [local setup](docs/local-development.md), [database](docs/database-schema.md), [security](docs/security.md), [agent design](docs/agent-design.md) and [feature boundary](docs/requirements-status.md).
The master prompt is preserved for reference; your Windows-native/no-Docker instruction takes precedence over its generic stack suggestions. Entra SSO/RBAC, vector retrieval and later-phase modules remain future work.

## Read-only live validation on your Windows PC
Run `scripts\validate-live-windows.bat` from your checkout. It reads the private backend/.env, checks SQL connectivity and required tables/columns, authenticates with Microsoft Graph and checks Inbox read access. It never sends mail, modifies mailbox messages or changes the database. Results are saved to validation/live-validation-result.json; credentials, tokens and email contents are excluded. This checks connectivity/schema/read permissions; full inbox import, deduplication and reply matching still require application acceptance.
