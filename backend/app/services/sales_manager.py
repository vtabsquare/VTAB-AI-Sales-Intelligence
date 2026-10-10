from datetime import datetime
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.models.entities import Opportunity, OutreachDraft, Contact, Suppression, Communication
from app.models.sales_followup import InboundResponse, FollowUpTask
from app.models.sales_agent import SalesAgentPolicy, SalesOutbound, ReplyReview, DailySendQuota, ClientCasebook


def policy_for(db):
    policy = db.get(SalesAgentPolicy, 'default')
    if not policy:
        policy = SalesAgentPolicy(id='default')
        db.add(policy)
        try: db.commit()
        except IntegrityError:
            db.rollback();return db.get(SalesAgentPolicy,'default')
        db.refresh(policy)
    return policy


def reserve_daily_send(db):
    """Atomic quota reservation; failed/ambiguous attempts still consume quota."""
    day = datetime.utcnow().date().isoformat()
    if not db.get(DailySendQuota, day):
        try:
            with db.begin_nested():
                baseline=db.query(Communication).filter(Communication.direction=='OUTBOUND',
                    Communication.created_at>=datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)).count()
                db.add(DailySendQuota(day=day, attempts=baseline))
                db.flush()
        except IntegrityError:
            pass
    policy = db.query(SalesAgentPolicy).filter_by(id='default').populate_existing().first()
    limit = min(settings.daily_outreach_limit, policy.daily_limit) if policy else settings.daily_outreach_limit
    result = db.execute(update(DailySendQuota).where(DailySendQuota.day==day,
                        DailySendQuota.attempts < limit).values(attempts=DailySendQuota.attempts+1))
    if result.rowcount != 1:
        db.rollback()
        raise ValueError('Daily outbound attempt limit reached')


def eligible(db, draft):
    contact = db.get(Contact, draft.contact_id) if draft.contact_id else None
    if contact:
        case=db.query(ClientCasebook).filter_by(company_id=contact.company_id).first()
        if case and case.status in {'LOST','CLOSED'}: return False
    statuses = {'VERIFIED','HUMAN_VERIFIED'}
    if settings.demo_mode and settings.app_env in {'test','local','development'}:
        statuses.add('TEST_VERIFIED')
    return bool(contact and contact.email and not contact.do_not_contact
                and contact.email_verification_status in statuses
                and not db.query(Suppression).filter(func.lower(Suppression.email)==contact.email.lower()).first())


