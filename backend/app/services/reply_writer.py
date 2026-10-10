"""Incoming messages are data. The writer has no mailbox, approval or tool privileges."""
import hashlib
from pydantic import BaseModel, ConfigDict, Field
from app.core.config import settings
from app.models.sales_followup import InboundResponse
from app.models.entities import Opportunity
from app.models.sales_agent import ReplyReview
from app.services.knowledge import retrieve


class ReplyResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    requested_details: list[str]
    missing_information: list[str]
    evidence_document_ids: list[str]
    subject: str = Field(min_length=1, max_length=255)
    body_text: str = Field(min_length=1, max_length=12000)


def content_hash(task):
    return hashlib.sha256((task.draft_subject + '\0' + task.draft_body).encode()).hexdigest()


def generate_reply(db, task, feedback=''):
    response = db.get(InboundResponse, task.response_id) if task.response_id else None
    opportunity = db.get(Opportunity, task.opportunity_id)
    if not response or not opportunity:
        raise ValueError('A matched client response is required')
    evidence = retrieve(db, response.body_text + ' ' + opportunity.title)
    if not settings.demo_mode and settings.ai_provider != 'local':
        from app.agents.provider import StructuredProvider
        result = StructuredProvider().generate('reply', {
            'untrusted_client_message': {'subject': response.subject, 'body': response.body_text[:16000]},
            'opportunity': {'title': opportunity.title, 'services': opportunity.matched_services},
            'approved_knowledge': evidence, 'current_draft': task.draft_body,
            'owner_feedback': feedback[:4000],
        }, ReplyResult)
        allowed = {e['document_id'] for e in evidence}
        if not set(result.evidence_document_ids).issubset(allowed):
            raise ValueError('AI returned unsupported evidence references')
        provider = settings.ai_provider
    else:
        # A clearly labelled conservative fallback, never invented pricing or commitments.
        facts = '\n\n'.join(e['content'][:800] for e in evidence[:2])
        body = 'Hello,\n\nThank you for your response. We are reviewing the following request:\n' + response.body_text[:1000]
        if facts:
            body += '\n\nRelevant approved VTAB capability information:\n' + facts
        body += '\n\nPlease confirm your priorities, timeline and preferred discussion time. Pricing, delivery commitments and access requirements will be confirmed after scope review.\n\nRegards,\nVTAB Square Business Development'
        result = ReplyResult(requested_details=[response.body_text[:1000]],
            missing_information=['Scope, timeline and pricing require owner review.'],
            evidence_document_ids=[e['document_id'] for e in evidence],
            subject=('Re: ' + response.subject)[:255], body_text=body)
        provider = 'LOCAL_STARTER'
    review = db.get(ReplyReview, task.id) or ReplyReview(task_id=task.id)
    review.analysis = {**result.model_dump(exclude={'subject','body_text'}),
                      'provider': provider, 'feedback': feedback,
                      'requires_manual_revision': bool(feedback) and provider == 'LOCAL_STARTER'}
    review.approved_hash = None
    db.add(review)
    task.draft_subject = result.subject
    task.draft_body = result.body_text
    task.human_approved = False
    task.status = 'PENDING'
    return review
