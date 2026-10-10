from datetime import date, datetime
import re
from pydantic import BaseModel, ConfigDict, Field
from app.core.config import settings
from app.models.entities import KnowledgeDocument
from app.models.intelligence import QualificationAssessment
from app.agents.provider import StructuredProvider

class Scores(BaseModel):
    model_config = ConfigDict(extra='forbid')
    technical_match: int = Field(ge=0, le=25)
    service_match: int = Field(ge=0, le=20)
    accessibility_score: int = Field(ge=0, le=15)
    geography_score: int = Field(ge=0, le=10)
    buyer_access_score: int = Field(ge=0, le=10)
    freshness_score: int = Field(ge=0, le=10)
    strategic_value_score: int = Field(ge=0, le=10)

class QualificationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dimensions: Scores
    matched_services: list[str]
    reasons: list[str]
    concerns: list[str]
    hard_rejections: list[str]
    confidence: int = Field(ge=0, le=100)

ALIASES = {'Power BI':['power bi','business intelligence','dashboard'], 'Microsoft Fabric':['fabric','onelake'], 'Databricks':['databricks','spark','lakehouse'], 'Data Engineering':['data engineering','etl','data platform'], 'AI Applications':['ai','automation'], 'Dynamics 365':['dynamics 365'], 'Power Platform':['power platform','power automate'], 'Custom Application Development':['application development','software development']}

def evaluate(db, opportunity):
    text = f'{opportunity.title} {opportunity.description}'.lower()
    docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.approved.is_(True)).all()
    if not settings.demo_mode: docs=[d for d in docs if d.category!='DEMO']
    approved = '\n'.join(d.content for d in docs).lower()
    matches = [name for name, terms in ALIASES.items() if any(re.search(r'(?<!\w)'+re.escape(t.strip())+r'(?!\w)',text) for t in terms) and name.lower() in approved]
    from app.models.platform import ServicePortfolio
    portfolio=db.query(ServicePortfolio).all()
    if portfolio:
        # Preserve canonical approved capabilities while honoring active catalog entries.
        active=[service for service in portfolio if service.active]
        enabled_known=set()
        for service in active:
            catalog=' '.join([service.name]+(service.keywords or [])).lower()
            names={name for name,terms in ALIASES.items() if any(re.search(r'\b'+re.escape(term.strip())+r'\b',catalog) for term in terms)}
            enabled_known.update(names)
            if not names and any(term.lower() in text and term.lower() in approved
                                 for term in [service.name]+(service.keywords or []) if len(term.strip())>=3):
                matches.append(service.name)
        matches=[name for name in matches if name in enabled_known or name not in ALIASES]
    hard = []
    if opportunity.closing_date and opportunity.closing_date < date.today(): hard.append('Deadline has passed.')
    for term, reason in [('hardware only','Hardware-only procurement.'), ('construction only','Construction-only procurement.'), ('local vendors only','Explicit local-vendor restriction requires eligibility review.'), ('pay to apply','Suspicious payment requirement.')]:
        if term in text: hard.append(reason)
    if not docs: hard.append('No approved knowledge is available to substantiate VTAB capabilities.')
    if hard or settings.demo_mode or settings.ai_provider == 'local':
        result = QualificationResult(dimensions=Scores(technical_match=min(25,10+5*len(matches)) if matches else 0, service_match=min(20,8+4*len(matches)) if matches else 0, accessibility_score=8, geography_score=6, buyer_access_score=5, freshness_score=10 if opportunity.closing_date and opportunity.closing_date >= date.today() else 4, strategic_value_score=6), matched_services=matches, reasons=[f'Requirement matches approved capabilities: {", ".join(matches)}.'], concerns=['Vendor eligibility, delivery feasibility and buyer channel require human verification.'], hard_rejections=[], confidence=65)
        provider = 'DEMO_RULES' if settings.demo_mode else 'LOCAL_RULES'
    else:
        result = StructuredProvider().generate('qualification', {'opportunity':{'title':opportunity.title,'description':opportunity.description,'country':opportunity.country,'closing_date':opportunity.closing_date,'source_url':opportunity.source_url},'supported_service_candidates':matches,'approved_knowledge':[{'title':d.title,'content':d.content} for d in docs]}, QualificationResult)
        # The model cannot authorize capability claims absent from approved knowledge.
        result.matched_services = [s for s in result.matched_services if s in matches]
        provider = settings.ai_provider
    hard += result.hard_rejections
    if not result.matched_services: hard.append('No supported approved VTAB capability match.')
    score = sum(result.dimensions.model_dump().values()) if not hard else 0
    status = 'REJECTED' if hard else ('QUALIFIED' if score >= settings.qualification_threshold else 'UNDER_REVIEW')
    opportunity.qualification_score=score; opportunity.qualification_status=status
    if opportunity.pipeline_status in {'DISCOVERED','UNDER_REVIEW','QUALIFIED','REJECTED'}: opportunity.pipeline_status=status
    opportunity.business_fit='HIGH' if score>=80 else ('MEDIUM' if score>=settings.qualification_threshold else 'LOW')
    opportunity.matched_services=result.matched_services
    opportunity.relevance_reason=' '.join(hard or result.reasons)
    row=db.get(QualificationAssessment, opportunity.id) or QualificationAssessment(opportunity_id=opportunity.id)
    row.dimensions=result.dimensions.model_dump();row.reasons=result.reasons;row.concerns=result.concerns;row.hard_rejections=hard;row.provider=provider;row.confidence=result.confidence;row.updated_at=datetime.utcnow()
    db.add(row);db.commit()
    return opportunity