def run_sales_cycle(db):
    """Bounded periodic workflow. Owner policy permits initial EOI/fixed acknowledgement only."""
    from app.services.global_discovery import run_discovery
    from app.services.response_intelligence import sync_inbox
    from app.services.engine import qualify, research, draft, send
    from app.services.reply_writer import generate_reply, content_hash
    policy = policy_for(db)
    if not policy.enabled:
        return {'status':'PAUSED', 'message':'Enable the sales agent in Sales Manager first.'}
    result = {'status':'COMPLETED','demo_mode':settings.demo_mode,'steps':{},'issues':[]}
    def issue(step):
        # Exception details can contain provider URLs/secrets. Store a safe diagnostic.
        result['issues'].append({'step':step,'message':'Step failed; review configuration and audit logs before retrying.'})
    try:
        result['steps']['discovery'] = run_discovery(db)
        if result['steps']['discovery'].get('errors'):
            result['issues'].append({'step':'discovery','message':'One or more discovery sources were unavailable. Review Discovery Engine connector errors.'})
    except Exception:
        db.rollback(); issue('discovery')
    if settings.microsoft_sender_email and not settings.demo_mode:
        try:
            result['steps']['inbox'] = sync_inbox(db)
        except Exception:
            db.rollback(); issue('inbox')
    else:
        result['steps']['inbox'] = {'status':'SKIPPED','reason':'Demo mode or Microsoft mailbox not configured.'}
    made = 0
    candidates = db.query(Opportunity).filter(Opportunity.pipeline_status.in_(
        ['DISCOVERED','UNDER_REVIEW','QUALIFIED','RESEARCHING','CONTACT_IDENTIFIED'])).order_by(Opportunity.created_at).limit(policy.batch_size).all()
    for opportunity in candidates:
        if db.query(OutreachDraft).filter_by(opportunity_id=opportunity.id).first():
            continue
        try:
            qualify(db, opportunity)
            if opportunity.qualification_status != 'QUALIFIED':
                continue
            research(db, opportunity)
            outreach = draft(db, opportunity)
            db.add(SalesOutbound(draft_id=outreach.id, purpose='INITIAL'))
            db.commit(); made += 1
        except Exception:
            db.rollback(); issue('research/draft:' + opportunity.id)
    result['steps']['initial_drafts'] = made
    # Drafts awaiting verified recipient evidence remain visible, never guessed or silently sent.
    if policy.auto_initial_outreach:
        rows = db.query(OutreachDraft).join(SalesOutbound, SalesOutbound.draft_id==OutreachDraft.id).filter(
            SalesOutbound.purpose=='INITIAL', OutreachDraft.status=='WAITING_APPROVAL').limit(policy.batch_size).all()
        for outreach in rows:
            if not eligible(db, outreach):
                continue
            try:
                outreach.status='APPROVED'; db.commit(); send(db, outreach)
            except Exception:
                db.rollback()
                if outreach.status=='APPROVED':
                    outreach.status='WAITING_APPROVAL';db.commit()
                issue('initial-send:' + outreach.id)
    # Fixed acknowledgement is separate from the detailed answer and sent at most once per imported reply.
    if policy.auto_acknowledge:
        replies = db.query(InboundResponse).filter(InboundResponse.opportunity_id.is_not(None),
            InboundResponse.classification.in_(['INTERESTED','NEEDS_INFO','FOLLOW_UP_LATER'])).order_by(InboundResponse.processed_at.desc()).limit(policy.batch_size).all()
        for response in replies:
            if db.query(SalesOutbound).filter_by(response_id=response.id).first():
                continue
            original = db.get(OutreachDraft,response.outreach_draft_id) if response.outreach_draft_id else None
            if not original or not eligible(db,original):
                continue
            acknowledgement = OutreachDraft(opportunity_id=response.opportunity_id,contact_id=original.contact_id,
                subject=('Re: '+response.subject)[:255], status='APPROVED',
                body_text='Hello,\n\nThank you for contacting VTAB Square. We have received your response and our team will review your requirements before sharing a detailed answer.\n\nRegards,\nVTAB Square Business Development')
            try:
                db.add(acknowledgement); db.flush()
                db.add(SalesOutbound(draft_id=acknowledgement.id,purpose='ACKNOWLEDGEMENT',response_id=response.id))
                db.commit(); send(db,acknowledgement)
            except Exception:
                db.rollback(); issue('acknowledgement:' + response.id)
    for task in db.query(FollowUpTask).filter(FollowUpTask.status=='PENDING').limit(policy.batch_size).all():
        if db.get(ReplyReview,task.id):
            continue
        try:
            generate_reply(db,task); db.commit()
        except Exception:
            db.rollback(); issue('reply-draft:' + task.id)
    # Only a content-bound approval issued from Sales Manager authorizes scheduled response delivery.
    for task, review in db.query(FollowUpTask,ReplyReview).join(ReplyReview,ReplyReview.task_id==FollowUpTask.id).filter(
        FollowUpTask.status=='APPROVED', FollowUpTask.human_approved.is_(True), ReplyReview.approved_hash.is_not(None)).limit(policy.batch_size).all():
        try:
            task=db.query(FollowUpTask).filter_by(id=task.id).with_for_update().populate_existing().first()
            review=db.query(ReplyReview).filter_by(task_id=task.id).populate_existing().first()
            if task.status!='APPROVED' or not task.human_approved:
                db.rollback();continue
            due=task.due_at.replace(tzinfo=None) if task.due_at else None
            if task.action_type=='FOLLOW_UP' and due and due>datetime.utcnow():
                db.rollback();continue
            if review.approved_hash != content_hash(task):
                task.status='PENDING'; task.human_approved=False; review.approved_hash=None; db.commit()
                continue
            original = db.get(OutreachDraft,task.outreach_draft_id) if task.outreach_draft_id else None
            if not original or not eligible(db,original):
                continue
            if review.outreach_id:
                outbound = db.get(OutreachDraft,review.outreach_id)
                if not outbound or outbound.status != 'APPROVED':
                    continue  # Ambiguous/failed attempts need human reconciliation, never automatic retries.
            else:
                outbound = OutreachDraft(opportunity_id=task.opportunity_id,contact_id=original.contact_id,
                    subject=task.draft_subject[:255],body_text=task.draft_body,status='APPROVED')
                db.add(outbound); db.flush(); review.outreach_id=outbound.id
            task.status='SENDING';db.commit()
            send(db,outbound); task.status='SENT'; db.commit()
        except Exception:
            db.rollback()
            task.status='DELIVERY_REVIEW';db.commit()
            issue('approved-reply-send:' + task.id)
    if result['issues']:
        result['status']='PARTIAL'
    return result
