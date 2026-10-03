import re, html, xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Opportunity, Company, AgentRun
from app.models.platform import ServicePortfolio, DiscoverySource

DEFAULT_SERVICES=[
 ('Microsoft Data & BI','Power BI, Microsoft Fabric, reporting and analytics',['power bi','microsoft fabric','business intelligence','reporting','analytics']),
 ('Data Engineering & Modernization','Databricks, lakehouse, ETL and data platform modernization',['databricks','lakehouse','data engineering','etl','data platform','sql server migration']),
 ('AI Applications & Automation','AI applications, agents and workflow automation',['artificial intelligence','generative ai','ai agent','automation','workflow automation']),
 ('Business Applications','Dynamics 365, Power Platform and custom applications',['dynamics 365','power platform','power automate','application development','software development']),
]

def seed_defaults(db:Session):
    if db.query(ServicePortfolio).count()==0:
        for n,d,k in DEFAULT_SERVICES: db.add(ServicePortfolio(name=n,description=d,keywords=k,target_buyers=['CIO','CTO','Head of Data','Procurement']))
    if db.query(DiscoverySource).count()==0:
        db.add(DiscoverySource(name='Global Web Search',source_type='WEB_SEARCH',base_url='https://google.serper.dev/search',countries=['Global']))
    db.commit()

def queries(db:Session):
    seed_defaults(db); qs=[]
    for p in db.query(ServicePortfolio).filter(ServicePortfolio.active==True).all():
        terms=(p.keywords or [])[:5] or [p.name]
        for term in terms:
            qs.extend([f'"{term}" RFP OR tender OR RFQ',f'"{term}" "implementation partner"',f'"{term}" procurement'])
    # dedupe and cap to protect API quotas
    return list(dict.fromkeys(qs))[:30]

def _serper(q):
    if not settings.serper_api_key: return []
    with httpx.Client(timeout=25) as c:
        r=c.post('https://google.serper.dev/search',headers={'X-API-KEY':settings.serper_api_key,'Content-Type':'application/json'},json={'q':q,'num':10})
        r.raise_for_status(); data=r.json()
    return [{'title':x.get('title',''),'url':x.get('link',''),'description':x.get('snippet',''),'source':'Global Web Search'} for x in data.get('organic',[])]

def _rss(url,name):
    with httpx.Client(timeout=25,follow_redirects=True,headers={'User-Agent':'VTAB-Opportunity-Agent/1.0'}) as c:
        response=c.get(url); response.raise_for_status(); raw=response.text
    root=ET.fromstring(raw); out=[]
    for item in root.findall('.//item')[:50]:
        out.append({'title':item.findtext('title') or '', 'url':item.findtext('link') or '', 'description':re.sub('<[^>]+>',' ',html.unescape(item.findtext('description') or '')), 'source':name})
    if not out:
        ns='{http://www.w3.org/2005/Atom}'
        for item in root.findall(f'.//{ns}entry')[:50]:
            link=item.find(f'{ns}link'); out.append({'title':item.findtext(f'{ns}title') or '', 'url':(link.attrib.get('href','') if link is not None else ''), 'description':item.findtext(f'{ns}summary') or '', 'source':name})
    return out

def _website(url,name):
    with httpx.Client(timeout=25,follow_redirects=True,headers={'User-Agent':'VTAB-Opportunity-Agent/1.0'}) as c:
        response=c.get(url); response.raise_for_status(); text=response.text
    title=re.search(r'<title[^>]*>(.*?)</title>',text,re.I|re.S); clean=re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',text))[:12000]
    return [{'title':html.unescape(title.group(1)).strip() if title else name,'url':url,'description':clean[:1500],'source':name}]

def match(db,text):
    low=text.lower(); matches=[]; evidence=[]
    for p in db.query(ServicePortfolio).filter(ServicePortfolio.active==True).all():
        hits=[k for k in (p.keywords or []) if k.lower() in low]
        if hits: matches.append(p.name); evidence.extend(hits)
    intent_hits=[x for x in ['rfp','tender','rfq','procurement','request for proposal','implementation partner','supplier','framework agreement'] if x in low]
    score=min(100,20+len(set(evidence))*10+len(intent_hits)*12) if matches and intent_hits else min(55,len(set(evidence))*10)
    return score,matches,list(dict.fromkeys(evidence)),intent_hits

def run_discovery(db:Session):
    seed_defaults(db); raw=[]; errors=[]; qlist=queries(db)
    for src in db.query(DiscoverySource).filter(DiscoverySource.active==True).all():
        try:
            if src.source_type=='WEB_SEARCH':
                if not settings.serper_api_key: errors.append({'source':src.name,'message':'SERPER_API_KEY not configured; web-search connector skipped.'}); continue
                for q in qlist: raw.extend([{**x,'query':q} for x in _serper(q)])
            elif src.source_type=='RSS' and src.base_url: raw.extend([{**x,'query':'RSS feed'} for x in _rss(src.base_url,src.name)])
            elif src.source_type=='WEBSITE' and src.base_url: raw.extend([{**x,'query':'Configured website scan'} for x in _website(src.base_url,src.name)])
        except Exception as e: errors.append({'source':src.name,'message':str(e)[:240]})
    created=0; qualified=0; seen=set()
    for x in raw:
        url=(x.get('url') or '').strip()
        if not url or url in seen: continue
        seen.add(url)
        if db.query(Opportunity).filter(Opportunity.source_url==url).first(): continue
        text=f"{x.get('title','')} {x.get('description','')}"; score,services,evidence,intents=match(db,text)
        if score<45: continue
        host=urlparse(url).netloc.replace('www.','') or x.get('source','Unknown')
        company=db.query(Company).filter(Company.website==f'https://{host}').first()
        if not company:
            company=Company(name=host,website=f'https://{host}',country='Unknown',description=f'Discovered from {x.get("source")}'); db.add(company); db.flush()
        o=Opportunity(company_id=company.id,title=(x.get('title') or 'Discovered opportunity')[:500],source_name=x.get('source','Live Discovery'),source_url=url,country='Unknown',published_date=date.today(),closing_date=None,description=(x.get('description') or '')[:6000],qualification_score=score,qualification_status='QUALIFIED' if score>=65 else 'UNDER_REVIEW',business_fit='HIGH' if score>=80 else ('MEDIUM' if score>=65 else 'LOW'),pipeline_status='QUALIFIED' if score>=65 else 'UNDER_REVIEW',matched_services=services,relevance_reason=f"Live source matched VTAB portfolio. Evidence: {', '.join(evidence[:8])}. Buyer intent: {', '.join(intents[:5])}. Discovery query: {x.get('query','')}")
        db.add(o); created+=1; qualified+=int(score>=65)
    db.commit()
    result={'provider':'SERPER' if settings.serper_api_key else 'CONFIGURED_SOURCES','queries_generated':len(qlist),'raw_results':len(raw),'new_opportunities':created,'qualified':qualified,'errors':errors,'demo_data_used':False}
    db.add(AgentRun(agent_name='Global Opportunity Discovery Agent',input_json={'queries':qlist[:10]},output_json=result,status='SUCCESS' if raw or not errors else 'WARNING')); db.commit(); return result
