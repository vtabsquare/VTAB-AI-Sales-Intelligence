"""Additive intelligence records; existing customer tables are preserved."""
from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.db import Base
from app.models.entities import uid

class QualificationAssessment(Base):
    __tablename__ = 'qualification_assessments'
    opportunity_id: Mapped[str] = mapped_column(ForeignKey('opportunities.id'), primary_key=True)
    dimensions: Mapped[dict] = mapped_column(JSON)
    reasons: Mapped[list] = mapped_column(JSON)
    concerns: Mapped[list] = mapped_column(JSON)
    hard_rejections: Mapped[list] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DiscoveryOccurrence(Base):
    __tablename__ = 'discovery_occurrences'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey('opportunities.id'), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(255))
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class IntelligenceWorkflow(Base):
    __tablename__ = 'intelligence_workflows'
    opportunity_id: Mapped[str] = mapped_column(ForeignKey('opportunities.id'), primary_key=True)
    completed_steps: Mapped[list] = mapped_column(JSON, default=list)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default='READY')
    error: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class KnowledgeChunk(Base):
    __tablename__ = 'knowledge_chunks'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('knowledge_documents.id'), index=True)
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)

class CountryTarget(Base):
    __tablename__ = 'country_targets'
    name: Mapped[str] = mapped_column(String(120), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    language: Mapped[str] = mapped_column(String(40), default='en')
    timezone: Mapped[str] = mapped_column(String(100), default='UTC')
