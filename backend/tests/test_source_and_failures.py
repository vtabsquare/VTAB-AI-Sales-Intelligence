from unittest.mock import patch
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mssql
from app.models.db import Base,SessionLocal
from app.services.engine import discover
from app.services.global_discovery import _rss
from app.services.source_evidence import fetch_evidence
from app.models.platform import AuthSession
import httpx

class FeedClient:
 def __init__(self,*a,**kw):pass
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def get(self,url):return httpx.Response(200,text='<rss><channel><item><title>Power BI RFP</title><link>https://example.com/rfp</link><description>Analytics tender</description></item></channel></rss>',request=httpx.Request('GET',url))

def test_rss_parser_no_network():
 with patch('httpx.Client',FeedClient): rows=_rss('https://example.com/feed','QA')
 assert rows[0]['title']=='Power BI RFP' and rows[0]['source']=='QA'

def test_source_contact_evidence(authorized):
 with SessionLocal() as db:oid=discover(db)[0].id
 with patch('app.services.source_evidence.fetch_evidence',return_value={'status':'FETCHED','text':'Public procurement contact','emails':['procurement@buyer.example'],'source_url':'https://buyer.example/tender'}):
  c=authorized.post(f'/api/opportunities/{oid}/find-contact').json()
 assert c['email']=='procurement@buyer.example' and c['verification']=='UNVERIFIED'
 assert authorized.post(f'/api/opportunities/{oid}/research').status_code==200

def test_mssql_metadata_ddl_compiles():
 for table in Base.metadata.sorted_tables:
  assert str(CreateTable(table).compile(dialect=mssql.dialect()))

def test_backend_failure_sanitized(authorized):
 with patch('app.api.platform_routes.seed_defaults',side_effect=RuntimeError('private connection details')):
  r=authorized.get('/api/platform/services')
 assert r.status_code==500 and 'private connection details' not in r.text

def test_template_generation_offline(authorized):
 r=authorized.post('/api/platform/templates/generate',json={'prompt':'Concise QA email','tone':'Executive'})
 assert r.status_code==200 and r.json()['configured'] is False and isinstance(r.json()['html'],str)

def test_disallowed_test_verification_in_live_mode(authorized):
 from app.core.config import settings
 from app.api.routes import _is_email_verified
 with patch.object(settings,'demo_mode',False):assert _is_email_verified('TEST_VERIFIED') is False


def test_human_recipient_evidence_gate(authorized):
    with SessionLocal() as db:oid=discover(db)[0].id
    did=authorized.post(f'/api/opportunities/{oid}/generate-outreach').json()['id']
    authorized.patch(f'/api/outreach/{did}/recipient',json={'email':'reviewed@example.com'})
    path=f'/api/outreach/{did}/confirm-recipient-evidence'
    assert authorized.post(path,json={'evidence':'short','confirmed':True}).status_code==422
    assert authorized.post(path,json={'evidence':'Reviewed official procurement notice reference QA','confirmed':False}).status_code==422
    r=authorized.post(path,json={'evidence':'Reviewed official procurement notice reference QA','confirmed':True})
    assert r.status_code==200 and r.json()['status']=='HUMAN_VERIFIED'
    assert authorized.post(f'/api/outreach/{did}/send',json={'confirmed':True}).status_code==409

def test_html_source_extraction_no_network():
    class HtmlClient(FeedClient):
        def get(self,url):return httpx.Response(200,text='<html><body><p>Official procurement contact</p><a href="mailto:procurement@buyer.example">Contact</a><script>hidden content</script></body></html>',request=httpx.Request('GET',url))
    # Local function reference is the original implementation, not the offline autouse patch.
    with patch('httpx.Client',HtmlClient):result=fetch_evidence('https://buyer.example/tender')
    assert result['status']=='FETCHED' and result['emails']==['procurement@buyer.example']
    assert 'hidden content' not in result['text']
