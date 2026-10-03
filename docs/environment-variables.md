# Environment variables
| Variable | Purpose |
|---|---|
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
| QUALIFICATION_THRESHOLD / DAILY_OUTREACH_LIMIT | Existing qualification and outbound limits |
| REDIS_URL | Reserved queue connection; current scheduler uses database state |

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
