from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.entities import Company, Opportunity, Contact, OutreachDraft, Communication
from app.models.sales_agent import ClientCasebook, CasebookEvent, ReplyReview, DailySendQuota, OrganizationResearch, SchedulerHeartbeat, WorkflowLease
from app.models.sales_followup import FollowUpTask
from app.core.config import settings
from app.services.sales_manager import policy_for
from app.services.reply_writer import content_hash, generate_reply
from app.services.casebooks import record_action

r = APIRouter(prefix='/api/sales-manager', tags=['sales-manager'])


@r.get('/sources/status')
def source_status():
    return {'google_drive_configured':bool(settings.google_client_id and settings.google_client_secret and
            settings.google_refresh_token and settings.google_drive_folder_ids),
            'github_private_read_configured':bool(settings.github_read_token),
            'demo_mode':settings.demo_mode,'imports_require_knowledge_approval':True}


@r.post('/sources/sync')
def source_sync(db:Session=Depends(get_db)):
    from app.services.company_sources import sync_company_sources
    return sync_company_sources(db)


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    auto_initial_outreach: bool = False
    auto_acknowledge: bool = False
    daily_limit: int = Field(default=10, ge=1, le=100)
    batch_size: int = Field(default=10, ge=1, le=50)


class RevisionInput(BaseModel):
    feedback: str = Field(default='', max_length=4000)
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    body_text: str | None = Field(default=None, min_length=1, max_length=12000)


class ApprovalInput(BaseModel):
    content_hash: str = Field(min_length=64, max_length=64)


class DeliveryReviewInput(BaseModel):
    resolution: str
    evidence: str = Field(min_length=20, max_length=2000)


class CaseUpdate(BaseModel):
    status: str = 'ENGAGED'
    owner_notes: str = Field(default='', max_length=10000)


def fields(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}


@r.get('/status')
def status(db:Session=Depends(get_db)):
    policy = policy_for(db)
    quota = db.get(DailySendQuota, datetime.utcnow().date().isoformat())
    heartbeat=db.get(SchedulerHeartbeat,'scheduler')
    return {'policy':fields(policy), 'demo_mode':settings.demo_mode,
            'sender':settings.microsoft_sender_email or 'Not configured',
            'attempts_today':quota.attempts if quota else 0,
            'effective_daily_limit':min(policy.daily_limit,settings.daily_outreach_limit),
            'scheduler_enabled_in_web':settings.scheduler_enabled,
            'scheduler_recently_observed':bool(heartbeat and (datetime.utcnow()-heartbeat.observed_at).total_seconds()<150),
            'scheduler_last_seen':heartbeat.observed_at if heartbeat else None,
            'ai_provider':settings.ai_provider, 'ai_configured':bool(settings.openai_api_key),
            'detailed_responses_require_approval':True}


@r.put('/policy')
def configure(payload:PolicyInput, db:Session=Depends(get_db)):
    if (payload.auto_initial_outreach or payload.auto_acknowledge) and not settings.demo_mode:
        if settings.microsoft_sender_email.lower().strip() != 'contactsales@vtabsquare.com':
            raise HTTPException(409,'Configure Contactsales@vtabsquare.com as the Microsoft sender first.')
    policy = policy_for(db)
    for key,value in payload.model_dump().items():
        setattr(policy,key,value)
    policy.updated_at=datetime.utcnow(); db.commit()
    return {'policy':fields(policy),'message':'Sales agent policy saved. Detailed client answers still require content-specific owner approval.'}


@r.post('/run')
def run(db:Session=Depends(get_db)):
    # Use the same persisted lease and run history as scheduled execution.
    from app.models.platform import ScheduledWorkflow
    from app.services.workflow_scheduler import run_and_record
    workflow=db.query(ScheduledWorkflow).filter_by(name='Sales Manager manual cycle',action_type='SALES_CYCLE').first()
    if not workflow:
        workflow=ScheduledWorkflow(name='Sales Manager manual cycle',action_type='SALES_CYCLE',enabled=False,interval_minutes=60)
        db.add(workflow);db.commit();db.refresh(workflow)
    history=run_and_record(db,workflow)
    if history is None:
        raise HTTPException(409,'This workflow is already running. Check Job Monitor.')
    return {'status':history.status,'history_id':history.id,'result':history.result}


