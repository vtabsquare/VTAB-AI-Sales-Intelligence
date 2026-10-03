from datetime import datetime,timedelta
from unittest.mock import patch
import pytest
from app.api import auth_routes as auth
from app.models.db import SessionLocal
from app.models.platform import AuthOtpChallenge

LISTS=['opportunities','outreach/approval-queue','outreach/send-center','agent-runs','responses','follow-ups','platform/templates','platform/services','platform/sources','platform/resources','platform/assets','platform/schedules','platform/schedule-history/all']
def test_public_and_protected(client):
    assert client.get('/api/health').status_code==200
    assert client.get('/docs').status_code==200
    assert client.get('/openapi.json').status_code==200
    for p in LISTS+['dashboard','pipeline','auth/session']: assert client.get('/api/'+p).status_code==401
    client.headers['Authorization']='Bearer fake'
    assert client.get('/api/dashboard').status_code==401

def test_auth_password_otp_session_logout(client):
    c=client
    assert c.post('/api/auth/login',json={'email':'qa@example.com','password':'wrong'}).status_code==401
    codes=[]
    with patch.object(auth,'send_otp',side_effect=codes.append):
        assert c.post('/api/auth/login',json={'email':'QA@example.com','password':'test-only-password'}).status_code==200
        assert c.post('/api/auth/login',json={'email':'qa@example.com','password':'test-only-password'}).status_code==429
    with SessionLocal() as db:
        challenge=db.query(AuthOtpChallenge).one();assert challenge.otp_hash!=codes[0]
    assert c.post('/api/auth/verify',json={'email':'qa@example.com','code':'bad'}).status_code==400
    wrong='000000' if codes[0]!='000000' else '111111'
    assert c.post('/api/auth/verify',json={'email':'qa@example.com','code':wrong}).status_code==401
    good=c.post('/api/auth/verify',json={'email':'qa@example.com','code':codes[0]});assert good.status_code==200
    assert c.post('/api/auth/verify',json={'email':'qa@example.com','code':codes[0]}).status_code==400
    token=good.json()['token'];c.headers['Authorization']='Bearer '+token
    assert c.get('/api/auth/session').json()['authenticated'] is True
    assert c.post('/api/auth/logout').status_code==200
    assert c.get('/api/dashboard').status_code==401
    assert auth.verify_token(token) is False

def test_expired_attempt_limit_delivery_failure(client):
    c=client;auth.create_otp_challenge('qa@example.com','123456')
    with SessionLocal() as db: x=db.query(AuthOtpChallenge).one();x.expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    assert c.post('/api/auth/verify',json={'email':'qa@example.com','code':'123456'}).status_code==400
    auth.create_otp_challenge('qa@example.com','123456')
    for i in range(5):assert c.post('/api/auth/verify',json={'email':'qa@example.com','code':'000000'}).status_code==401
    assert c.post('/api/auth/verify',json={'email':'qa@example.com','code':'123456'}).status_code==429

def test_provider_failure_invalidates_challenge(client):
    with patch.object(auth,'send_otp',side_effect=RuntimeError('provider unavailable')):
        assert client.post('/api/auth/login',json={'email':'qa@example.com','password':'test-only-password'}).status_code==502
    with SessionLocal() as db:assert db.query(AuthOtpChallenge).one().used

def test_all_collections_and_missing_records(authorized):
    for p in LISTS:
        r=authorized.get('/api/'+p);assert r.status_code==200,(p,r.text);assert isinstance(r.json(),list)
    for p in ['dashboard','pipeline','platform/overview','platform/discovery/queries','integrations/microsoft/status','outreach/provider-status']:
        r=authorized.get('/api/'+p);assert r.status_code==200,(p,r.text);assert isinstance(r.json(),dict)
    for p in ['opportunities/missing','outreach/missing','platform/unknown']:
        assert authorized.get('/api/'+p).status_code==404

def test_platform_validation_patch_duplicate(authorized):
    c=authorized
    assert c.post('/api/platform/templates',json={}).status_code==422
    t=c.post('/api/platform/templates',json={'name':'QA','subject':'Subject','body_html':'<p>Body</p>'});assert t.status_code==200
    changed=c.patch('/api/platform/templates/'+t.json()['id'],json={'name':'Renamed'}).json();assert changed['subject']=='Subject'
    svc={'name':'Unique','keywords':['test']}
    assert c.post('/api/platform/services',json=svc).status_code==200
    assert c.post('/api/platform/services',json=svc).status_code==409
    assert c.post('/api/platform/schedules',json={'name':'Bad','timezone':'wrong'}).status_code==422
    assert c.post('/api/platform/schedules',json={'name':'Bad','interval_minutes':-1}).status_code==422
    assert c.post('/api/platform/resources',json={'title':'Bad','url':'javascript:alert(1)'}).status_code==422
    assert c.delete('/api/platform/templates/'+t.json()['id']).status_code==200
