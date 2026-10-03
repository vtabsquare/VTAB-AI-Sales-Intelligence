# Phase 1 API additions
All endpoints require the existing bearer session except auth and health. Browser requests use /backend-api; FastAPI routes use /api.

| Method | Path | Purpose |
|---|---|---|
| GET / POST | /api/knowledge | List/create unapproved evidence |
| POST | /api/knowledge/upload | UTF-8 .txt/.md, multipart file/title, 200 KB limit |
| PATCH | /api/knowledge/{id}/approval | Human approve/withdraw with {approved: boolean} |
| POST | /api/knowledge/{id}/reindex | Rebuild local retrieval chunks |
| GET | /api/knowledge/search?q=... | Approved text retrieval |
| GET | /api/intelligence/opportunities/{id} | Scores, company, knowledge, workflow |
| POST | /api/intelligence/opportunities/{id}/run | Run/resume tools to approval |
| POST | /api/demo/seed | Idempotent demo seed; rejected in live mode |
| GET / POST | /api/admin/countries | List/upsert country targets |

Existing discovery, qualification, research, contacts, draft, approval, dashboard and agent-run endpoints remain. Detailed request/response contracts are available at /docs and /openapi.json when the API is running. This documentation does not claim that all optional Phase 4 modules exist.

Manual opportunity management is also available: POST /api/opportunities creates an operator-supplied source record; PATCH /api/opportunities/{id} edits a pre-outreach requirement and resets qualification; DELETE /api/opportunities/{id} archives it as CLOSED while retaining history. Archiving rejects pending drafts and refuses to interrupt approved/sending outreach.
