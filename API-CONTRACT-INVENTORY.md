# API contract inventory

39 frontend call sites; 50 backend operations; 20 database tables.

Browser URLs use `/backend-api`; the Next route handler maps to `/api` and forwards only the canonical HttpOnly session as a bearer header. Protected APIs return 401 on absent, revoked, malformed or expired sessions. Public endpoints: health, login and OTP verification. Documentation is public.

| Frontend file:line | Method | Path/expression |
|---|---|---|
| app/admin/page.tsx:8 | GET | ``${API}/integrations/microsoft/status`` |
| app/admin/page.tsx:10 | POST | ``${API}/integrations/microsoft/test`` |
| app/agents/page.tsx:8 | GET | ``${API}/agent-runs`` |
| app/approval/page.tsx:4 | GET | `'/outreach/approval-queue'` |
| app/approval/page.tsx:4 | PATCH | ``/outreach/${x.id}`` |
| app/approval/page.tsx:4 | POST | ``/outreach/${x.id}/${action}`` |
| app/discovery/page.tsx:7 | GET | ``${API}/platform/sources`` |
| app/discovery/page.tsx:8 | GET | ``${API}/platform/discovery/queries`` |
| app/discovery/page.tsx:19 | POST | ``${API}/platform/discovery/run`` |
| app/discovery/page.tsx:19 | POST | ``${API}/platform/sources`` |
| app/job-monitor/page.tsx:3 | GET | ``${API}/platform/schedule-history/all?limit=300`` |
| app/login/page.tsx:34 | POST | ``${API}/auth/login`` |
| app/login/page.tsx:83 | POST | ``${API}/auth/verify`` |
| app/login/page.tsx:122 | GET | ``${API}/auth/session`` |
| app/opportunities/page.tsx:7 | GET | `'/opportunities'` |
| app/opportunities/page.tsx:7 | POST | ``/opportunities/${selected.id}/${name}`` |
| app/outreach/page.tsx:1353 | GET | ``${API}/outreach/send-center`` |
| app/outreach/page.tsx:1659 | POST | ``${API}/outreach/${item.id}/resolve-recipient`` |
| app/outreach/page.tsx:2675 | PATCH | ``${API}/outreach/${item.id}/recipient`` |
| app/outreach/page.tsx:3272 | POST | ``/outreach/${item.id}/confirm-recipient-evidence`` |
| app/outreach/page.tsx:3289 | POST | ``${API}/outreach/${item.id}/verify-recipient`` |
| app/outreach/page.tsx:3539 | POST | ``${API}/outreach/${item.id}/test-verify-recipient`` |
| app/outreach/page.tsx:3789 | POST | ``${API}/outreach/${item.id}/send`` |
| app/page.tsx:10 | GET | `"/api/dashboard"` |
| app/pipeline/page.tsx:7 | GET | ``${API}/pipeline`` |
| app/portfolio/page.tsx:6 | GET | ``${API}/platform/services`` |
| app/portfolio/page.tsx:6 | POST | ``${API}/platform/services`` |
| app/resources/page.tsx:3 | GET | ``${API}/platform/resources`` |
| app/resources/page.tsx:3 | POST | ``${API}/platform/resources`` |
| app/responses/page.tsx:14 | GET | ``${API}${path}`` |
| app/schedulers/page.tsx:3 | GET | ``${API}/platform/schedules`` |
| app/schedulers/page.tsx:3 | POST | ``${API}/platform/schedules`` |
| app/schedulers/page.tsx:3 | POST | ``${API}/platform/schedules/${id}/run`` |
| app/security/page.tsx:1 | GET | `'/auth/session'` |
| app/security/page.tsx:1 | GET | `'/integrations/microsoft/status'` |
| app/templates/page.tsx:6 | GET | ``${API}/platform/templates`` |
| app/templates/page.tsx:6 | POST | ``${API}/platform/templates`` |
| app/templates/page.tsx:6 | POST | ``${API}/platform/templates/generate`` |
| components/AppSidebar.tsx:151 | POST | `"/backend-api/auth/logout"` |

Dynamic opportunity actions resolve to qualify, research, find-contact and generate-outreach; approval actions resolve to PATCH draft / POST approve or reject; response actions resolve to approve, dismiss and prepare-outreach. Method values held in a RequestInit variable are resolved by those handlers, rather than inferred as GET by the static call-site scanner.

