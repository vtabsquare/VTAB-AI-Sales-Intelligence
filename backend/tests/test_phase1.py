from datetime import date,timedelta
from unittest.mock import patch
from app.models.db import SessionLocal
from app.models.entities import KnowledgeDocument,OutreachDraft
from app.models.intelligence import QualificationAssessment
from app.core.config import settings
from app.services.engine import discover

def test_demo_supervisor_to_human_approval(authorized):
    c=authorized
    assert c.post('/api/demo/seed').json()['opportunities']==3
    oid=c.get('/api/opportunities').json()[0]['id']
    with patch('httpx.Client',side_effect=AssertionError('Demo must not call a provider')):
        response=c.post(f'/api/intelligence/opportunities/{oid}/run')
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_APPROVAL'
    assert len(response.json()['completed_steps'])==5
    c.post(f'/api/intelligence/opportunities/{oid}/run')
    with SessionLocal() as db:
        assert db.query(OutreachDraft).count()==1
        assert db.get(QualificationAssessment,oid).provider=='DEMO_RULES'
    assert len(c.get('/api/outreach/approval-queue').json())==1

def test_knowledge_approval_and_retrieval(authorized):
    c=authorized
    d=c.post('/api/knowledge',json={'title':'Reviewed capability','content':'Power BI and Microsoft Fabric implementation support.'}).json()
    assert not d['approved']
    assert c.get('/api/knowledge/search?q=Fabric').json()==[]
    assert c.patch(f"/api/knowledge/{d['id']}/approval",json={'approved':True}).status_code==200
    assert c.get('/api/knowledge/search?q=Fabric').json()[0]['document_id']==d['id']
    c.patch(f"/api/knowledge/{d['id']}/approval",json={'approved':False})
    assert c.get('/api/knowledge/search?q=Fabric').json()==[]

def test_upload_limits_and_format(authorized):
    c=authorized
    assert c.post('/api/knowledge/upload',files={'file':('facts.pdf',b'x')},data={'title':'Facts'}).status_code==415
    assert c.post('/api/knowledge/upload',files={'file':('facts.txt',b'x'*200001)},data={'title':'Facts'}).status_code==413
    assert c.post('/api/knowledge/upload',files={'file':('facts.txt',b'Power BI')},data={'title':'Facts'}).status_code==200

def test_hard_rejection_overrides_score(authorized):
    c=authorized
    with SessionLocal() as db:
        o=discover(db)[0];oid=o.id;o.closing_date=date.today()-timedelta(days=1);db.commit()
    q=c.post(f'/api/opportunities/{oid}/qualify').json()
    assert q['qualification_score']==0 and q['qualification_status']=='REJECTED'
    assert c.post(f'/api/opportunities/{oid}/generate-outreach').status_code==409
    r=c.post(f'/api/intelligence/opportunities/{oid}/run').json()
    assert r['status']=='REVIEW_REQUIRED' and r['completed_steps']==['qualify']

def test_unapproved_knowledge_cannot_substantiate_claims(authorized):
    with SessionLocal() as db:
        oid=discover(db)[0].id
        for d in db.query(KnowledgeDocument):d.approved=False
        db.commit()
    assert authorized.post(f'/api/opportunities/{oid}/qualify').json()['qualification_status']=='REJECTED'

def test_resume_failure_without_restarting_qualification(authorized):
    c=authorized
    with SessionLocal() as db:oid=discover(db)[0].id
    with patch('app.services.engine.research',side_effect=RuntimeError('fixture failure')):
        failed=c.post(f'/api/intelligence/opportunities/{oid}/run').json()
    assert failed['status']=='FAILED' and failed['completed_steps']==['qualify']
    with patch('app.services.engine.qualify',side_effect=AssertionError('Completed step must not rerun')):
        resumed=c.post(f'/api/intelligence/opportunities/{oid}/run').json()
    assert resumed['status']=='WAITING_APPROVAL'

def test_live_seed_disabled(authorized,monkeypatch):
    monkeypatch.setattr(settings,'demo_mode',False)
    assert authorized.post('/api/demo/seed').status_code==409

