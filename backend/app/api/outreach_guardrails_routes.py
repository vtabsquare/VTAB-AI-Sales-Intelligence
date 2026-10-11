from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db import get_db
from app.models.entities import Company, Contact, Opportunity, OutreachDraft, Suppression
from app.models.sales_agent import OrganizationResearch
from app.services.source_evidence import fetch_evidence

r = APIRouter(prefix="/api/outreach", tags=["outreach-guardrails"])


class HumanVerifyRequest(BaseModel):
    confirmation: bool
    evidence_note: str = Field(min_length=12, max_length=1000)


def _verified(status: str | None) -> bool:
    return (status or "").strip().upper() in {"VERIFIED", "HUMAN_VERIFIED"}


def _recipient_payload(contact: Contact | None):
    status = contact.email_verification_status if contact else None
    return {
        "name": contact.full_name if contact else None,
        "title": contact.title if contact else None,
        "email": contact.email if contact else None,
        "verification": status,
        "verified": _verified(status),
        "do_not_contact": bool(contact.do_not_contact) if contact else False,
        "source": "CONTACT_RECORD" if contact else None,
    }


@r.get("/send-center-v2")
def send_center_v2(db: Session = Depends(get_db)):
    rows = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.status == "APPROVED")
        .order_by(OutreachDraft.created_at.desc())
        .all()
    )
    items = []
    for draft in rows:
        opportunity = db.get(Opportunity, draft.opportunity_id)
        company = db.get(Company, opportunity.company_id) if opportunity and opportunity.company_id else None
        contact = db.get(Contact, draft.contact_id) if draft.contact_id else None
        recipient = _recipient_payload(contact)
        suppressed = False
        if contact and contact.email:
            suppressed = bool(
                db.query(Suppression)
                .filter(func.lower(Suppression.email) == contact.email.lower())
                .first()
            )
        send_allowed = bool(
            draft.status == "APPROVED"
            and contact
            and contact.email
            and recipient["verified"]
            and not contact.do_not_contact
            and not suppressed
        )
        research = db.get(OrganizationResearch, opportunity.id) if opportunity else None
        items.append({
            "id": draft.id,
            "opportunity_id": draft.opportunity_id,
            "contact_id": draft.contact_id,
            "subject": draft.subject,
            "body_text": draft.body_text,
            "status": draft.status,
            "created_at": draft.created_at,
            "human_approved": True,
            "send_allowed": send_allowed,
            "recipient": recipient,
            "opportunity": {
                "title": opportunity.title if opportunity else None,
                "country": opportunity.country if opportunity else None,
                "source_name": opportunity.source_name if opportunity else None,
                "source_url": opportunity.source_url if opportunity else None,
                "qualification_score": opportunity.qualification_score if opportunity else None,
            },
            "company": {
                "name": company.name if company else None,
                "website": company.website if company else None,
            },
            "evidence": {
                "status": research.evidence_status if research else None,
                "published_emails": research.published_emails if research else [],
                "published_phones": research.published_phones if research else [],
                "source_url": research.source_url if research else (opportunity.source_url if opportunity else None),
            },
            "blocked_reason": (
                "Recipient is suppressed" if suppressed else
                "Recipient is marked Do Not Contact" if contact and contact.do_not_contact else
                "Recipient email is missing" if not contact or not contact.email else
                "Recipient requires published-evidence verification" if not recipient["verified"] else
                None
            ),
        })
    return items


@r.post("/{draft_id}/human-verify-published-recipient")
def human_verify_published_recipient(
    draft_id: str,
    payload: HumanVerifyRequest,
    db: Session = Depends(get_db),
):
    if not payload.confirmation:
        raise HTTPException(409, "Explicit confirmation is required.")

    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        raise HTTPException(404, "Outreach draft not found")
    if draft.status not in {"WAITING_APPROVAL", "APPROVED"}:
        raise HTTPException(409, "Recipient verification is only allowed before delivery.")
    if not draft.contact_id:
        raise HTTPException(409, "Identify a recipient before verification.")

    contact = db.get(Contact, draft.contact_id)
    if not contact or not contact.email:
        raise HTTPException(409, "Recipient email is required.")
    if contact.do_not_contact:
        raise HTTPException(409, "Recipient is marked Do Not Contact.")
    if db.query(Suppression).filter(func.lower(Suppression.email) == contact.email.lower()).first():
        raise HTTPException(409, "Recipient is on the suppression list.")

    opportunity = db.get(Opportunity, draft.opportunity_id)
    if not opportunity:
        raise HTTPException(404, "Opportunity not found")

    research = db.get(OrganizationResearch, opportunity.id)
    published = [x.lower().strip() for x in (research.published_emails or [])] if research else []

    # Refresh published evidence from the source URL when the stored research row has no email evidence.
    if contact.email.lower().strip() not in published:
        evidence = fetch_evidence(opportunity.source_url)
        published = [x.lower().strip() for x in evidence.get("emails", [])]
        if research:
            research.published_emails = evidence.get("emails", [])
            research.published_phones = evidence.get("phones", [])
            research.evidence_status = evidence.get("status", research.evidence_status)

    # Demo fixtures use reserved domains and can only be verified while demo mode is active.
    is_demo_fixture = bool(settings.demo_mode and contact.email.lower().endswith("@example.com"))
    if contact.email.lower().strip() not in published and not is_demo_fixture:
        raise HTTPException(
            409,
            "The email is not present in published source evidence. Human verification cannot be granted."
        )

    contact.email_verification_status = "HUMAN_VERIFIED"
    db.commit()
    return {
        "success": True,
        "email": contact.email,
        "verification": "HUMAN_VERIFIED",
        "verified": True,
        "evidence_note": payload.evidence_note,
        "message": "Recipient verified against published evidence. Human approval is still required before delivery.",
    }


@r.get("/production-readiness")
def production_readiness():
    checks = {
        "demo_mode_disabled": not settings.demo_mode,
        "microsoft_sender_is_vtab": settings.microsoft_sender_email.lower().strip() == "contactsales@vtabsquare.com",
        "microsoft_graph_configured": bool(
            settings.microsoft_tenant_id.strip()
            and settings.microsoft_client_id.strip()
            and settings.microsoft_client_secret.strip()
            and settings.microsoft_sender_email.strip()
        ),
        "database_configured": bool(settings.database_url and "localhost/vtab_sales" not in settings.database_url),
        "jwt_configured": bool(settings.jwt_secret and len(settings.jwt_secret) >= 32),
        "login_configured": bool(settings.login_email and settings.login_password),
        "human_approval_required": True,
        "auto_initial_outreach_disabled_by_policy": True,
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "message": "Live mode should only be enabled after all readiness checks pass.",
    }
