# Windows-native local development
Python 3.12, Node.js 22, SQL Server and Microsoft ODBC Driver 18 are prerequisites. No Docker or PostgreSQL installation is required.
Run scripts/setup-windows.bat. Preserve private backend/.env and frontend/.env.local, and configure the existing SQL Server DATABASE_URL. Configure LOGIN_EMAIL, LOGIN_PASSWORD, JWT_SECRET and Graph credentials locally.
Follow database-schema.md for explicit migrations; keep INITIALIZE_SCHEMA=false. Existing schema adoption requires a successful comparison and reviewed backup.
Run scripts/start-acceptance-windows.bat for frontend port 3000 and backend port 8001. It sets DEMO_MODE=true and SCHEDULER_ENABLED=false and checks for occupied ports. Microsoft email OTP remains real with DEMO_AUTH=false; customer sends remain simulated.
Manual backend: `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001`. Manual frontend: `npm run dev -- --port 3000` from frontend. Optional single scheduler worker: `python -m app.worker`; do not enable both embedded scheduler and standalone worker.
For an isolated offline demo, explicitly configure DEMO_AUTH=true, APP_ENV=development and DEMO_MODE=true. Use development OTP 123456; `python -m app.seed` adds labeled synthetic fixtures. Do not seed synthetic records into the customer database.
