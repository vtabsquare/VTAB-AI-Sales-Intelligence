> Current cloud target: native Render services + Neon PostgreSQL, as authorized on 2026-10-03. See [cloud deployment](RENDER-DEPLOYMENT.md). SQL Server instructions below are for legacy local setups. No Docker is required.

# Native deployment
Windows-native Python/FastAPI, Next.js/Node.js and the existing SQL Server are the supported deployment path. Docker and PostgreSQL are not required. Preserve private configuration and back up the database before reviewed additive migrations.
GitHub Actions runs backend checks/tests and frontend type checks/production build. The container job has been removed.
Use scripts/setup-windows.bat and scripts/start-acceptance-windows.bat for local acceptance. For production, run API and frontend under supervised services with TLS, protected secrets, database backups and approved identity configuration. Use at most one scheduler instance. Live mailbox and SQL Server acceptance require the actual configured environment.
