from datetime import datetime
import httpx
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.platform import ServicePortfolio,DiscoverySource,ResourceLink,EmailTemplate,CompanyAsset,ScheduledWorkflow,WorkflowRunHistory
from app.services.global_discovery import run_discovery,queries,seed_defaults
from app.services.workflow_scheduler import run_and_record,next_run
from app.core.config import settings
r=APIRouter(prefix='/api/platform',tags=['platform'])
class Item(BaseModel):
    name:str=''; title:str=''; category:str='Digital Services'; description:str=''; keywords:list[str]=[]; target_buyers:list[str]=[]; active:bool=True; source_type:str='WEB_SEARCH'; base_url:str=''; countries:list[str]=[]; resource_type:str='PRESENTATION'; url:str=''; tags:list[str]=[]; subject:str=''; body_html:str=''; purpose:str='OUTREACH'; asset_type:str='COMPANY_WEBSITE'; action_type:str='DISCOVERY'; interval_minutes:int=Field(default=1440, ge=5, le=525600); timezone:str='Asia/Kolkata'; run_at_time:str='09:00'; enabled:bool=True
class GenerateRequest(BaseModel):
    prompt:str; tone:str='Professional'; purpose:str='OUTREACH'; company:str=''; opportunity:str=''; services:str=''
MODELS={'services':ServicePortfolio,'sources':DiscoverySource,'resources':ResourceLink,'templates':EmailTemplate,'assets':CompanyAsset,'schedules':ScheduledWorkflow}

@r.get('/overview')
def overview(db:Session=Depends(get_db)):
    seed_defaults(db); return {k:db.query(m).count() for k,m in MODELS.items()}|{'search_provider_configured':bool(settings.serper_api_key)}
@r.get('/discovery/queries')
def discovery_queries(db:Session=Depends(get_db)): return {'queries':queries(db)}
@r.post('/discovery/run')
def discovery_run(db:Session=Depends(get_db)): return run_discovery(db)
@r.get('/schedule-history/all')
def schedule_history(limit:int=200,db:Session=Depends(get_db)):
    return db.query(WorkflowRunHistory).order_by(WorkflowRunHistory.started_at.desc()).limit(min(max(limit,1),1000)).all()
@r.get('/schedule-history/{workflow_id}')
def schedule_history_for(workflow_id:str,limit:int=100,db:Session=Depends(get_db)):
    return db.query(WorkflowRunHistory).filter(WorkflowRunHistory.workflow_id==workflow_id).order_by(WorkflowRunHistory.started_at.desc()).limit(min(max(limit,1),500)).all()
@r.post('/schedules/{id}/run')
def run_schedule(id:str,db:Session=Depends(get_db)):
    w=db.get(ScheduledWorkflow,id)
    if not w: raise HTTPException(404,'Schedule not found')
    h=run_and_record(db,w)
    if h is None: raise HTTPException(409,'This workflow is already running.')
    return {'status':h.status,'history_id':h.id,'result':h.result,'error':h.error}
@r.post('/templates/generate')
def generate_template(p:GenerateRequest):
    if not settings.openai_api_key:
        return {'configured':False,'subject':f'VTAB Square | {p.opportunity or p.purpose.replace("_"," ").title()}','html':f'''<p>Hello {{{{Name}}}},</p><p>{p.prompt}</p><p>Based on your current priorities, VTAB Square can support <strong>{p.services or '{{Services}}'}</strong> with a focused delivery approach.</p><p>Would you be open to a short discussion?</p><p>Regards,<br><strong>VTAB Square Business Development</strong></p>''','message':'OPENAI_API_KEY is not configured; a structured starter draft was generated locally.'}
    system='You write concise B2B technology outreach for VTAB Square. Return JSON only with keys subject and html. Use email-safe HTML, no scripts, no external CSS. Preserve placeholders like {{Name}}, {{Organization}}, {{Opportunity}}, {{Services}}.'
    user=f'Purpose: {p.purpose}\nTone: {p.tone}\nCompany: {p.company}\nOpportunity: {p.opportunity}\nServices: {p.services}\nInstruction: {p.prompt}'
    try:
        rr=httpx.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {settings.openai_api_key}','Content-Type':'application/json'},json={'model':settings.openai_model,'instructions':system+' Output valid JSON only.','input':user},timeout=45); rr.raise_for_status(); import json; payload=rr.json(); output_text=''.join(c.get('text','') for item in payload.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text'); data=json.loads(output_text); return {'configured':True,**data}
    except Exception as e: raise HTTPException(502,f'AI generation failed: {str(e)[:300]}')
