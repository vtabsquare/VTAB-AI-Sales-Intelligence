# Database schema and migration
Existing tables cover companies, opportunities, contacts, outreach drafts, communications, suppressions, agent runs, knowledge documents, inbound responses, follow-ups, portfolios, source configuration, templates, resources, schedules and authentication.
New tables: qualification_assessments (one per opportunity), discovery_occurrences (source history), intelligence_workflows (one persisted workflow per opportunity), knowledge_chunks (document retrieval chunks) and country_targets (editable regional configuration).

Fresh PostgreSQL database: `cd backend && alembic upgrade head`. Frozen migrations 0001 baseline, 0002 intelligence and 0003 country targets are explicit and do not run inside API startup. INITIALIZE_SCHEMA=false is the deployment setting.

Existing SQL Server/PostgreSQL databases: back up first. `python adopt_baseline.py` compares the existing schema against baseline metadata without writing. Only when it reports a match and the backup has been reviewed, run `python adopt_baseline.py --stamp-reviewed-baseline`, then `alembic upgrade head`. A mismatch stops adoption and requires DBA review; do not blindly stamp or recreate customer tables. SQL Server requires its existing Microsoft ODBC driver in addition to pyodbc. The PostgreSQL Docker image is not a SQL Server image.

Schema downgrades are deliberately disabled because dropping these records destroys evidence. Restore a reviewed backup instead. pgvector/semantic embeddings are not installed in Phase 1; knowledge retrieval reports LEXICAL explicitly.
