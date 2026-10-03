"""Read-only SQL Server/schema and Microsoft Graph acceptance. Never sends email."""
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
import httpx
os.environ['DEMO_MODE']='true'
os.environ['SCHEDULER_ENABLED']='false'
from app.core.config import settings
result={'checked_at':datetime.now(timezone.utc).isoformat(),'read_only':True,'customer_email_sent':False}
try:
    from sqlalchemy import inspect,text
    from app.models.db import Base,engine
    from app.models import entities,platform,sales_followup,intelligence
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
        inspector=inspect(connection)
        existing=set(inspector.get_table_names())
        missing={}
        for name,table in Base.metadata.tables.items():
            if name not in existing:missing[name]=['TABLE MISSING'];continue
            columns={c['name'] for c in inspector.get_columns(name)}
            absent=[c.name for c in table.columns if c.name not in columns]
            if absent:missing[name]=absent
        result['database']={'connection':'PASS','schema':'PASS' if not missing else 'FAIL','missing':missing}
except Exception as exc:
    result['database']={'connection':'FAIL','error_type':type(exc).__name__,'action':'Check SQL Server availability, DATABASE_URL and Microsoft ODBC Driver 18. No database changes were made.'}
required=[settings.microsoft_tenant_id,settings.microsoft_client_id,settings.microsoft_client_secret,settings.microsoft_sender_email]
if not all(required):result['microsoft']={'status':'NOT_CONFIGURED'}
else:
    try:
        with httpx.Client(timeout=20) as client:
            response=client.post(f'https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token',data={'client_id':settings.microsoft_client_id,'client_secret':settings.microsoft_client_secret,'scope':'https://graph.microsoft.com/.default','grant_type':'client_credentials'})
            if response.status_code!=200:
                data=response.json() if 'json' in response.headers.get('content-type','') else {}
                result['microsoft']={'authentication':'FAIL','http_status':response.status_code,'error_code':data.get('error','HTTP_ERROR'),'error_codes':data.get('error_codes',[])}
            else:
                mailbox=client.get(f'https://graph.microsoft.com/v1.0/users/{quote(settings.microsoft_sender_email,safe="")}/mailFolders/inbox/messages',headers={'Authorization':'Bearer '+response.json()['access_token']},params={'$top':'1','$select':'id'})
                result['microsoft']={'authentication':'PASS','inbox_read_access':'PASS' if mailbox.status_code==200 else 'FAIL','http_status':mailbox.status_code}
    except Exception as exc:result['microsoft']={'status':'BLOCKED','error_type':type(exc).__name__,'action':'Check network access to Microsoft login and Graph endpoints.'}
output=Path(__file__).resolve().parents[1]/'validation'/'live-validation-result.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
print('Report: '+str(output))
raise SystemExit(0 if result.get('database',{}).get('schema')=='PASS' and result.get('microsoft',{}).get('inbox_read_access')=='PASS' else 1)
