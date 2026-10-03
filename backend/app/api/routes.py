import os

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from sqlalchemy import func

from app.models.db import get_db
from app.core.config import settings

from app.models.entities import *

from app.schemas.api import OpportunityOut, DraftUpdate, ReplyIn, SendConfirmation

from app.services.engine import (

    discover,

    qualify,

    research,

    find_contact,

    draft,

    send,

)

from app.services.email_verification import (

    verify_email_address,

)

from typing import Optional

from pydantic import BaseModel, EmailStr

# ============================================================

# ROUTER

# ============================================================

r = APIRouter(prefix="/api")

def _app_environment() -> str:
    return settings.app_env.strip().lower()

def _is_development_environment() -> bool:
    return _app_environment() in {"development", "local", "test"}

def _is_email_verified(status: Optional[str]) -> bool:
    if status in {"VERIFIED", "HUMAN_VERIFIED"}:
        return True
    if status == "TEST_VERIFIED" and _is_development_environment() and settings.demo_mode:
        return True
    return False

# ============================================================

# RECIPIENT REQUEST / RESPONSE MODELS

# ============================================================

class RecipientUpdate(BaseModel):

    email: EmailStr

    name: Optional[str] = None

    title: Optional[str] = None

    source: Optional[str] = "MANUAL"

    confidence: Optional[int] = 100

class RecipientOut(BaseModel):

    outreach_id: str

    contact_id: Optional[str] = None

    name: Optional[str] = None

    title: Optional[str] = None

    email: Optional[str] = None

    source: Optional[str] = None

    confidence: Optional[int] = None

    verified: bool = False

# ============================================================

# HEALTH CHECK

# ============================================================

@r.get("/health")

def health():

    return {

        "status": "ok"

    }

# ============================================================

# OPPORTUNITY DISCOVERY

# ============================================================

@r.post(

    "/opportunities/discover",

    response_model=list[OpportunityOut]

)

def discovery(

    db: Session = Depends(get_db)

):

    from app.services.global_discovery import run_discovery
    run_discovery(db)
    return db.query(Opportunity).order_by(Opportunity.created_at.desc()).limit(200).all()

# ============================================================

# GET ALL OPPORTUNITIES

# ============================================================

@r.get(

    "/opportunities",

    response_model=list[OpportunityOut]

)

def opportunities(

    db: Session = Depends(get_db)

):

    return (

        db.query(Opportunity)

        .order_by(

            Opportunity.created_at.desc()

        )

        .all()

    )

# ============================================================

# INTERNAL OPPORTUNITY LOOKUP

# ============================================================

def opp(

    db: Session,

    id: str

):

    opportunity = db.get(

        Opportunity,

        id

    )

    if not opportunity:

        raise HTTPException(

            status_code=404,

            detail="Opportunity not found"

        )

    return opportunity

# ============================================================

# GET OPPORTUNITY DETAILS

# ============================================================

@r.get(

    "/opportunities/{id}",

    response_model=OpportunityOut

)

def detail(

    id: str,

    db: Session = Depends(get_db)

):

    return opp(

        db,

        id

    )

# ============================================================

# QUALIFY OPPORTUNITY

# ============================================================

@r.post(

    "/opportunities/{id}/qualify",

    response_model=OpportunityOut

)

def q(

    id: str,

    db: Session = Depends(get_db)

):

    opportunity = opp(

        db,

        id

    )

    return qualify(

        db,

        opportunity

    )

# ============================================================

# RESEARCH COMPANY

# ============================================================

@r.post(

    "/opportunities/{id}/research"

)

def rs(

    id: str,

    db: Session = Depends(get_db)

):

    opportunity = opp(

        db,

        id

    )

    return research(

        db,

        opportunity

    )

# ============================================================

# FIND CONTACT

# ============================================================

@r.post(

    "/opportunities/{id}/find-contact"

)

def fc(

    id: str,

    db: Session = Depends(get_db)

):

    opportunity = opp(

        db,

        id

    )

    contact = find_contact(

        db,

        opportunity

    )

    return {

        "id": contact.id,

        "name": contact.full_name,

        "title": contact.title,

        "email": contact.email,

        "verification":

            contact.email_verification_status,

    }

# ============================================================

# GENERATE OUTREACH

#

# IMPORTANT:

# Do not generate another WAITING_APPROVAL draft when one

# already exists for the same opportunity.

# ============================================================

