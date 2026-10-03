"""External test harness only. Never imported by the production application."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ.update(DATABASE_URL='sqlite:///'+os.environ['VTAB_VALIDATION_DB'],INITIALIZE_SCHEMA='true',SCHEDULER_ENABLED='false',DEMO_MODE='true',APP_ENV='test',LOGIN_EMAIL='qa@example.com',LOGIN_PASSWORD='test-only-password',JWT_SECRET='test-only-private-signing-key',MICROSOFT_TENANT_ID='qa-tenant',MICROSOFT_CLIENT_ID='qa-client',MICROSOFT_CLIENT_SECRET='mock-only',MICROSOFT_SENDER_EMAIL='sales@qa.example',SERPER_API_KEY='',OPENAI_API_KEY='')
from app.main import app
from app.api import auth_routes
# Deterministic OTP delivery replaces Graph only inside this test server process.
auth_routes.send_otp=lambda code:None
auth_routes.secrets.randbelow=lambda n:123456
from app.services import global_discovery
# Only this isolated fixture has synthetic feed content.
global_discovery._rss=lambda url,name:[{'title':'QA Power BI Fabric tender RFP','url':'https://example.com/qa-tender','description':'Power BI analytics reporting procurement implementation partner RFP','source':name}]
from app.services import source_evidence
source_evidence.fetch_evidence=lambda url:{'status':'UNAVAILABLE','source_url':url,'text':'','emails':[]}
import importlib.util
spec=importlib.util.spec_from_file_location('qa_graph_fixture',ROOT/'backend/tests/test_integrations_scheduler.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
import httpx
httpx.Client=module.GraphClient
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8001,log_level='warning')
