from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.db import get_db
from app.models.sales_followup import FollowUpTask, InboundResponse
from app.models.entities import Opportunity
from app.services.response_intelligence import sync_inbox, reprocess_existing, QUALIFIED, NON_CUSTOMER

r=APIRouter(prefix="/api",tags=["sales-intelligence"])

@r.post("/responses/sync")
def sync_responses(db:Session=Depends(get_db)):
    try:return sync_inbox(db)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@r.post("/responses/reprocess")
def reprocess(db:Session=Depends(get_db)):
    try:return reprocess_existing(db)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@r.get("/responses")
def responses(db:Session=Depends(get_db)):
    rows=db.query(InboundResponse).order_by(InboundResponse.received_at.desc()).limit(500).all()
    fields=["id","opportunity_id","outreach_draft_id","sender_name","sender_email","subject","body_text","received_at","classification","sentiment","summary","suggested_action","suggested_reply","confidence","review_required"]
    return [{**{k:getattr(x,k) for k in fields},"matched":bool(x.opportunity_id or x.outreach_draft_id),"is_customer_response":x.classification in QUALIFIED} for x in rows]

@r.get("/follow-ups")
def followups(db:Session=Depends(get_db)):
    rows=db.query(FollowUpTask).order_by(FollowUpTask.due_at.asc()).limit(200).all()
    return [{k:getattr(x,k) for k in ["id","opportunity_id","outreach_draft_id","response_id","status","action_type","due_at","reason","draft_subject","draft_body","human_approved"]} for x in rows]

@r.post("/follow-ups/{task_id}/approve")
def approve(task_id:str,db:Session=Depends(get_db)):
    x=db.get(FollowUpTask,task_id)
    if not x: raise HTTPException(404,"Follow-up task not found")
    if x.status != 'PENDING': raise HTTPException(409,'Only pending recommendations may be approved')
    from app.models.sales_agent import ReplyReview
    review=db.get(ReplyReview,x.id)
    if review: review.approved_hash=None  # This older endpoint approves preparation, not scheduled delivery.
    x.human_approved=True;x.status="APPROVED";db.commit();return {"id":x.id,"status":x.status,"message":"Approved for the next human-controlled step. No email was sent."}

@r.post("/follow-ups/{task_id}/dismiss")
def dismiss(task_id:str,db:Session=Depends(get_db)):
    x=db.get(FollowUpTask,task_id)
    if not x: raise HTTPException(404,"Follow-up task not found")
    if x.status not in {'PENDING','APPROVED'}: raise HTTPException(409,'Follow-up cannot be dismissed from its current status')
    x.human_approved=False
    x.status="DISMISSED";db.commit();return {"id":x.id,"status":x.status}

@r.get("/pipeline")
def pipeline(db:Session=Depends(get_db)):
    ops=db.query(Opportunity).all(); responses=db.query(InboundResponse).all(); fus=db.query(FollowUpTask).all(); pc={};rc={}
    for x in ops: pc[x.pipeline_status or "NEW"]=pc.get(x.pipeline_status or "NEW",0)+1
    for x in responses: rc[x.classification]=rc.get(x.classification,0)+1
    qualified=sum(x.classification in QUALIFIED for x in responses); filtered=sum(x.classification in NON_CUSTOMER for x in responses); matched=sum(bool(x.opportunity_id or x.outreach_draft_id) for x in responses)
    return {"opportunities_total":len(ops),"inbox_messages_total":len(responses),"responses_total":qualified,"filtered_messages_total":filtered,"matched_responses_total":matched,"pipeline":pc,"response_classifications":rc,"follow_ups_pending":sum(x.status=="PENDING" for x in fus),"follow_ups_approved":sum(x.status=="APPROVED" for x in fus)}


@r.post('/follow-ups/{task_id}/prepare-outreach')
def prepare_followup(task_id:str, db:Session=Depends(get_db)):
    from app.models.entities import OutreachDraft, Contact
    task=db.get(FollowUpTask,task_id)
    if not task: raise HTTPException(404,'Follow-up task not found')
    if not task.human_approved or task.status != 'APPROVED': raise HTTPException(409,'Human approval is required before preparing follow-up outreach')
    from app.models.sales_agent import ReplyReview
    review=db.get(ReplyReview,task.id)
    if review and review.outreach_id: raise HTTPException(409,'This response already has a delivery draft. Review it in Send Center.')
    original=db.get(OutreachDraft,task.outreach_draft_id) if task.outreach_draft_id else None
    if not original or not original.contact_id: raise HTTPException(409,'A matched recipient is required')
    contact=db.get(Contact,original.contact_id)
    if not contact or contact.do_not_contact: raise HTTPException(409,'Recipient is missing or suppressed')
    if not task.draft_body.strip(): raise HTTPException(409,'Review and provide a response body first')
    draft=OutreachDraft(opportunity_id=task.opportunity_id,contact_id=original.contact_id,subject=task.draft_subject,body_text=task.draft_body,status='WAITING_APPROVAL')
    db.add(draft);task.status='DRAFTED';db.commit();db.refresh(draft)
    return {'id':draft.id,'status':draft.status,'message':'Follow-up draft prepared. Review in Approval Queue before a confirmed send.'}