def test_demo_auth_and_production_guard(client,monkeypatch):
    monkeypatch.setattr(settings,'demo_auth',True)
    monkeypatch.setattr(settings,'demo_otp','123456')
    r=client.post('/api/auth/login',json={'email':'qa@example.com','password':'test-only-password'})
    assert r.status_code==200
    assert client.post('/api/auth/verify',json={'email':'qa@example.com','code':'123456'}).status_code==200
    monkeypatch.setattr(settings,'app_env','production')
    from app.api.auth_routes import send_otp
    import pytest
    with pytest.raises(RuntimeError):send_otp('123456')

def test_country_targets_and_query_generation(authorized):
    c=authorized
    body={'name':'Ireland','priority':90,'keywords':['analytics'],'timezone':'Europe/Dublin'}
    assert c.post('/api/admin/countries',json=body).status_code==200
    qs=c.get('/api/platform/discovery/queries').json()['queries']
    assert qs and all('Ireland' in q and 'analytics' in q for q in qs)
    c.post('/api/admin/countries',json={**body,'enabled':False})
    assert c.get('/api/platform/discovery/queries').json()['queries']==[]
    assert c.post('/api/admin/countries',json={**body,'timezone':'bad-zone'}).status_code==422

def test_public_sources_reject_private_network():
    from app.services.public_http import validate_public_url
    import pytest
    for url in ['http://127.0.0.1/private','http://169.254.169.254/latest','http://[::1]/','file:///etc/passwd','https://user:secret@example.com/']:
        with pytest.raises(ValueError):validate_public_url(url)

def test_demo_knowledge_is_excluded_from_live(authorized,monkeypatch):
    with SessionLocal() as db:oid=discover(db)[0].id
    monkeypatch.setattr(settings,'demo_mode',False)
    assert authorized.get('/api/knowledge/search?q=Fabric').json()==[]
    assert authorized.post(f'/api/opportunities/{oid}/qualify').json()['qualification_status']=='REJECTED'

def test_live_structured_qualification_uses_approved_evidence(authorized,monkeypatch):
    from app.agents.qualification import QualificationResult,Scores
    with SessionLocal() as db:
        oid=discover(db)[0].id
        db.add(KnowledgeDocument(title='Reviewed factual capability',category='CAPABILITY',approved=True,content='Power BI and Microsoft Fabric implementation support.'))
        db.commit()
    monkeypatch.setattr(settings,'demo_mode',False);monkeypatch.setattr(settings,'ai_provider','openai')
    result=QualificationResult(dimensions=Scores(technical_match=25,service_match=20,accessibility_score=10,geography_score=8,buyer_access_score=8,freshness_score=10,strategic_value_score=8),matched_services=['Power BI','Invented Certification'],reasons=['Approved BI capability fits the modernization requirement.'],concerns=['Eligibility needs verification.'],hard_rejections=[],confidence=85)
    with patch('app.agents.provider.StructuredProvider.generate',return_value=result) as provider:
        q=authorized.post(f'/api/opportunities/{oid}/qualify').json()
    assert provider.call_count==1
    assert q['matched_services']==['Power BI'] and q['qualification_score']==89
    assert 'approved_knowledge' in provider.call_args.args[1]

def test_requalification_does_not_regress_contacted_pipeline(authorized):
    with SessionLocal() as db:
        o=discover(db)[0];o.pipeline_status='CONTACTED';oid=o.id;db.commit()
    assert authorized.post(f'/api/opportunities/{oid}/qualify').json()['pipeline_status']=='CONTACTED'

def test_opportunity_create_edit_archive_preserves_evidence(authorized):
    body={'title':'Power BI tender','organization':'Verified Buyer Example','source_name':'Reviewed manual evidence','source_url':'https://example.com/manual-tender','description':'Power BI implementation partner required.'}
    created=authorized.post('/api/opportunities',json=body)
    assert created.status_code==200
    oid=created.json()['id']
    assert authorized.post('/api/opportunities',json=body).status_code==409
    edited=authorized.patch(f'/api/opportunities/{oid}',json={'title':'Updated Power BI tender'})
    assert edited.json()['qualification_status']=='PENDING'
    assert authorized.delete(f'/api/opportunities/{oid}').json()['status']=='CLOSED'
    assert authorized.get(f'/api/opportunities/{oid}').json()['source_url']==body['source_url']
