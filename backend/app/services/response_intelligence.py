from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from html import unescape
import httpx
from sqlalchemy import or_,func
from app.core.config import settings
from app.models.sales_followup import FollowUpTask, InboundResponse, MailSyncState
from app.models.entities import Contact, OutreachDraft, Opportunity, Suppression

POSITIVE=("interested","sounds good","let's discuss","schedule","meeting","call","proposal","demo","please contact")
NEGATIVE=("not interested","no thanks","remove me","unsubscribe","do not contact","not required")
LATER=("later","next month","next quarter","circle back","follow up")
INFO=("more information","details","pricing","rate","rates","capability","capabilities","case study","briefing","registration request")
AUTO_SENDERS=("noreply","no-reply","donotreply","do-not-reply","mailer-daemon","postmaster","powerautomate","notifications@","notification@")
AUTO_WORDS=("automated notification","automatic reply","out of office","delivery status notification","undeliverable","delivery has failed","flow(s) have failed","password reset","security alert")
PROCUREMENT_WORDS=("etenders","tender","procurement","rfp","rfq","cft","pin publication","contract notice","bid notification")
MARKETING_WORDS=("newsletter","webinar","renewal","special offer","promotion","marketing","opt out","view in browser")

QUALIFIED={"INTERESTED","NEEDS_INFO","FOLLOW_UP_LATER","NOT_INTERESTED","NEEDS_REVIEW"}
NON_CUSTOMER={"AUTOMATED_NOTIFICATION","PROCUREMENT_UPDATE","BOUNCE_NDR","NEWSLETTER_MARKETING","INTERNAL"}

def _strip_html(value):
    return re.sub(r"\s+"," ",unescape(re.sub(r"<[^>]+>"," ",value or ""))).strip()

def _norm_subject(value):
    s=(value or "").lower().strip()
    while True:
        n=re.sub(r"^(re|fw|fwd)\s*:\s*","",s,flags=re.I).strip()
        if n==s:return s
        s=n

def _domain(email):
    return (email.rsplit("@",1)[1].lower() if "@" in (email or "") else "")

def classify_message(sender_email,subject,body,mailbox=""):
    email=(sender_email or "").lower(); text=f"{subject} {body}".lower(); domain=_domain(email)
    if email == (mailbox or "").lower() or domain == _domain(mailbox):
        return {"classification":"INTERNAL","sentiment":"NEUTRAL","summary":"Internal VTAB mailbox message; excluded from customer-response KPIs.","suggested_action":"No sales follow-up is created automatically.","confidence":98,"review_required":False}
    if "mailer-daemon" in email or "postmaster" in email or any(x in text for x in ("undeliverable","delivery status notification","delivery has failed","returned mail")):
        return {"classification":"BOUNCE_NDR","sentiment":"NEUTRAL","summary":"Delivery/bounce notification; not a customer response.","suggested_action":"Review recipient deliverability before future outreach.","confidence":96,"review_required":True}
    if any(x in text for x in NEGATIVE): return {"classification":"NOT_INTERESTED","sentiment":"NEGATIVE","summary":"The recipient appears to decline further outreach.","suggested_action":"Close or suppress follow-up after human review.","confidence":90,"review_required":True}
    # Procurement notifications are operationally valuable even when sent from a no-reply address,
    # so classify them before the generic automated-notification rule.
    if any(x in text for x in PROCUREMENT_WORDS) or "etenders" in domain:
        return {"classification":"PROCUREMENT_UPDATE","sentiment":"NEUTRAL","summary":"Procurement/tender update detected; track as opportunity intelligence rather than a customer reply.","suggested_action":"Review against the related tender/opportunity and update pipeline if relevant.","confidence":92,"review_required":True}
    if any(x in email for x in AUTO_SENDERS) or any(x in text for x in AUTO_WORDS):
        return {"classification":"AUTOMATED_NOTIFICATION","sentiment":"NEUTRAL","summary":"Automated system notification; excluded from customer-response KPIs.","suggested_action":"No customer follow-up. Review only if operationally relevant.","confidence":94,"review_required":False}
    if any(x in text for x in MARKETING_WORDS):
        return {"classification":"NEWSLETTER_MARKETING","sentiment":"NEUTRAL","summary":"Marketing/newsletter-style message; excluded from customer-response KPIs.","suggested_action":"No sales follow-up is required.","confidence":82,"review_required":False}
    if any(x in text for x in NEGATIVE): return {"classification":"NOT_INTERESTED","sentiment":"NEGATIVE","summary":"The recipient appears to decline further outreach.","suggested_action":"Close or suppress follow-up after human review.","confidence":90,"review_required":True}
    if any(x in text for x in LATER): return {"classification":"FOLLOW_UP_LATER","sentiment":"NEUTRAL","summary":"The recipient appears open to a later follow-up.","suggested_action":"Create a follow-up task for human review.","confidence":80,"review_required":True}
    if any(x in text for x in INFO): return {"classification":"NEEDS_INFO","sentiment":"POSITIVE","summary":"The recipient appears to request additional information.","suggested_action":"Prepare an information response for human approval.","confidence":82,"review_required":True}
    if any(x in text for x in POSITIVE): return {"classification":"INTERESTED","sentiment":"POSITIVE","summary":"The recipient appears interested in continuing the conversation.","suggested_action":"Prepare a response and propose the next discussion step.","confidence":84,"review_required":True}
    return {"classification":"NEEDS_REVIEW","sentiment":"NEUTRAL","summary":"A potentially relevant external message requires human review.","suggested_action":"Review the message and decide the next action.","confidence":45,"review_required":True}

