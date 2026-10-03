# Deployment
The Compose stack includes PostgreSQL health checks and persistent volume, Redis, a one-shot migration/demo seed job, API health check, one scheduler worker and Next.js frontend. API and frontend listen on loopback for local use. Migrations must succeed before app startup. Dockerfiles exclude local secrets/dependencies.

GitHub Actions validates backend syntax, pytest, TypeScript and frontend production build. The container job builds the stack and checks frontend/backend startup. It performs local fixture acceptance only; no production deployment or live outbound send is configured.

For Azure Container Apps/App Service: build backend/frontend images, configure PostgreSQL and secrets externally, run migrations as a release job, disable DEMO_AUTH, configure TLS and appropriate origins, and isolate one scheduler worker. Production release needs tenant Graph consent, Entra identity work, database/backup validation and security acceptance. Existing SQL Server installations should follow database-schema.md rather than point the fresh Compose PostgreSQL configuration at their live DB.
