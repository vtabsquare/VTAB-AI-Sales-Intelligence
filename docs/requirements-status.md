# Master prompt implementation boundary
The execution instruction requests Phase 1 first. This checkpoint extends the existing application and does not claim that every future module in all 80 sections is finished.

| Requirement | Current implementation |
|---|---|
| Local end-to-end demo | Labeled seed discovery, password + development OTP, seven-dimensional qualification, research, approved knowledge, contact review, draft, approval queue |
| Container structure | PostgreSQL, Redis, migration/seed job, API, worker, Next.js, persistent database, health checks |
| Database migrations | Three frozen Alembic revisions and strict existing-baseline adoption check |
| AI abstraction | local deterministic mode; schema-validated OpenAI/Azure endpoint for live qualification/outreach |
| Agent orchestration | Allowlisted supervisor tools, persisted outputs/checkpoints, failed-step retry, human approval termination |
| Knowledge | UTF-8 text/Markdown upload/paste, approval/withdrawal, chunk indexing/reindex API, approval-filtered text retrieval |
| Source evidence | RSS, websites and optional Serper connector; actual source URL; unknown publication dates remain unknown |
| Regional targeting | Editable country/region, priority, enabled flag, keywords, language/timezone metadata; country and keywords enter web-search queries |
| Duplicates | Normalized URL, same normalized title/source host, database uniqueness and discovery occurrences; semantic deduplication deferred |
| Opportunity management | Create/read/edit/archive APIs; searchable filtered/paginated UI; CSV export; source/score/workflow detail |
| Email controls | Existing approval, recipient evidence/verification, suppression, final confirmation and demo-send simulation retained |
| Microsoft inbox | Existing integration retained and mocked regression tests passed; live tenant acceptance still pending |
| Production identity | Entra SSO, multi-user RBAC and passkey enrolment deferred |
| Vector search | pgvector/embeddings deferred; retrieval is explicitly LEXICAL |
| Advanced automation | Single scheduler worker; distributed queues/leases, no-reply business-day cadence and full state-history CRM deferred |
| Analytics / Phase 4 | Existing dashboard/pipeline/logs retained; advanced reports, proposals, calendar and LinkedIn discovery deferred |
| Production release | Docker execution, PostgreSQL/SQL Server tenant acceptance, live AI/Graph and security acceptance require their configured environments |