@r.post(

    "/opportunities/{id}/generate-outreach"

)

def gd(

    id: str,

    db: Session = Depends(get_db)

):

    opportunity = opp(

        db,

        id

    )

    if opportunity.qualification_status != 'QUALIFIED':
        raise HTTPException(409, 'Qualify the opportunity before generating outreach.')

    # --------------------------------------------------------

    # Check for existing draft waiting for approval

    # --------------------------------------------------------

    existing_draft = (

        db.query(OutreachDraft)

        .filter(

            OutreachDraft.opportunity_id == id,

            OutreachDraft.status.in_(["WAITING_APPROVAL", "APPROVED", "SENDING"])

        )

        .order_by(

            OutreachDraft.created_at.desc()

        )

        .first()

    )

    # --------------------------------------------------------

    # Return existing draft instead of creating duplicate

    # --------------------------------------------------------

    if existing_draft:

        return {

            "id": existing_draft.id,

            "subject":

                existing_draft.subject,

            "body_text":

                existing_draft.body_text,

            "status":

                existing_draft.status,

            "existing": True,

            "message": (

                "An outreach draft is already "

                "waiting for approval."

            ),

        }

    # --------------------------------------------------------

    # Generate new outreach draft

    # --------------------------------------------------------

    new_draft = draft(

        db,

        opportunity

    )

    return {

        "id": new_draft.id,

        "subject": new_draft.subject,

        "body_text": new_draft.body_text,

        "status": new_draft.status,

        "existing": False,

        "message": (

            "Outreach draft generated and "

            "submitted for human approval."

        ),

    }

# ============================================================

# APPROVAL QUEUE

# ============================================================

@r.get(

    "/outreach/approval-queue"

)

def queue(

    db: Session = Depends(get_db)

):

    drafts = (

        db.query(OutreachDraft)

        .filter(

            OutreachDraft.status

            == "WAITING_APPROVAL"

        )

        .order_by(

            OutreachDraft.created_at.desc()

        )

        .all()

    )

    return [

        {

            "id": d.id,

            "opportunity_id":

                d.opportunity_id,

            "contact_id":

                d.contact_id,

            "subject":

                d.subject,

            "body_text":

                d.body_text,

            "status":

                d.status,

            "created_at":

                d.created_at,

        }

        for d in drafts

    ]

# ============================================================

# EDIT OUTREACH DRAFT

# ============================================================

@r.patch(

    "/outreach/{id}"

)

