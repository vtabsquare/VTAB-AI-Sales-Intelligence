# VTAB Global Opportunity Agent — Windows Native Setup

Docker and WSL are **not required** for local development. This variant runs Next.js, FastAPI and SQL Server directly on Windows. Redis is deferred until scheduled/background jobs are enabled.

## Prerequisites

1. Python 3.12 or 3.13 (`py --version`)
2. Node.js 20+ (`node --version`, `npm --version`)
3. Local Microsoft SQL Server
4. Microsoft ODBC Driver 18 for SQL Server

## Database

Create an empty database named `VTABOpportunityAgent`. In SSMS you can execute `scripts/create-database.sql`. The application creates the Phase-1 tables on first startup. Alembic migrations should be used before production deployment.

The default `backend/.env.example` assumes a default SQL Server instance at `localhost` with Windows Authentication. For SQL Server Express or another named instance, edit `DATABASE_URL` as shown in that file.

## Install

From Command Prompt in the repository root:

```bat
scripts\setup-windows.bat
```

## Start

```bat
scripts\start-windows.bat
```

Then open:

- Application: http://localhost:3000
- Swagger API: http://localhost:8001/docs

## Manual start

Backend:

```bat
cd backend
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8001
```

Frontend (second Command Prompt):

```bat
cd frontend
npm run dev
```

## Demo mode

Keep `DEMO_MODE=true`. No real email is sent. OpenAI and Microsoft Graph credentials are not required for the current demo workflow.
