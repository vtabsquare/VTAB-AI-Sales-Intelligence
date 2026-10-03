"""Resumable allowlisted workflow; the supervisor cannot send email."""
from datetime import datetime,timedelta
from sqlalchemy import update
from app.models.entities import Opportunity,OutreachDraft
from app.models.intelligence import IntelligenceWorkflow
from app.services.knowledge import retrieve

def run(db, opportunity):
    from app.services import engine
    row=db.get(IntelligenceWorkflow,opportunity.id)
    if not row:
        row=IntelligenceWorkflow(opportunity_id=opportunity.id,completed_steps=[],outputs={},status='READY');db.add(row);db.commit()
    if row.status=='REVIEW_REQUIRED':
        row.status='READY';row.completed_steps=[];row.outputs={};db.commit()
    # Explicit rerun may reclaim a process that died; short provider operations are bounded.
    if row.status=='RUNNING' and row.updated_at < datetime.utcnow()-timedelta(minutes=15):
        row.status='FAILED';db.commit()
    claimed=db.execute(update(IntelligenceWorkflow).where(IntelligenceWorkflow.opportunity_id==opportunity.id,IntelligenceWorkflow.status.in_(['READY','FAILED'])).values(status='RUNNING',error='',updated_at=datetime.utcnow()))
    if claimed.rowcount!=1:
        db.rollback();return row
    db.commit();db.refresh(row)
    def qualify():
        engine.qualify(db,opportunity)
        return {'status':opportunity.qualification_status,'score':opportunity.qualification_score}
    def matching():
        evidence=retrieve(db,f'{opportunity.title} {opportunity.description}')
        if not evidence: raise ValueError('No approved knowledge evidence matches this opportunity.')
        return {'matched_services':opportunity.matched_services,'knowledge':evidence,'do_not_claim':['Undocumented customer references','Undocumented certifications']}
    def outreach():
        existing=db.query(OutreachDraft).filter(OutreachDraft.opportunity_id==opportunity.id,OutreachDraft.status.in_(['WAITING_APPROVAL','APPROVED','SENDING'])).first()
        d=existing or engine.draft(db,opportunity)
        return {'draft_id':d.id,'status':d.status}
    tools=[('qualify',qualify),('research',lambda:engine.research(db,opportunity)),('capability_match',matching),('contact',lambda:{'contact_id':engine.find_contact(db,opportunity).id}),('outreach',outreach)]
    try:
        for name,tool in tools:
            if name in row.completed_steps: continue
            output=tool()
            row.completed_steps=[*row.completed_steps,name];row.outputs={**row.outputs,name:output};row.updated_at=datetime.utcnow();db.commit()
            if name=='qualify' and opportunity.qualification_status!='QUALIFIED':
                row.status='REVIEW_REQUIRED';db.commit();return row
        row.status='WAITING_APPROVAL';row.updated_at=datetime.utcnow();db.commit()
        engine.log(db,'Supervisor Agent',{'opportunity_id':opportunity.id},{'completed_steps':row.completed_steps,'status':row.status})
    except Exception:
        db.rollback();row=db.get(IntelligenceWorkflow,opportunity.id);row.status='FAILED';row.error='Workflow stopped. Review provider, evidence and knowledge configuration, then retry.';db.commit()
        engine.log(db,'Supervisor Agent',{'opportunity_id':opportunity.id},{'completed_steps':row.completed_steps,'error':row.error},'FAILED')
    return row