## Backend operations

| Method | Backend path |
|---|---|
| POST | `/api/auth/login` |
| POST | `/api/auth/verify` |
| GET | `/api/auth/session` |
| POST | `/api/auth/logout` |
| GET | `/api/health` |
| POST | `/api/opportunities/discover` |
| GET | `/api/opportunities` |
| GET | `/api/opportunities/{id}` |
| POST | `/api/opportunities/{id}/qualify` |
| POST | `/api/opportunities/{id}/research` |
| POST | `/api/opportunities/{id}/find-contact` |
| POST | `/api/opportunities/{id}/generate-outreach` |
| GET | `/api/outreach/approval-queue` |
| PATCH | `/api/outreach/{id}` |
| GET | `/api/outreach/{id}` |
| POST | `/api/outreach/{id}/approve` |
| POST | `/api/outreach/{id}/reject` |
| GET | `/api/outreach/send-center` |
| GET | `/api/outreach/provider-status` |
| GET | `/api/outreach/{id}/recipient` |
| PATCH | `/api/outreach/{id}/recipient` |
| POST | `/api/outreach/{id}/resolve-recipient` |
| POST | `/api/outreach/{id}/verify-recipient` |
| POST | `/api/outreach/{id}/test-verify-recipient` |
| POST | `/api/outreach/{id}/send` |
| POST | `/api/responses/simulate` |
| GET | `/api/dashboard` |
| GET | `/api/agent-runs` |
| POST | `/api/outreach/{id}/confirm-recipient-evidence` |
| POST | `/api/responses/sync` |
| POST | `/api/responses/reprocess` |
| GET | `/api/responses` |
| GET | `/api/follow-ups` |
| POST | `/api/follow-ups/{task_id}/approve` |
| POST | `/api/follow-ups/{task_id}/dismiss` |
| GET | `/api/pipeline` |
| POST | `/api/follow-ups/{task_id}/prepare-outreach` |
| GET | `/api/integrations/microsoft/status` |
| POST | `/api/integrations/microsoft/test` |
| GET | `/api/platform/overview` |
| GET | `/api/platform/discovery/queries` |
| POST | `/api/platform/discovery/run` |
| GET | `/api/platform/schedule-history/all` |
| GET | `/api/platform/schedule-history/{workflow_id}` |
| POST | `/api/platform/schedules/{id}/run` |
| POST | `/api/platform/templates/generate` |
| GET | `/api/platform/{kind}` |
| POST | `/api/platform/{kind}` |
| PATCH | `/api/platform/{kind}/{id}` |
| DELETE | `/api/platform/{kind}/{id}` |

## Contract decisions

- Collections return JSON arrays of records, including empty arrays. An HTTP error detail object is never a collection. The shared client checks HTTP status, JSON shape, record IDs, required display strings and string-array fields before page state changes.
- Discovery query result is `{queries: string[]}`. Discovery run returns counters plus connector errors. Skipped/unconfigured connectors are surfaced rather than reported as successful opportunities.
- Dashboard and pipeline return objects; pipeline stage/classification values are numeric maps.
- Nullable service matches are normalized at the backend serializer. Published closing date is returned explicitly; pages no longer look for nonexistent deadline/due_date fields.
- OTP verification creates a database-backed session; the proxy writes a single HttpOnly cookie with SameSite=Lax, eight-hour expiry and Secure over HTTPS. Logout revokes its token fingerprint.
- Generic platform PATCH uses only provided fields. Validation rejects blank names, invalid URLs/timezones/action types, invalid intervals and duplicate service names.
- Send requires APPROVED state, evidence-reviewed recipient, suppression checks and `{confirmed:true}`. TEST_VERIFIED is accepted only in demo mode. Atomic claim prevents duplicate sends. Provider failures leave SEND_FAILED for human investigation.
- Follow-up approval alone sends nothing. Preparing an approved recommendation creates a WAITING_APPROVAL outreach draft, which must pass the same approval/send gates.

Exact request/response schemas, parameters and response codes are in `validation/openapi.json`. API authentication is implemented in middleware; it is not represented as a Swagger OAuth login scheme. Live schema comparison is still required using `backend/schema_check.py`.