@r.get('/cases')
def cases(db:Session=Depends(get_db)):
    items=[]
    for case in db.query(ClientCasebook).order_by(ClientCasebook.updated_at.desc()).limit(500).all():
        company=db.get(Company,case.company_id)
        items.append({**fields(case),'company_name':company.name if company else 'Unknown',
                      'event_count':db.query(CasebookEvent).filter_by(casebook_id=case.id).count()})
    return {'items':items}


@r.get('/cases/{case_id}')
def case_detail(case_id:str,db:Session=Depends(get_db)):
    case=db.get(ClientCasebook,case_id)
    if not case: raise HTTPException(404,'Client casebook not found')
    return {'case':fields(case),'company':fields(db.get(Company,case.company_id)),
            'research':[fields(row) for row in db.query(OrganizationResearch).join(Opportunity,Opportunity.id==OrganizationResearch.opportunity_id).filter(Opportunity.company_id==case.company_id).all()],
            'contacts':[fields(c) for c in db.query(Contact).filter_by(company_id=case.company_id).all()],
            'opportunities':[fields(o) for o in db.query(Opportunity).filter_by(company_id=case.company_id).all()],
            'events':[fields(e) for e in db.query(CasebookEvent).filter_by(casebook_id=case.id).order_by(CasebookEvent.created_at).all()]}


@r.patch('/cases/{case_id}')
def update_case(case_id:str,payload:CaseUpdate,db:Session=Depends(get_db)):
    case=db.get(ClientCasebook,case_id)
    if not case: raise HTTPException(404,'Client casebook not found')
    if payload.status not in {'RESPONDED','ENGAGED','PROPOSAL','NEGOTIATION','WON','LOST','CLOSED'}:
        raise HTTPException(422,'Invalid case status')
    case.status=payload.status;case.owner_notes=payload.owner_notes;case.updated_at=datetime.utcnow()
    db.add(CasebookEvent(casebook_id=case.id,event_key='owner:'+str(uuid4()),kind='OWNER_UPDATE',
                        body=payload.owner_notes,details={'status':payload.status}))
    db.commit();return fields(case)


@r.get('/reviews')
def reviews(db:Session=Depends(get_db)):
    items=[]
    for task in db.query(FollowUpTask).filter(FollowUpTask.status.in_(['PENDING','APPROVED','SENDING','DELIVERY_REVIEW'])).order_by(FollowUpTask.due_at).limit(200).all():
        review=db.get(ReplyReview,task.id)
        items.append({**fields(task),'content_hash':content_hash(task),
                      'analysis':review.analysis if review else {},
                      'delivery_draft_id':review.outreach_id if review else None,
                      'scheduled_send_approved':bool(review and review.approved_hash)})
    return {'items':items}


