from datetime import datetime,timedelta
from unittest.mock import patch
import httpx
from app.core.config import settings
from app.models.db import SessionLocal
from app.models.platform import ScheduledWorkflow, WorkflowRunHistory
from app.models.sales_followup import InboundResponse, FollowUpTask
from app.models.entities import Contact,Opportunity
from app.services.engine import discover
from app.services.response_intelligence import classify_message
from app.services.workflow_scheduler import next_run
from app.api import auth_routes as auth

class GraphClient:
    """No external network; exercise exact token/send/delta request contracts."""
    calls=[]
    def __init__(self,*a,**kw):pass
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def post(self,url,**kwargs):
        self.calls.append(('POST',url,kwargs))
        if url.endswith('/token'):return httpx.Response(200,json={'access_token':'mock-access-token'},request=httpx.Request('POST',url))
        return httpx.Response(202,request=httpx.Request('POST',url))
    def get(self,url,**kwargs):
        self.calls.append(('GET',url,kwargs))
        if url.endswith('page2'):
            value={'value':[], '@odata.deltaLink':'https://graph.microsoft.com/delta'}
        elif 'messages/delta' in url or url.endswith('/delta'):
            value={'value':[{'id':'graph-qa-1','internetMessageId':'<qa>','subject':'Re: QA Outreach','from':{'emailAddress':{'address':'reply@example.com','name':'Buyer'}},'receivedDateTime':'2026-10-02T10:00:00Z','body':{'content':'<p>We are interested. Please arrange a meeting.</p>'}}], '@odata.nextLink':'https://graph.microsoft.com/page2'}
        else:value={'value':[]}
        return httpx.Response(200,json=value,request=httpx.Request('GET',url))

def graph_config():return patch.multiple(settings,microsoft_tenant_id='qa-tenant',microsoft_client_id='qa-client',microsoft_client_secret='mock-only',microsoft_sender_email='sales@qa.example')

def test_graph_otp_request_contract(client):
    GraphClient.calls=[]
    with graph_config(),patch('httpx.Client',GraphClient):auth.send_otp('123456')
    assert len(GraphClient.calls)==2
    body=GraphClient.calls[1][2]['json'];assert body['message']['toRecipients'][0]['emailAddress']['address']=='qa@example.com'
    assert body['saveToSentItems'] is True

def test_graph_sync_response_followup_pipeline(authorized):
    c=authorized
    with SessionLocal() as db:oid=discover(db)[0].id
    c.post(f'/api/opportunities/{oid}/qualify')
    did=c.post(f'/api/opportunities/{oid}/generate-outreach').json()['id']
    c.patch(f'/api/outreach/{did}',json={'subject':'QA Outreach'})
    c.patch(f'/api/outreach/{did}/recipient',json={'email':'reply@example.com'})
    GraphClient.calls=[]
    with graph_config(),patch('httpx.Client',GraphClient):
        assert c.post('/api/integrations/microsoft/test').json()['connected'] is True
        assert c.post('/api/responses/sync').json()['processed']==1
        assert c.post('/api/responses/sync').json()['processed']==0
    assert all(not url.endswith('sendMail') for _,url,_ in GraphClient.calls)
    reply=c.get('/api/responses').json()[0];assert reply['classification']=='INTERESTED' and reply['matched']
    assert c.get(f'/api/opportunities/{oid}').json()['pipeline_status']=='RESPONDED'
    task=c.get('/api/follow-ups').json()[0];assert task['human_approved'] is False
    assert c.post(f"/api/follow-ups/{task['id']}/prepare-outreach").status_code==409
    assert c.post(f"/api/follow-ups/{task['id']}/approve").status_code==200
    result=c.post(f"/api/follow-ups/{task['id']}/prepare-outreach");assert result.status_code==200 and result.json()['status']=='WAITING_APPROVAL'
    assert c.post(f"/api/follow-ups/{task['id']}/prepare-outreach").status_code==409
    assert c.post('/api/responses/reprocess').status_code==200

def test_classification_negative_auto_procurement():
    assert classify_message('x@example.com','Reply','Not interested')['classification']=='NOT_INTERESTED'
    assert classify_message('noreply@example.com','RFP tender','notice')['classification']=='PROCUREMENT_UPDATE'
    assert classify_message('noreply@example.com','notification','flow(s) have failed')['classification']=='AUTOMATED_NOTIFICATION'
    assert classify_message('postmaster@example.com','undeliverable','bounce')['classification']=='BOUNCE_NDR'
    assert classify_message('x@example.com','Reply','More information please')['classification']=='NEEDS_INFO'
    assert classify_message('x@example.com','Reply','Next month please')['classification']=='FOLLOW_UP_LATER'

def test_schedulers_success_failure_and_history(authorized):
    c=authorized
    payload={'name':'Reprocess QA','action_type':'REPROCESS','interval_minutes':60,'enabled':False}
    r=c.post('/api/platform/schedules',json=payload);assert r.status_code==200
    sid=r.json()['id'];assert c.post(f'/api/platform/schedules/{sid}/run').json()['status']=='SUCCESS'
    assert len(c.get('/api/platform/schedule-history/all').json())==1
    assert len(c.get(f'/api/platform/schedule-history/{sid}').json())==1
    assert c.delete(f'/api/platform/schedules/{sid}').status_code==409
    with patch('app.services.workflow_scheduler.execute',side_effect=RuntimeError('QA failure')):
        assert c.post(f'/api/platform/schedules/{sid}/run').json()['status']=='FAILED'
    changed=c.patch(f'/api/platform/schedules/{sid}',json={'enabled':False}).json();assert changed['action_type']=='REPROCESS'
    w=ScheduledWorkflow(interval_minutes=10080,timezone='UTC',run_at_time='09:00')
    now=datetime(2026,10,2,10,0)
    assert next_run(w,now)==datetime(2026,10,9,9,0)

def test_null_services_serialization(authorized):
    with SessionLocal() as db:
        o=discover(db)[0];oid=o.id;o.matched_services=None;db.commit()
    assert authorized.get(f'/api/opportunities/{oid}').status_code==200
    assert authorized.get(f'/api/opportunities/{oid}').json()['matched_services']==[]

def test_explicit_confirmation_required(authorized):
    c=authorized
    with SessionLocal() as db:oid=discover(db)[0].id
    c.post(f'/api/opportunities/{oid}/qualify')
    did=c.post(f'/api/opportunities/{oid}/generate-outreach').json()['id'];c.post(f'/api/outreach/{did}/approve')
    c.patch(f'/api/outreach/{did}/recipient',json={'email':'confirmed@example.com'});c.post(f'/api/outreach/{did}/test-verify-recipient')
    assert c.post(f'/api/outreach/{did}/send').status_code==409
    assert c.get(f'/api/outreach/{did}').json()['status']=='APPROVED'