def _token(client):
    vals={"MICROSOFT_TENANT_ID":settings.microsoft_tenant_id,"MICROSOFT_CLIENT_ID":settings.microsoft_client_id,"MICROSOFT_CLIENT_SECRET":settings.microsoft_client_secret,"MICROSOFT_SENDER_EMAIL":settings.microsoft_sender_email}
    missing=[k for k,v in vals.items() if not (v or "").strip()]
    if missing: raise RuntimeError("Microsoft Graph configuration missing: "+", ".join(missing))
    r=client.post(f"https://login.microsoftonline.com/{settings.microsoft_tenant_id.strip()}/oauth2/v2.0/token",data={"client_id":settings.microsoft_client_id.strip(),"client_secret":settings.microsoft_client_secret.strip(),"scope":"https://graph.microsoft.com/.default","grant_type":"client_credentials"}); r.raise_for_status(); return r.json()["access_token"]

def _context(db,email,subject=""):
    # Match only previously sent outreach to this exact address. A shared mailbox
    # with multiple opportunities must have a matching subject; never pick the latest blindly.
    contacts=db.query(Contact).filter(func.lower(Contact.email)==email.lower()).all()
    ids=[c.id for c in contacts]
    drafts=db.query(OutreachDraft).filter(OutreachDraft.contact_id.in_(ids),
        OutreachDraft.status=='SENT').order_by(OutreachDraft.created_at.desc()).all() if ids else []
    needle=_norm_subject(subject)
    if needle:
        for d in drafts:
            ds=_norm_subject(d.subject)
            if ds and needle==ds:
                return d.opportunity_id,d.id
    if len({d.opportunity_id for d in drafts})==1:
        return drafts[0].opportunity_id,drafts[0].id
    return None,None

def _suggested_reply(response):
    name=(response.sender_name or "").strip().split(" ")[0]
    hello=f"Hello {name}," if name else "Hello,"
    if response.classification=="INTERESTED":
        middle="Thank you for your interest in VTAB Square. We would be happy to discuss your requirements and the most relevant next steps. Please share a convenient time for a short discussion."
    elif response.classification=="NEEDS_INFO":
        middle="Thank you for your response. We would be happy to provide the requested information. We will review your requirements and share the most relevant capability details for your consideration."
    elif response.classification=="FOLLOW_UP_LATER":
        middle="Thank you for letting us know. We will respect your timing and reconnect at the appropriate time."
    else:
        return ""
    return f"{hello}\n\n{middle}\n\nRegards,\nBusiness Development Team\nVTAB Square Private Limited"

def _make_followup(db,response):
    if not response.opportunity_id or response.classification not in {"INTERESTED","NEEDS_INFO","FOLLOW_UP_LATER"}: return
    exists=db.query(FollowUpTask).filter(FollowUpTask.response_id==response.id).first()
    if exists:return
    now=datetime.now(timezone.utc)
    due=now+timedelta(days=1 if response.classification in {"INTERESTED","NEEDS_INFO"} else 7)
    if response.classification=='FOLLOW_UP_LATER':
        text=response.body_text.lower()
        months=3 if 'next quarter' in text else 1 if 'next month' in text else 0
        if months:
            import calendar
            year=now.year+(now.month-1+months)//12;month=(now.month-1+months)%12+1
            due=now.replace(year=year,month=month,day=min(now.day,calendar.monthrange(year,month)[1]))
    db.add(FollowUpTask(opportunity_id=response.opportunity_id,outreach_draft_id=response.outreach_draft_id,response_id=response.id,status="PENDING",action_type="RESPOND" if response.classification in {"INTERESTED","NEEDS_INFO"} else "FOLLOW_UP",due_at=due,reason=response.suggested_action,draft_subject=f"Re: {response.subject}",draft_body=response.suggested_reply or _suggested_reply(response),human_approved=False))

