> Current cloud target: native Render services + Neon PostgreSQL, as authorized on 2026-10-03. See [cloud deployment](RENDER-DEPLOYMENT.md). SQL Server instructions below are for legacy local setups. No Docker is required.

# Database schema and migration
Existing tables cover companies, opportunities, contacts, outreach drafts, communications, suppressions, agent runs, knowledge documents, inbound responses, follow-ups, portfolios, source configuration, templates, resources, schedules and authentication.
New tables: qualification_assessments (one per opportunity), discovery_occurrences (source history), intelligence_workflows (one persisted workflow per opportunity), knowledge_chunks (document retrieval chunks) and country_targets (editable regional configuration).



Schema downgrades are deliberately disabled because dropping these records destroys evidence. Restore a reviewed backup instead. pgvector/semantic embeddings are not installed in Phase 1; knowledge retrieval reports LEXICAL explicitly.

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
