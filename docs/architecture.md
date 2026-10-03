# Architecture
Next.js serves the operational UI and forwards same-origin requests to FastAPI using an HttpOnly session cookie. The API validates a database-backed token fingerprint on every protected request. PostgreSQL is the new Docker default; SQLAlchemy retains SQLite test and SQL Server deployment support.

Discovery connectors normalize public search/RSS/web sources. Structured qualification uses a provider boundary and versioned prompt; deterministic demo rules keep local demos independent of external providers. Approved knowledge is chunked and retrieved by text overlap. The supervisor calls only allowlisted tools, checkpoints each result, and ends at human approval. It cannot send email.

A separate single-replica scheduler executes persisted DISCOVERY, INBOX_SYNC and REPROCESS jobs. Redis is provisioned for a future queue, but no Celery queue is falsely claimed active. Human send controls and Microsoft Graph integrations from the existing application remain separate.