def _apply_intelligence(db,response):
    oid,did=_context(db,response.sender_email,response.subject)
    result=classify_message(response.sender_email,response.subject,response.body_text,settings.microsoft_sender_email)
    response.opportunity_id=oid; response.outreach_draft_id=did
    for k,v in result.items(): setattr(response,k,v)
    response.suggested_reply=_suggested_reply(response)
    if oid and response.classification in QUALIFIED:
        from app.services.casebooks import record_inbound
        record_inbound(db,response)
        opportunity = db.get(Opportunity, oid)
        if opportunity and opportunity.pipeline_status not in {'WON','LOST','CLOSED'}:
            opportunity.pipeline_status = 'RESPONDED'
    if any(x in (response.body_text or '').lower() for x in ('unsubscribe','remove me','do not contact')):
        for contact in db.query(Contact).filter(func.lower(Contact.email)==response.sender_email.lower()).all():
            contact.do_not_contact=True
        if not db.query(Suppression).filter(func.lower(Suppression.email)==response.sender_email.lower()).first():
            db.add(Suppression(email=response.sender_email.lower(), reason='UNSUBSCRIBE'))


    # Reprocessing must also clean up stale AI-created follow-up recommendations.
    # It never sends, deletes or modifies an Outlook message.
    existing=db.query(FollowUpTask).filter(FollowUpTask.response_id==response.id).all()
    actionable=response.classification in {"INTERESTED","NEEDS_INFO","FOLLOW_UP_LATER"} and bool(response.opportunity_id)
    if not actionable:
        for task in existing:
            if task.status in {"PENDING","APPROVED"}:
                task.status="DISMISSED"
                task.human_approved=False
                task.reason=f"Suppressed by smart inbound reprocessing: {response.classification}."
    else:
        _make_followup(db,response)

def reprocess_existing(db):
    rows=db.query(InboundResponse).all(); counts={}; matched=0
    for x in rows:
        _apply_intelligence(db,x); counts[x.classification]=counts.get(x.classification,0)+1
        if x.opportunity_id:matched+=1
    db.commit()
    return {"status":"REPROCESSED","processed":len(rows),"matched":matched,"classifications":counts,"message":f"Reprocessed {len(rows)} inbox messages with smart filtering and outreach matching."}

def sync_inbox(db):
    mailbox=settings.microsoft_sender_email.strip()
    if not mailbox: raise RuntimeError('Configure the Microsoft sender mailbox before syncing.')
    state=db.query(MailSyncState).filter(MailSyncState.mailbox==mailbox).first()
    if not state: state=MailSyncState(mailbox=mailbox); db.add(state); db.commit(); db.refresh(state)
    with httpx.Client(timeout=httpx.Timeout(settings.graph_timeout_seconds)) as client:
        headers={"Authorization":f"Bearer {_token(client)}"}
        url=state.delta_link or f"https://graph.microsoft.com/v1.0/users/{__import__('urllib.parse',fromlist=['quote']).quote(mailbox,safe='')}/mailFolders/inbox/messages/delta?$select=id,internetMessageId,subject,from,receivedDateTime,body"
        processed=0; final_delta=None; counts={}
        while url:
            from urllib.parse import urlparse
            parsed=urlparse(url)
            if parsed.scheme!='https' or parsed.hostname!='graph.microsoft.com' or parsed.username or parsed.password:
                raise RuntimeError('Unexpected Microsoft Graph delta URL. Reset the mailbox sync cursor after review.')
            r=client.get(url,headers=headers); r.raise_for_status(); payload=r.json()
            for m in payload.get("value",[]):
                gid=m.get("id")
                if not gid or "@removed" in m or db.query(InboundResponse).filter(InboundResponse.graph_message_id==gid).first(): continue
                sender=((m.get("from") or {}).get("emailAddress") or {}); email=(sender.get("address") or "").strip()
                if not email: continue
                subject=m.get("subject") or "(No subject)"; body=_strip_html(((m.get("body") or {}).get("content") or ""))
                received_at=None
                if m.get("receivedDateTime"):
                    try: received_at=datetime.fromisoformat(m["receivedDateTime"].replace("Z", "+00:00"))
                    except ValueError: pass
                response=InboundResponse(graph_message_id=gid,internet_message_id=m.get("internetMessageId"),sender_name=sender.get("name"),sender_email=email,subject=subject,body_text=body,received_at=received_at)
                db.add(response); db.flush(); _apply_intelligence(db,response); counts[response.classification]=counts.get(response.classification,0)+1; processed+=1
            url=payload.get("@odata.nextLink"); final_delta=payload.get("@odata.deltaLink") or final_delta
        state.delta_link=final_delta or state.delta_link; state.last_synced_at=datetime.now(timezone.utc); state.last_error=None; db.commit()
    return {"status":"SYNCED","processed":processed,"classifications":counts,"mailbox":mailbox,"read_only":True,"demo_mode":settings.demo_mode,"message":f"Inbox sync completed. {processed} new message(s) imported and filtered. No email was sent or modified."}
