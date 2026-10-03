# Architecture

Discovery connectors normalize public search/RSS/web sources. Structured qualification uses a provider boundary and versioned prompt; deterministic demo rules keep local demos independent of external providers. Approved knowledge is chunked and retrieved by text overlap. The supervisor calls only allowlisted tools, checkpoints each result, and ends at human approval. It cannot send email.

A separate single-replica scheduler executes persisted DISCOVERY, INBOX_SYNC and REPROCESS jobs. Redis is provisioned for a future queue, but no Celery queue is falsely claimed active. Human send controls and Microsoft Graph integrations from the existing application remain separate.

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
