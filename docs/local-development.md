# Local demo
Prerequisites: Git, Python 3.12 (for the configuration helper), Docker Engine/Desktop with Compose v2.
From the repository root:
```
python scripts/configure-demo.py
docker compose up --build -d
docker compose ps
```
Open http://localhost:3000/login. Use LOGIN_EMAIL and LOGIN_PASSWORD from the generated root .env. Enter demo OTP 123456. Never share that .env.
Discovery Engine → Run Discovery Now → Opportunities → select an opportunity → Run / resume to approval → inspect scoring and knowledge → Approval Queue → edit/approve/reject. Demo discovery returns three labeled synthetic requirements, including Example Ireland Analytics Ltd's Power BI/Fabric modernization example. It is idempotent. No customer email is sent in demo mode.

Knowledge Base lets you add evidence, inspect it, approve/withdraw it and search approved chunks. Discovery Engine lets you configure country/region priority, keywords, language and IANA timezone; these alter generated queries for live web search. Country query targeting is not proof of vendor eligibility, nor a strict geographical filter on RSS/web pages.

Native development: create a backend virtual environment, install backend/requirements.txt, configure DATABASE_URL to a fresh SQLite/PostgreSQL DB plus LOGIN_EMAIL, LOGIN_PASSWORD and JWT_SECRET. Set DEMO_MODE=true, DEMO_AUTH=true, APP_ENV=development, SCHEDULER_ENABLED=false and INITIALIZE_SCHEMA=false. Run `alembic upgrade head`, `python -m app.seed`, and `uvicorn app.main:app --host 127.0.0.1 --port 8001` from backend. In frontend run `npm ci` and `npm run dev`. A separate terminal may run `python -m app.worker` from backend; use only one scheduler worker.

Stop containers: `docker compose down` preserves PostgreSQL data. Do not use `down -v` on data you want to retain.