def edit(

    id: str,

    p: DraftUpdate,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    # --------------------------------------------------------

    # Only WAITING_APPROVAL drafts can be edited

    # --------------------------------------------------------

    if (

        outreach_draft.status

        != "WAITING_APPROVAL"

    ):

        raise HTTPException(

            status_code=409,

            detail=(

                "Only drafts awaiting approval "

                "can be edited"

            )

        )

    # --------------------------------------------------------

    # Update subject

    # --------------------------------------------------------

    if p.subject is not None:

        subject = p.subject.strip()

        if not subject:

            raise HTTPException(

                status_code=400,

                detail="Subject cannot be empty"

            )

        outreach_draft.subject = subject

    # --------------------------------------------------------

    # Update email body

    # --------------------------------------------------------

    if p.body_text is not None:

        body = p.body_text.strip()

        if not body:

            raise HTTPException(

                status_code=400,

                detail="Email body cannot be empty"

            )

        outreach_draft.body_text = body

    # --------------------------------------------------------

    # Save

    # --------------------------------------------------------

    db.commit()

    db.refresh(

        outreach_draft

    )

    return {

        "id":

            outreach_draft.id,

        "opportunity_id":

            outreach_draft.opportunity_id,

        "subject":

            outreach_draft.subject,

        "body_text":

            outreach_draft.body_text,

        "status":

            outreach_draft.status,

        "message": (

            "Draft updated successfully. "

            "Human approval is still required."

        ),

    }

# ============================================================

# APPROVE OUTREACH

#

# Approval does NOT send email.

# ============================================================

@r.post(

    "/outreach/{id}/approve"

)

def approve(

    id: str,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    # --------------------------------------------------------

    # Only WAITING_APPROVAL can become APPROVED

    # --------------------------------------------------------

    if (

        outreach_draft.status

        != "WAITING_APPROVAL"

    ):

        raise HTTPException(

            status_code=409,

            detail=(

                "Draft cannot be approved from "

                f"status {outreach_draft.status}"

            )

        )

    # --------------------------------------------------------

    # Human approval

    # --------------------------------------------------------

    outreach_draft.status = "APPROVED"

    db.commit()

    db.refresh(

        outreach_draft

    )

    return {

        "id":

            outreach_draft.id,

        "opportunity_id":

            outreach_draft.opportunity_id,

        "status":

            outreach_draft.status,

        "message": (

            "Outreach approved successfully. "

            "No email has been sent."

        ),

    }

# ============================================================

# REJECT OUTREACH

# ============================================================

@r.post(

    "/outreach/{id}/reject"

)

def reject(

    id: str,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    # --------------------------------------------------------

    # Only WAITING_APPROVAL drafts can be rejected

    # --------------------------------------------------------

    if (

        outreach_draft.status

        != "WAITING_APPROVAL"

    ):

        raise HTTPException(

            status_code=409,

            detail=(

                "Draft cannot be rejected from "

                f"status {outreach_draft.status}"

            )

        )

    outreach_draft.status = "REJECTED"

    db.commit()

    db.refresh(

        outreach_draft

    )

    return {

        "id":

            outreach_draft.id,

        "opportunity_id":

            outreach_draft.opportunity_id,

        "status":

            outreach_draft.status,

        "message":

            "Outreach draft rejected successfully.",

    }

# ============================================================

# APPROVED OUTREACH / SEND CENTER

#

# IMPORTANT:

# This endpoint does NOT send anything.

#

# It now also resolves recipient information so the frontend

# can determine whether an approved message is ready to send.

# ============================================================

@r.get(

    "/outreach/send-center"

)

def send_center(

    db: Session = Depends(get_db)

):

    approved_drafts = (

        db.query(OutreachDraft)

        .filter(

            OutreachDraft.status

            == "APPROVED"

        )

        .order_by(

            OutreachDraft.created_at.desc()

        )

        .all()

    )

    results = []

    for d in approved_drafts:

        contact = None

        if d.contact_id:

            contact = db.get(

                Contact,

                d.contact_id

            )

        recipient_email = (

            contact.email

            if contact

            else None

        )

        verification_status = (

            contact.email_verification_status

            if contact

            else None

        )

        # ----------------------------------------------------

        # IMPORTANT:

        # Email existence and email verification are separate.

        # ----------------------------------------------------

        verified = _is_email_verified(verification_status)

        results.append(

            {

                "id": d.id,

                "opportunity_id":

                    d.opportunity_id,

                "contact_id":

                    d.contact_id,

                "subject":

                    d.subject,

                "body_text":

                    d.body_text,

                "status":

                    d.status,

                "created_at":

                    d.created_at,

                "human_approved":

                    True,

                "send_allowed": (

                    bool(recipient_email)

                    and verified

                    and not (

                        contact.do_not_contact

                        if contact

                        else False

                    )

                ),

                # --------------------------------------------

                # Nested recipient object

                # --------------------------------------------

                "recipient": {

                    "name": (

                        contact.full_name

                        if contact

                        else None

                    ),

                    "title": (

                        contact.title

                        if contact

                        else None

                    ),

                    "email":

                        recipient_email,

                    "verification":

                        verification_status,

                    "verified":

                        verified,

                    "do_not_contact": (

                        contact.do_not_contact

                        if contact

                        else False

                    ),

                    "source":

                        "CONTACT_RECORD"

                        if contact

                        else None,

                },

                # --------------------------------------------

                # Flat fields for compatibility with the

                # newer SendCenterClient frontend.

                # --------------------------------------------

                "recipient_name": (

                    contact.full_name

                    if contact

                    else None

                ),

                "recipient_title": (

                    contact.title

                    if contact

                    else None

                ),

                "recipient_email":

                    recipient_email,

                "recipient_source": (

                    "CONTACT_RECORD"

                    if contact

                    else None

                ),

                "recipient_verified":

                    verified,

            }

        )

    return results

# ============================================================

# GET SINGLE OUTREACH DRAFT

# ============================================================

@r.get("/outreach/provider-status")
def outbound_provider_status():
    configured = all(
        [
            settings.microsoft_tenant_id.strip(),
            settings.microsoft_client_id.strip(),
            settings.microsoft_client_secret.strip(),
            settings.microsoft_sender_email.strip(),
        ]
    )

    return {
        "app_env": settings.app_env,
        "demo_mode": settings.demo_mode,
        "provider": (
            "DEMO"
            if settings.demo_mode
            else "MICROSOFT_GRAPH"
        ),
        "configured": (
            True
            if settings.demo_mode
            else configured
        ),
        "sender": (
            settings.microsoft_sender_email
            if settings.microsoft_sender_email
            else None
        ),
        "live_send_enabled": (
            (not settings.demo_mode)
            and configured
        ),
    }


# ============================================================

# SEND OUTREACH

#

# SAFETY GATES:

#

# 1. Draft must exist

# 2. Human approval required

# 3. Contact required

# 4. Email required

# 5. Contact must not be suppressed

# 6. Email must be VERIFIED

#

# Only after these checks do we call the existing send()

# service.

# ============================================================


@r.get(

    "/outreach/{id}"

)

def get_outreach(

    id: str,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    contact = None

    if outreach_draft.contact_id:

        contact = db.get(

            Contact,

            outreach_draft.contact_id

        )

    recipient_email = (

        contact.email

        if contact

        else None

    )

    verification_status = (

        contact.email_verification_status

        if contact

        else None

    )

    verified = _is_email_verified(verification_status)

    return {

        "id":

            outreach_draft.id,

        "opportunity_id":

            outreach_draft.opportunity_id,

        "contact_id":

            outreach_draft.contact_id,

        "subject":

            outreach_draft.subject,

        "body_text":

            outreach_draft.body_text,

        "status":

            outreach_draft.status,

        "created_at":

            outreach_draft.created_at,

        "human_approved": (

            outreach_draft.status

            == "APPROVED"

        ),

        "send_allowed": (

            outreach_draft.status

            == "APPROVED"

            and bool(recipient_email)

            and verified

            and not (

                contact.do_not_contact

                if contact

                else False

            )

        ),

        "recipient": {

            "name": (

                contact.full_name

                if contact

                else None

            ),

            "title": (

                contact.title

                if contact

                else None

            ),

            "email":

                recipient_email,

            "verification":

                verification_status,

            "verified":

                verified,

            "do_not_contact": (

                contact.do_not_contact

                if contact

                else False

            ),

        },

    }

# ============================================================

# GET OUTREACH RECIPIENT

# ============================================================

@r.get(

    "/outreach/{id}/recipient",

    response_model=RecipientOut

)

def get_outreach_recipient(

    id: str,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    # --------------------------------------------------------

    # No contact currently attached

    # --------------------------------------------------------

    if not outreach_draft.contact_id:

        return RecipientOut(

            outreach_id=id,

            contact_id=None,

            name=None,

            title=None,

            email=None,

            source=None,

            confidence=None,

            verified=False,

        )

    contact = db.get(

        Contact,

        outreach_draft.contact_id

    )

    if not contact:

        return RecipientOut(

            outreach_id=id,

            contact_id=

                outreach_draft.contact_id,

            name=None,

            title=None,

            email=None,

            source=None,

            confidence=None,

            verified=False,

        )

    return RecipientOut(

        outreach_id=id,

        contact_id=contact.id,

        name=contact.full_name,

        title=contact.title,

        email=contact.email,

        source="CONTACT_RECORD",

        confidence=None,

        verified=_is_email_verified(contact.email_verification_status),

    )

# ============================================================

# MANUALLY ASSIGN / UPDATE RECIPIENT

#

# IMPORTANT:

# Manual entry does NOT automatically mean that an email

# address has been independently verified.

# ============================================================

@r.patch(

    "/outreach/{id}/recipient"

)

def update_outreach_recipient(

    id: str,

    payload: RecipientUpdate,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    # --------------------------------------------------------

    # Recipient may only be changed during controlled stages.

    # --------------------------------------------------------

    if outreach_draft.status not in [

        "WAITING_APPROVAL",

        "APPROVED",

    ]:

        raise HTTPException(

            status_code=409,

            detail=(

                "Recipient cannot be changed "

                f"while outreach status is "

                f"{outreach_draft.status}"

            )

        )

    opportunity = db.get(

        Opportunity,

        outreach_draft.opportunity_id

    )

    if not opportunity:

        raise HTTPException(

            status_code=404,

            detail="Opportunity not found"

        )

    # --------------------------------------------------------

    # Reuse existing contact if draft already has one.

    # --------------------------------------------------------

    contact = None

    if outreach_draft.contact_id:

        contact = db.get(

            Contact,

            outreach_draft.contact_id

        )

    # --------------------------------------------------------

    # Otherwise create a contact using the opportunity's

    # company.

    # --------------------------------------------------------

    if not contact:

        if not opportunity.company_id:

            raise HTTPException(

                status_code=409,

                detail=(

                    "The opportunity has no company. "

                    "A recipient cannot be created "

                    "until a company is associated "

                    "with the opportunity."

                )

            )

        contact = Contact(

            company_id=

                opportunity.company_id,

            full_name=(

                payload.name.strip()

                if payload.name

                else "Business Contact"

            ),

            title=(

                payload.title.strip()

                if payload.title

                else "Business Contact"

            ),

            email=

                str(payload.email),

            # --------------------------------------------

            # Manual entry is not automatically VERIFIED.

            # --------------------------------------------

            email_verification_status=

                "MANUAL_REVIEW",

            do_not_contact=False,

        )

        db.add(contact)

        db.flush()

        outreach_draft.contact_id = (

            contact.id

        )

    else:

        # ----------------------------------------------------

        # Update existing contact

        # ----------------------------------------------------

        if payload.name is not None:

            name = payload.name.strip()

            if name:

                contact.full_name = name

        if payload.title is not None:

            title = payload.title.strip()

            if title:

                contact.title = title

        contact.email = str(

            payload.email

        )

        # ----------------------------------------------------

        # Changing the email invalidates prior verification.

        # ----------------------------------------------------

        contact.email_verification_status = (

            "MANUAL_REVIEW"

        )

    db.commit()

    db.refresh(contact)

    db.refresh(

        outreach_draft

    )

    return {

        "success": True,

        "message": (

            "Recipient saved successfully. "

            "The email address still requires "

            "verification before sending."

        ),

        "outreach_id":

            outreach_draft.id,

        "contact_id":

            contact.id,

        "recipient": {

            "name":

                contact.full_name,

            "title":

                contact.title,

            "email":

                contact.email,

            "source":

                payload.source,

            "confidence":

                payload.confidence,

            "verification":

                contact.email_verification_status,

            "verified":

                False,

        },

    }

# ============================================================

# RESOLVE RECIPIENT

#

# Resolution order:

#

# 1. Existing contact already attached to draft

# 2. Existing contact belonging to opportunity company

# 3. No match -> manual/external discovery required

#

# This endpoint does NOT scrape websites and does NOT guess

# email addresses.

# ============================================================

@r.post(

    "/outreach/{id}/resolve-recipient"

)

def resolve_recipient(

    id: str,

    db: Session = Depends(get_db)

):

    outreach_draft = db.get(

        OutreachDraft,

        id

    )

    if not outreach_draft:

        raise HTTPException(

            status_code=404,

            detail="Outreach draft not found"

        )

    opportunity = db.get(

        Opportunity,

        outreach_draft.opportunity_id

    )

    if not opportunity:

        raise HTTPException(

            status_code=404,

            detail="Opportunity not found"

        )

    # --------------------------------------------------------

    # STEP 1:

    # Check contact already attached to outreach draft.

    # --------------------------------------------------------

    if outreach_draft.contact_id:

        existing_contact = db.get(

            Contact,

            outreach_draft.contact_id

        )

        if (

            existing_contact

            and existing_contact.email

            and not existing_contact.do_not_contact

        ):

            verification_status = (

                existing_contact

                .email_verification_status

            )

            return {

                "success": True,

                "resolved": True,

                "method":

                    "EXISTING_CONTACT",

                "contact_id":

                    existing_contact.id,

                "name":

                    existing_contact.full_name,

                "title":

                    existing_contact.title,

                "email":

                    existing_contact.email,

                "source":

                    "CONTACT_RECORD",

                "verification":

                    verification_status,

                "verified": _is_email_verified(verification_status),

                "do_not_contact":

                    existing_contact.do_not_contact,

            }

    # --------------------------------------------------------

    # STEP 2:

    # Search contacts associated with the same company.

    # --------------------------------------------------------

    if opportunity.company_id:

        company_contacts = (

            db.query(Contact)

            .filter(

                Contact.company_id

                == opportunity.company_id,

                Contact.email.isnot(None),

                Contact.do_not_contact

                == False,

            )

            .all()

        )

        # ----------------------------------------------------

        # Prefer VERIFIED contact

        # ----------------------------------------------------

        selected_contact = None

        for candidate in company_contacts:

            if _is_email_verified(candidate.email_verification_status):

                selected_contact = candidate

                break

        # ----------------------------------------------------

        # Otherwise use first available contact, but sending

        # will remain blocked until verification.

        # ----------------------------------------------------

        if (

            selected_contact is None

            and company_contacts

        ):

            selected_contact = (

                company_contacts[0]

            )

        if selected_contact:

            outreach_draft.contact_id = (

                selected_contact.id

            )

            db.commit()

            db.refresh(

                outreach_draft

            )

            verification_status = (

                selected_contact

                .email_verification_status

            )

            return {

                "success": True,

                "resolved": True,

                "method":

                    "COMPANY_CONTACT",

                "contact_id":

                    selected_contact.id,

                "name":

                    selected_contact.full_name,

                "title":

                    selected_contact.title,

                "email":

                    selected_contact.email,

                "source":

                    "COMPANY_CONTACT_RECORD",

                "verification":

                    verification_status,

                "verified": _is_email_verified(verification_status),

                "do_not_contact":

                    selected_contact.do_not_contact,

            }

    # --------------------------------------------------------

    # STEP 3:

    # Nothing reliable was found.

    # --------------------------------------------------------

    return {

        "success": True,

        "resolved": False,

        "method":

            "NO_CONTACT_FOUND",

        "contact_id":

            None,

        "name":

            None,

        "title":

            None,

        "email":

            None,

        "source":

            None,

        "verification":

            None,

        "verified":

            False,

        "message": (

            "No usable recipient was found. "

            "Manual recipient entry or external "

            "contact discovery is required."

        ),

    }

# ============================================================
# VERIFY OUTREACH RECIPIENT EMAIL
# ============================================================

@r.post("/outreach/{id}/verify-recipient")
def verify_outreach_recipient(id: str, db: Session = Depends(get_db)):
    outreach_draft = db.get(OutreachDraft, id)
    if not outreach_draft:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if not outreach_draft.contact_id:
        raise HTTPException(status_code=409, detail="Recipient must be identified before email verification.")

    contact = db.get(Contact, outreach_draft.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Recipient contact not found")
    if not contact.email:
        raise HTTPException(status_code=409, detail="Recipient does not have an email address.")
    if contact.do_not_contact:
        raise HTTPException(status_code=409, detail="Recipient is marked Do Not Contact.")

    result = verify_email_address(contact.email)
    if result.get("normalized_email"):
        contact.email = result["normalized_email"]

    status = result.get("status", "INVALID")
    contact.email_verification_status = status
    db.commit()
    db.refresh(contact)

    verified = _is_email_verified(contact.email_verification_status)
    return {
        "success": status == "DOMAIN_VALID" or verified,
        "outreach_id": outreach_draft.id,
        "contact_id": contact.id,
        "email": contact.email,
        "verification": contact.email_verification_status,
        "verified": verified,
        "send_eligible": verified,
        "syntax_valid": result.get("syntax_valid", False),
        "domain_valid": result.get("domain_valid", False),
        "mx_found": result.get("mx_found", False),
        "mx_hosts": result.get("mx_hosts", []),
        "message": result.get("message"),
    }

# ============================================================
# TEST-ONLY RECIPIENT VERIFICATION
# ============================================================

@r.post("/outreach/{id}/test-verify-recipient")
def test_verify_outreach_recipient(id: str, db: Session = Depends(get_db)):
    if not _is_development_environment():
        raise HTTPException(status_code=403, detail="Test verification is disabled outside development environments.")

    outreach_draft = db.get(OutreachDraft, id)
    if not outreach_draft:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if not outreach_draft.contact_id:
        raise HTTPException(status_code=409, detail="Recipient must be identified first.")

    contact = db.get(Contact, outreach_draft.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Recipient contact not found")
    if not contact.email:
        raise HTTPException(status_code=409, detail="Recipient email is required.")
    if contact.do_not_contact:
        raise HTTPException(status_code=409, detail="Recipient is marked Do Not Contact.")

    suppressed = db.query(Suppression).filter(
        func.lower(Suppression.email) == contact.email.lower()
    ).first()
    if suppressed:
        raise HTTPException(status_code=409, detail="This recipient is present in the suppression list.")

    contact.email_verification_status = "TEST_VERIFIED"
    db.commit()
    db.refresh(contact)

    return {
        "success": True,
        "outreach_id": outreach_draft.id,
        "contact_id": contact.id,
        "email": contact.email,
        "verification": "TEST_VERIFIED",
        "verified": True,
        "send_eligible": True,
        "test_mode": True,
        "message": "Recipient marked TEST_VERIFIED for local development only.",
    }


# ============================================================
# OUTBOUND EMAIL PROVIDER STATUS
# ============================================================

@r.post("/outreach/{id}/send")
def snd(id: str, confirmation: SendConfirmation = SendConfirmation(), db: Session = Depends(get_db)):
    outreach_draft = db.get(OutreachDraft, id)
    if not outreach_draft:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if outreach_draft.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Human approval is required before sending outreach.")
    if not outreach_draft.contact_id:
        raise HTTPException(status_code=409, detail="Recipient must be identified before sending outreach.")

    contact = db.get(Contact, outreach_draft.contact_id)
    if not contact:
        raise HTTPException(status_code=409, detail="Recipient contact record does not exist.")
    if contact.do_not_contact:
        raise HTTPException(status_code=409, detail="This recipient is marked Do Not Contact.")
    if not contact.email:
        raise HTTPException(status_code=409, detail="Recipient email address is required before sending.")

    suppressed = db.query(Suppression).filter(
        func.lower(Suppression.email) == contact.email.lower()
    ).first()
    if suppressed:
        raise HTTPException(status_code=409, detail="This recipient is present in the suppression list.")

    if not _is_email_verified(contact.email_verification_status):
        raise HTTPException(
            status_code=409,
            detail=(
                "Recipient email must be verified before sending outreach. "
                f"Current verification status: {contact.email_verification_status}"
            ),
        )

    if not confirmation.confirmed:
        raise HTTPException(409, 'Explicit final send confirmation is required.')
    try:
        return send(db, outreach_draft)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

# ============================================================

# SIMULATE INBOUND RESPONSE

# ============================================================

@r.post(

    "/responses/simulate"

)

def reply(

    p: ReplyIn,

    db: Session = Depends(get_db)

):

    text = p.body.lower()

    # --------------------------------------------------------

    # Classify response

    # --------------------------------------------------------

    if any(

        phrase in text

        for phrase in [

            "unsubscribe",

            "do not contact",

            "remove me",

        ]

    ):

        response_type = "UNSUBSCRIBE"

    elif "meeting" in text:

        response_type = (

            "MEETING_REQUEST"

        )

    elif any(

        phrase in text

        for phrase in [

            "interested",

            "more information",

        ]

    ):

        response_type = "INTERESTED"

    else:

        response_type = "OTHER"

    # --------------------------------------------------------

    # Store inbound communication

    # --------------------------------------------------------

    communication = Communication(

        opportunity_id=

            p.opportunity_id,

        direction=

            "INBOUND",

        subject=

            p.subject,

        body=

            p.body,

        status=

            "RECEIVED",

    )

    db.add(

        communication

    )

    # --------------------------------------------------------

    # Update opportunity pipeline

    # --------------------------------------------------------

    opportunity = opp(

        db,

        p.opportunity_id

    )

    opportunity.pipeline_status = (

        "RESPONDED"

    )

    # --------------------------------------------------------

    # UNSUBSCRIBE:

    # Add known recipient to suppression list.

    # --------------------------------------------------------

    if response_type == "UNSUBSCRIBE":

        latest_draft = (

            db.query(OutreachDraft)

            .filter(

                OutreachDraft.opportunity_id

                == p.opportunity_id

            )

            .order_by(

                OutreachDraft.created_at.desc()

            )

            .first()

        )

        if (

            latest_draft

            and latest_draft.contact_id

        ):

            contact = db.get(

                Contact,

                latest_draft.contact_id

            )

            if contact:

                contact.do_not_contact = True

                if contact.email:

                    existing_suppression = (

                        db.query(Suppression)

                        .filter(

                            func.lower(

                                Suppression.email

                            )

                            == contact.email.lower()

                        )

                        .first()

                    )

                    if not existing_suppression:

                        db.add(

                            Suppression(

                                email=

                                    contact.email,

                                reason=

                                    "UNSUBSCRIBE",

                            )

                        )

    db.commit()

    # --------------------------------------------------------

    # Recommended action

    # --------------------------------------------------------

    if (

        response_type

        == "UNSUBSCRIBE"

    ):

        recommended_action = (

            "STOP_CONTACT"

        )

    else:

        recommended_action = (

            "HUMAN_REVIEW"

        )

    return {

        "response_type":

            response_type,

        "summary":

            p.body[:160],

        "recommended_action":

            recommended_action,

    }

# ============================================================

# DASHBOARD

# ============================================================

@r.get(

    "/dashboard"

)

def dashboard(

    db: Session = Depends(get_db)

):

    total = (

        db.query(

            func.count(

                Opportunity.id

            )

        )

        .scalar()

    )

    qualified = (

        db.query(

            func.count(

                Opportunity.id

            )

        )

        .filter(

            Opportunity.qualification_status

            == "QUALIFIED"

        )

        .scalar()

    )

    waiting = (

        db.query(

            func.count(

                OutreachDraft.id

            )

        )

        .filter(

            OutreachDraft.status

            == "WAITING_APPROVAL"

        )

        .scalar()

    )

    approved = (

        db.query(

            func.count(

                OutreachDraft.id

            )

        )

        .filter(

            OutreachDraft.status

            == "APPROVED"

        )

        .scalar()

    )

    sent = (

        db.query(

            func.count(

                OutreachDraft.id

            )

        )

        .filter(

            OutreachDraft.status

            == "SENT"

        )

        .scalar()

    )

    rejected = (

        db.query(

            func.count(

                OutreachDraft.id

            )

        )

        .filter(

            OutreachDraft.status

            == "REJECTED"

        )

        .scalar()

    )

    agent_runs = (

        db.query(

            func.count(

                AgentRun.id

            )

        )

        .scalar()

    )

    return {

        "demo_mode": settings.demo_mode,

        "opportunities":

            total,

        "qualified":

            qualified,

        "waiting_approval":

            waiting,

        "approved":

            approved,

        "sent":

            sent,

        "rejected":

            rejected,

        "agent_runs":

            agent_runs,

    }

# ============================================================

# AI AGENT RUN LOGS

# ============================================================

@r.get(

    "/agent-runs"

)

def runs(

    db: Session = Depends(get_db)

):

    agent_runs = (

        db.query(AgentRun)

        .order_by(

            AgentRun.created_at.desc()

        )

        .limit(100)

        .all()

    )

    return [

        {

            "id":

                x.id,

            "agent_name":

                x.agent_name,

            "status":

                x.status,

            "created_at":

                x.created_at,

        }

        for x in agent_runs

    ]

class RecipientEvidence(BaseModel):
    evidence: str
    confirmed: bool = False

@r.post('/outreach/{id}/confirm-recipient-evidence')
def confirm_recipient_evidence(id:str, payload:RecipientEvidence, db:Session=Depends(get_db)):
    """Explicit human review of source evidence; does not claim SMTP/mailbox delivery proof."""
    from email_validator import validate_email, EmailNotValidError
    from app.services.engine import log
    draft=db.get(OutreachDraft,id)
    if not draft: raise HTTPException(404,'Outreach draft not found')
    if draft.status not in {'WAITING_APPROVAL','APPROVED'}: raise HTTPException(409,'Recipient evidence can only be reviewed before sending')
    contact=db.get(Contact,draft.contact_id) if draft.contact_id else None
    if not contact or not contact.email: raise HTTPException(409,'Save an evidence-backed recipient first')
    if contact.do_not_contact or db.query(Suppression).filter(func.lower(Suppression.email)==contact.email.lower()).first(): raise HTTPException(409,'Recipient is suppressed')
    if not payload.confirmed or len(payload.evidence.strip())<20 or len(payload.evidence)>2000:
        raise HTTPException(422,'Explicit confirmation and a source/reference note of 20–2000 characters are required')
    try: validate_email(contact.email,check_deliverability=False)
    except EmailNotValidError: raise HTTPException(422,'Recipient address has invalid syntax')
    contact.email_verification_status='HUMAN_VERIFIED';db.commit()
    log(db,'Human Recipient Evidence Review',{'outreach_id':id,'contact_id':contact.id},
        {'verification':'HUMAN_VERIFIED','evidence':payload.evidence.strip(),'delivery_proof':False})
    return {'status':'HUMAN_VERIFIED','verified':True,'message':'Human source-evidence review recorded. This does not prove mailbox deliverability. Approval and final send confirmation remain required.'}
