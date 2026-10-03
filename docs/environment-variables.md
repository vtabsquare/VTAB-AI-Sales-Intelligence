# Environment variables
| Variable | Purpose |
|---|---|
| DATABASE_URL | SQLAlchemy PostgreSQL, SQLite test or existing SQL Server connection |
| POSTGRES_PASSWORD | Generated local Docker database password |
| LOGIN_EMAIL / LOGIN_PASSWORD | Single-operator development sign-in |
| JWT_SECRET | Private session signing key |
| DEMO_MODE | Simulates outbound delivery and uses labeled synthetic discovery |
| DEMO_AUTH / DEMO_OTP | Explicit development-only local OTP; default disabled / 123456 |
| INITIALIZE_SCHEMA | Legacy/test convenience; false for migrations/deployment |
| SCHEDULER_ENABLED | Embedded scheduler; false when using the separate worker |
| AI_PROVIDER | local, openai or azure; local is a deterministic fallback, not semantic AI |
| AI_ENDPOINT | Chat completions endpoint; Azure users supply their deployment/API-version URL |
| OPENAI_API_KEY / OPENAI_MODEL | Provider credential and compatible structured-output model |
| SERPER_API_KEY | Optional live web search credential |
| MICROSOFT_TENANT_ID / MICROSOFT_CLIENT_ID / MICROSOFT_CLIENT_SECRET / MICROSOFT_SENDER_EMAIL | Existing Microsoft Graph service identity |
| API_BASE_URL | Server-only frontend backend URL; Docker uses http://backend:8001 |
| QUALIFICATION_THRESHOLD / DAILY_OUTREACH_LIMIT | Existing qualification and outbound limits |
| REDIS_URL | Reserved queue connection; current scheduler uses database state |

Compose intentionally fixes local demo mode and local AI. Switch to a separately reviewed production deployment configuration for live integrations. Never put credentials into NEXT_PUBLIC variables.