@r.get('/{kind}')
def listing(kind:str,db:Session=Depends(get_db)):
    m=MODELS.get(kind)
    if not m: raise HTTPException(404,'Unknown collection')
    if kind=='services': seed_defaults(db)
    return db.query(m).all()
@r.post('/{kind}')
def create(kind:str,p:Item,db:Session=Depends(get_db)):
    m=MODELS.get(kind)
    if not m: raise HTTPException(404,'Unknown collection')
    fields={c.name for c in m.__table__.columns if c.name not in {'id','created_at','last_run_at','next_run_at','last_status','last_result'}}; data={k:v for k,v in p.model_dump().items() if k in fields}
    validate_item(kind, data)
    if kind=='schedules': temp=ScheduledWorkflow(**data); data['next_run_at']=next_run(temp)
    obj=m(**data); db.add(obj)
    try: db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, 'Unable to save item. Check required fields and duplicate names.')
    db.refresh(obj); return obj
@r.patch('/{kind}/{id}')
def update(kind:str,id:str,p:Item,db:Session=Depends(get_db)):
    m=MODELS.get(kind); obj=db.get(m,id) if m else None
    if not obj: raise HTTPException(404,'Item not found')
    fields={c.name for c in m.__table__.columns}; data=p.model_dump(exclude_unset=True)
    validate_item(kind, {**{c.name:getattr(obj,c.name) for c in m.__table__.columns}, **data})
    for k,v in data.items():
        if k in fields: setattr(obj,k,v)
    if kind=='schedules': obj.next_run_at=next_run(obj)
    db.commit(); db.refresh(obj); return obj
@r.delete('/{kind}/{id}')
def delete(kind:str,id:str,db:Session=Depends(get_db)):
    m=MODELS.get(kind); obj=db.get(m,id) if m else None
    if not obj: raise HTTPException(404,'Item not found')
    if kind=='schedules' and db.query(WorkflowRunHistory).filter(WorkflowRunHistory.workflow_id==id).first(): raise HTTPException(409,'Disable schedules with execution history instead of deleting their audit trail.')
    db.delete(obj); db.commit(); return {'deleted':True}


def validate_item(kind, data):
    from urllib.parse import urlparse
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    key = 'title' if kind == 'resources' else 'name'
    if not str(data.get(key) or '').strip(): raise HTTPException(422, f'{key} is required')
    if kind in {'resources', 'assets'} or (kind=='sources' and data.get('source_type') in {'RSS','WEBSITE'}):
        url = data.get('base_url') if kind=='sources' else data.get('url')
        if urlparse(url or '').scheme not in {'https','http'} or not urlparse(url or '').hostname:
            raise HTTPException(422, 'A valid HTTP/HTTPS URL is required')
    if kind=='sources' and data.get('source_type') not in {'RSS','WEBSITE','WEB_SEARCH'}: raise HTTPException(422,'Unsupported source type')
    if kind=='templates' and (not data.get('subject','').strip() or not data.get('body_html','').strip()): raise HTTPException(422,'Subject and email content are required')
    if kind=='schedules':
        if data.get('action_type') not in {'DISCOVERY','INBOX_SYNC','REPROCESS','SALES_CYCLE','RESOURCE_SYNC'}: raise HTTPException(422,'Unsupported workflow action')
        try:
            ZoneInfo(data.get('timezone') or 'UTC')
            hh,mm = map(int,data.get('run_at_time','09:00').split(':'))
            if not (0<=hh<=23 and 0<=mm<=59): raise ValueError()
        except (ZoneInfoNotFoundError, ValueError): raise HTTPException(422,'Valid timezone and HH:MM run time are required')
