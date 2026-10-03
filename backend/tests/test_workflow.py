from unittest.mock import patch
from app.models.db import SessionLocal
from app.models.entities import Opportunity, Contact, Suppression
from app.services.engine import discover
from app.models.platform import DiscoverySource

def test_end_to_end_demo(authorized):
    c=authorized
    with SessionLocal() as db: oid=discover(db)[0].id
    q=c.post(f'/api/opportunities/{oid}/qualify'); assert q.status_code==200 and q.json()['qualification_score']>=65
    assert c.post(f'/api/opportunities/{oid}/research').status_code==200
    assert c.post(f'/api/opportunities/{oid}/find-contact').json()['email'] is None
    d=c.post(f'/api/opportunities/{oid}/generate-outreach').json();did=d['id']; assert d['status']=='WAITING_APPROVAL'
    c.post(f'/api/opportunities/{oid}/qualify')
    assert c.post(f'/api/opportunities/{oid}/generate-outreach').json()['id']==did
    assert c.post(f'/api/outreach/{did}/send').status_code==409
    assert c.patch(f'/api/outreach/{did}',json={'subject':'Reviewed subject','body_text':'Reviewed body'}).status_code==200
    assert c.post(f'/api/outreach/{did}/approve').json()['status']=='APPROVED'
    c.post(f'/api/opportunities/{oid}/qualify')
    assert c.post(f'/api/opportunities/{oid}/generate-outreach').json()['id']==did
    assert c.post(f'/api/outreach/{did}/send').status_code==409
    assert c.patch(f'/api/outreach/{did}/recipient',json={'email':'human@example.com','name':'QA Recipient'}).status_code==200
    assert c.post(f'/api/outreach/{did}/test-verify-recipient').status_code==200
    assert c.post(f'/api/outreach/{did}/send',json={'confirmed':True}).json()['status']=='SIMULATED_SENT'
    assert c.post(f'/api/outreach/{did}/send',json={'confirmed':True}).status_code==409
    assert c.post('/api/responses/simulate',json={'opportunity_id':oid,'body':'We are interested. Please arrange a meeting.'}).json()['response_type']=='MEETING_REQUEST'
    assert c.get('/api/pipeline').json()['opportunities_total']==3
    assert c.get('/api/agent-runs').json()

def test_live_discovery_extraction_duplicate_and_match(authorized,monkeypatch):
    monkeypatch.setattr("app.core.config.settings.demo_mode",False)
    c=authorized
    c.get('/api/platform/services')
    with SessionLocal() as db: db.query(DiscoverySource).delete();db.add(DiscoverySource(name='QA RSS',source_type='RSS',base_url='https://example.com/feed'));db.commit()
    items=[{'title':'Power BI Fabric tender RFP','url':'https://example.com/tender','description':'Power BI analytics reporting implementation partner procurement','source':'QA RSS'}]*2
    with patch('app.services.global_discovery._rss',return_value=items):
        first=c.post('/api/platform/discovery/run').json();second=c.post('/api/platform/discovery/run').json()
    assert first['new_opportunities']==1 and first['qualified']==0
    assert second['new_opportunities']==0

def test_send_suppression(authorized):
    c=authorized
    with SessionLocal() as db: oid=discover(db)[0].id
    c.post(f'/api/opportunities/{oid}/qualify')
    d=c.post(f'/api/opportunities/{oid}/generate-outreach').json()['id']
    c.post(f'/api/outreach/{d}/approve')
    c.patch(f'/api/outreach/{d}/recipient',json={'email':'suppressed@example.com'})
    c.post(f'/api/outreach/{d}/test-verify-recipient')
    with SessionLocal() as db:db.add(Suppression(email='suppressed@example.com',reason='QA'));db.commit()
    assert c.post(f'/api/outreach/{d}/send',json={'confirmed':True}).status_code==409