@r.post('/reviews/{task_id}/reconcile')
def reconcile(task_id:str,payload:DeliveryReviewInput,db:Session=Depends(get_db)):
    if len(payload.evidence.strip())<20: raise HTTPException(422,'A meaningful delivery evidence note is required')
    task=db.query(FollowUpTask).filter_by(id=task_id).with_for_update().first()
    if not task: raise HTTPException(404,'Response recommendation not found')
    if task.status not in {'SENDING','DELIVERY_REVIEW'}: raise HTTPException(409,'This task does not require delivery reconciliation')
    lease=db.get(WorkflowLease,'action:SALES_CYCLE')
    if task.status=='SENDING' and lease and lease.expires_at>datetime.utcnow():
        raise HTTPException(409,'The sales worker may still be sending. Wait for the run or its lease to finish.')
    review=db.get(ReplyReview,task.id)
    outbound=db.get(OutreachDraft,review.outreach_id) if review and review.outreach_id else None
    if not outbound: raise HTTPException(409,'No delivery attempt is recorded for this task')
    if payload.resolution=='SENT_CONFIRMED':
        if outbound.status!='SENT':
            outbound.status='SENT'
            db.add(Communication(opportunity_id=outbound.opportunity_id,direction='OUTBOUND',
                subject=outbound.subject,body=outbound.body_text,status='HUMAN_CONFIRMED_SENT'))
            record_action(db,outbound.opportunity_id,'outbound:'+outbound.id,'OUTBOUND',outbound.subject,
                outbound.body_text,{'delivery_status':'HUMAN_CONFIRMED_SENT','evidence':payload.evidence})
        task.status='SENT'
    elif payload.resolution=='NOT_SENT_CONFIRMED':
        if outbound.status=='SENT': raise HTTPException(409,'A recorded accepted/sent message cannot be reset as unsent')
        outbound.status='REJECTED';review.outreach_id=None;review.approved_hash=None
        task.status='PENDING';task.human_approved=False
    else: raise HTTPException(422,'Choose SENT_CONFIRMED or NOT_SENT_CONFIRMED after checking Sent Items and provider records')
    record_action(db,task.opportunity_id,'delivery-review:'+str(uuid4()),'DELIVERY_RECONCILED',
                  details={'resolution':payload.resolution,'owner_evidence':payload.evidence})
    db.commit();return {'id':task.id,'status':task.status,'message':'Delivery review recorded. A new attempt requires a new owner approval.'}


@r.post('/reviews/{task_id}/revise')
def revise(task_id:str,payload:RevisionInput,db:Session=Depends(get_db)):
    task=db.query(FollowUpTask).filter_by(id=task_id).with_for_update().first()
    if not task: raise HTTPException(404,'Response recommendation not found')
    if task.status not in {'PENDING','APPROVED'}: raise HTTPException(409,'This response cannot be revised')
    review=db.get(ReplyReview,task.id)
    if review and review.outreach_id:
        outbound=db.get(OutreachDraft,review.outreach_id)
        if outbound and outbound.status in {'SENDING','SENT','SEND_FAILED'}:
            raise HTTPException(409,'Reconcile the previous delivery attempt before revising.')
        if outbound:
            outbound.status='REJECTED'
        review.outreach_id=None
    if payload.subject is None and payload.body_text is None:
        try: review=generate_reply(db,task,payload.feedback)
        except ValueError as exc: raise HTTPException(409,str(exc))
        except Exception: raise HTTPException(502,'AI generation failed. Check provider configuration.')
    else:
        review=review or ReplyReview(task_id=task.id)
        if payload.subject is not None: task.draft_subject=payload.subject
        if payload.body_text is not None: task.draft_body=payload.body_text
        review.analysis={**(review.analysis or {}),'requires_manual_revision':False}
        review.approved_hash=None;db.add(review)
        task.human_approved=False;task.status='PENDING'
    record_action(db,task.opportunity_id,'revision:'+str(uuid4()),'REPLY_REVISED',task.draft_subject,
                  task.draft_body,{'owner_feedback':payload.feedback})
    db.commit();return {'id':task.id,'content_hash':content_hash(task),'analysis':review.analysis,'message':'Revision saved. Review and approve the new version.'}


@r.post('/reviews/{task_id}/approve')
def approve(task_id:str,payload:ApprovalInput,db:Session=Depends(get_db)):
    # Row lock serializes editing/approval/sending on PostgreSQL.
    task=db.query(FollowUpTask).filter_by(id=task_id).with_for_update().first()
    if not task: raise HTTPException(404,'Response recommendation not found')
    if task.status != 'PENDING': raise HTTPException(409,'Only pending responses can be approved')
    if not task.draft_body.strip() or payload.content_hash != content_hash(task):
        raise HTTPException(409,'The response changed. Reload and review the latest version.')
    review=db.get(ReplyReview,task.id) or ReplyReview(task_id=task.id)
    review.approved_hash=payload.content_hash;db.add(review)
    task.human_approved=True;task.status='APPROVED'
    record_action(db,task.opportunity_id,'approval:'+str(uuid4()),'OWNER_APPROVAL',task.draft_subject,
                  task.draft_body,{'content_hash':payload.content_hash})
    db.commit();return {'id':task.id,'message':'This exact response is approved for delivery in the next enabled sales cycle.'}
