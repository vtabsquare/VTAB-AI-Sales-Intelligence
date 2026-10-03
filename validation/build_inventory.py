"""Static contract inventory: records source call sites and runtime OpenAPI contracts."""
import json,re,sys,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
runpy.run_path(str(ROOT/'backend/tests/conftest.py'))
from app.main import app
from app.models.db import Base
schema=app.openapi();(ROOT/'validation/openapi.json').write_text(json.dumps(schema,indent=2))
endpoints=[]
for path,methods in schema['paths'].items():
 for method,operation in methods.items():
  if method not in {'get','post','patch','put','delete'}:continue
  endpoints.append({'method':method.upper(),'path':path,'operation':operation.get('operationId'),'request_body':operation.get('requestBody'),'responses':operation.get('responses')})
(ROOT/'validation/backend-endpoints.json').write_text(json.dumps(endpoints,indent=2))
models={name:[{'name':c.name,'type':str(c.type),'nullable':c.nullable,'primary_key':c.primary_key} for c in table.columns] for name,table in Base.metadata.tables.items()}
(ROOT/'validation/database-models.json').write_text(json.dumps(models,indent=2))
calls=json.loads((ROOT/'validation/frontend-api-inventory.json').read_text())
text=['# API contract inventory','',f'{len(calls)} frontend call sites; {len(endpoints)} backend operations; {len(models)} database tables.','', 'Browser URLs use `/backend-api`; the Next route handler maps to `/api` and forwards only the canonical HttpOnly session as a bearer header. Protected APIs return 401 on absent, revoked, malformed or expired sessions. Public endpoints: health, login and OTP verification. Documentation is public.', '', '| Frontend file:line | Method | Path/expression |', '|---|---|---|']
for row in calls:text.append(f"| {row['file']}:{row['line']} | {row['method']} | `{row['url'].replace('|',' / ')}` |")
text+=['','Dynamic opportunity actions resolve to qualify, research, find-contact and generate-outreach; approval actions resolve to PATCH draft / POST approve or reject; response actions resolve to approve, dismiss and prepare-outreach. Method values held in a RequestInit variable are resolved by those handlers, rather than inferred as GET by the static call-site scanner.','', '## Backend operations','', '| Method | Backend path |','|---|---|']
for row in endpoints:text.append(f"| {row['method']} | `{row['path']}` |")
text+=['', '## Contract decisions','', '- Collections return JSON arrays of records, including empty arrays. An HTTP error detail object is never a collection. The shared client checks HTTP status, JSON shape, record IDs, required display strings and string-array fields before page state changes.', '- Discovery query result is `{queries: string[]}`. Discovery run returns counters plus connector errors. Skipped/unconfigured connectors are surfaced rather than reported as successful opportunities.', '- Dashboard and pipeline return objects; pipeline stage/classification values are numeric maps.', '- Nullable service matches are normalized at the backend serializer. Published closing date is returned explicitly; pages no longer look for nonexistent deadline/due_date fields.', '- OTP verification creates a database-backed session; the proxy writes a single HttpOnly cookie with SameSite=Lax, eight-hour expiry and Secure over HTTPS. Logout revokes its token fingerprint.', '- Generic platform PATCH uses only provided fields. Validation rejects blank names, invalid URLs/timezones/action types, invalid intervals and duplicate service names.', '- Send requires APPROVED state, evidence-reviewed recipient, suppression checks and `{confirmed:true}`. TEST_VERIFIED is accepted only in demo mode. Atomic claim prevents duplicate sends. Provider failures leave SEND_FAILED for human investigation.', '- Follow-up approval alone sends nothing. Preparing an approved recommendation creates a WAITING_APPROVAL outreach draft, which must pass the same approval/send gates.', '', 'Exact request/response schemas, parameters and response codes are in `validation/openapi.json`. API authentication is implemented in middleware; it is not represented as a Swagger OAuth login scheme. Live schema comparison is still required using `backend/schema_check.py`.']
(ROOT/'API-CONTRACT-INVENTORY.md').write_text('\n'.join(text)+'\n')
print('Inventory:',len(endpoints),'operations,',len(models),'tables')
