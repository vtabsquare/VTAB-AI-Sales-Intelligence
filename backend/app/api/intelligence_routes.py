from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.entities import KnowledgeDocument,Opportunity,Company,OutreachDraft
from app.models.intelligence import QualificationAssessment,IntelligenceWorkflow
from app.core.config import settings
from app.services.knowledge import reindex,retrieve
from app.agents.supervisor import run

r=APIRouter(prefix='/api',tags=['phase-1-intelligence'])

def record(row):
    return None if row is None else {column.name:getattr(row,column.name) for column in row.__table__.columns}


class KnowledgeInput(BaseModel):
    title:str=Field(min_length=1,max_length=255)
    category:str=Field(default='CAPABILITY',max_length=255)
    content:str=Field(min_length=1,max_length=200000)

class KnowledgeApproval(BaseModel):
    approved:bool

@r.get('/knowledge')
def documents(db:Session=Depends(get_db)):
    return [record(d) for d in db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()]

@r.post('/knowledge')
def create_document(payload:KnowledgeInput,db:Session=Depends(get_db)):
    doc=KnowledgeDocument(**payload.model_dump(),approved=False);db.add(doc);db.commit();reindex(db,doc)
    return record(doc)

@r.post('/knowledge/upload')
async def upload(file:UploadFile=File(...),title:str=Form(...),db:Session=Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(('.txt','.md')):
        raise HTTPException(415,'Phase 1 accepts UTF-8 text and Markdown documents.')
    content=await file.read(200001)
    if len(content)>200000: raise HTTPException(413,'Document is too large (200 KB maximum).')
    try: text=content.decode('utf-8')
    except UnicodeDecodeError: raise HTTPException(400,'Document must use UTF-8.')
    if not title.strip() or not text.strip(): raise HTTPException(422,"Document title and content are required.")
    payload=KnowledgeInput(title=title,content=text)
    return create_document(payload,db)

@r.patch('/knowledge/{id}/approval')
def approve_knowledge(id:str,payload:KnowledgeApproval,db:Session=Depends(get_db)):
    doc=db.get(KnowledgeDocument,id)
    if not doc: raise HTTPException(404,'Knowledge document not found.')
    doc.approved=payload.approved;db.commit();return record(doc)

@r.post('/knowledge/{id}/reindex')
def index_document(id:str,db:Session=Depends(get_db)):
    doc=db.get(KnowledgeDocument,id)
    if not doc: raise HTTPException(404,'Knowledge document not found.')
    reindex(db,doc);return {'status':'INDEXED','method':'LEXICAL','document_id':id}

@r.get('/knowledge/search')
def search_knowledge(q:str,db:Session=Depends(get_db)):
    return retrieve(db,q[:2000])

@r.get('/intelligence/opportunities/{id}')
def workspace(id:str,db:Session=Depends(get_db)):
    o=db.get(Opportunity,id)
    if not o: raise HTTPException(404,'Opportunity not found.')
    return {'opportunity':record(o),'company':record(db.get(Company,o.company_id)),'assessment':record(db.get(QualificationAssessment,id)),'workflow':record(db.get(IntelligenceWorkflow,id)),'knowledge':retrieve(db,f'{o.title} {o.description}')}

@r.post('/intelligence/opportunities/{id}/run')
def workflow(id:str,db:Session=Depends(get_db)):
    o=db.get(Opportunity,id)
    if not o: raise HTTPException(404,'Opportunity not found.')
    return record(run(db,o))

@r.post('/demo/seed')
def demo_seed(db:Session=Depends(get_db)):
    if not settings.demo_mode: raise HTTPException(409,'Demo seeding is disabled in live mode.')
    from app.seed import seed_demo
    return {'opportunities':len(seed_demo(db)),'mode':'DEMO'}

class CountryInput(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    priority:int=Field(default=50,ge=0,le=100)
    enabled:bool=True
    keywords:list[str]=Field(default_factory=list,max_length=20)
    language:str=Field(default='en',max_length=40)
    timezone:str=Field(default='UTC',max_length=100)

@r.get('/admin/countries')
def countries(db:Session=Depends(get_db)):
    from app.models.intelligence import CountryTarget
    return [record(c) for c in db.query(CountryTarget).order_by(CountryTarget.priority.desc()).all()]

@r.post('/admin/countries')
def save_country(payload:CountryInput,db:Session=Depends(get_db)):
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    from app.models.intelligence import CountryTarget
    try: ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError: raise HTTPException(422,'Choose a valid IANA time zone.')
    if not payload.name.strip(): raise HTTPException(422,'Country name is required.')
    row=db.get(CountryTarget,payload.name.strip()) or CountryTarget(name=payload.name.strip())
    for key,value in payload.model_dump(exclude={'name'}).items():setattr(row,key,value)
    db.add(row);db.commit();return record(row)

class OpportunityInput(BaseModel):
    title:str=Field(min_length=1,max_length=255)
    organization:str=Field(min_length=1,max_length=255)
    source_name:str=Field(min_length=1,max_length=255)
    source_url:str=Field(min_length=1,max_length=2048)
    country:str=Field(default='Unknown',max_length=255)
    description:str=Field(min_length=1,max_length=20000)
    published_date:date|None=None
    closing_date:date|None=None

@r.post('/opportunities')
def create_opportunity(payload:OpportunityInput,db:Session=Depends(get_db)):
    from urllib.parse import urlparse
    parsed=urlparse(payload.source_url)
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422,'Source URL must be an HTTP(S) evidence URL without credentials.')
    if db.query(Opportunity).filter(Opportunity.source_url==payload.source_url).first():
        raise HTTPException(409,'An opportunity with this source URL already exists.')
    company=db.query(Company).filter(Company.name==payload.organization).first()
    if not company:
        company=Company(name=payload.organization,country=payload.country);db.add(company);db.flush()
    row=Opportunity(company_id=company.id,**payload.model_dump(exclude={'organization'}));db.add(row);db.commit()
    return record(row)

class OpportunityUpdate(BaseModel):
    title:str|None=Field(default=None,min_length=1,max_length=255)
    description:str|None=Field(default=None,min_length=1,max_length=20000)
    country:str|None=Field(default=None,min_length=1,max_length=255)
    closing_date:date|None=None

@r.patch('/opportunities/{id}')
def update_opportunity(id:str,payload:OpportunityUpdate,db:Session=Depends(get_db)):
    row=db.get(Opportunity,id)
    if not row:raise HTTPException(404,'Opportunity not found.')
    if row.pipeline_status not in {'DISCOVERED','UNDER_REVIEW','QUALIFIED','REJECTED'}:
        raise HTTPException(409,'Requirement edits require a pre-outreach review stage.')
    for key,value in payload.model_dump(exclude_unset=True).items():
        if key!='closing_date' and (value is None or not value.strip()):raise HTTPException(422,'Text fields must contain a value.')
        setattr(row,key,value)
    row.qualification_status='PENDING';row.qualification_score=None;row.pipeline_status='UNDER_REVIEW';row.matched_services=[];row.relevance_reason='Requirement edited by operator; qualification must be rerun.'
    db.query(QualificationAssessment).filter(QualificationAssessment.opportunity_id==id).delete()
    workflow=db.get(IntelligenceWorkflow,id)
    if workflow:workflow.status='READY';workflow.completed_steps=[];workflow.outputs={}
    db.commit();return record(row)

@r.delete('/opportunities/{id}')
def archive_opportunity(id:str,db:Session=Depends(get_db)):
    row=db.get(Opportunity,id)
    if not row:raise HTTPException(404,'Opportunity not found.')
    drafts=db.query(OutreachDraft).filter(OutreachDraft.opportunity_id==id).all()
    if any(d.status in {'APPROVED','SENDING'} for d in drafts): raise HTTPException(409,'Resolve approved or sending outreach before archiving.')
    for d in drafts:
        if d.status=='WAITING_APPROVAL': d.status='REJECTED'
    row.pipeline_status='CLOSED';db.commit()
    return {'id':id,'status':'CLOSED','message':'Opportunity archived. Historical evidence and communications retained.'}
