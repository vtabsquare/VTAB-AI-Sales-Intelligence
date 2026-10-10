"""Additive sales-manager state; existing production tables are not rewritten."""
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.db import Base
from app.models.entities import uid


class SalesAgentPolicy(Base):
    __tablename__ = 'sales_agent_policy'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default='default')
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_initial_outreach: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_acknowledge: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10)
    batch_size: Mapped[int] = mapped_column(Integer, default=10)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClientCasebook(Base):
    __tablename__ = 'client_casebooks'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'), unique=True)
    status: Mapped[str] = mapped_column(String(32), default='RESPONDED')
    owner_notes: Mapped[str] = mapped_column(Text, default='')
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CasebookEvent(Base):
    __tablename__ = 'casebook_events'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    casebook_id: Mapped[str] = mapped_column(ForeignKey('client_casebooks.id'), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey('opportunities.id'))
    event_key: Mapped[str] = mapped_column(String(255), unique=True)
    kind: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str] = mapped_column(String(1000), default='')
    body: Mapped[str] = mapped_column(Text, default='')
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReplyReview(Base):
    __tablename__ = 'reply_reviews'
    task_id: Mapped[str] = mapped_column(ForeignKey('follow_up_tasks.id'), primary_key=True)
    approved_hash: Mapped[str | None] = mapped_column(String(64))
    outreach_id: Mapped[str | None] = mapped_column(ForeignKey('outreach_drafts.id'))
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)


class WorkflowLease(Base):
    __tablename__ = 'workflow_leases'
    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class SalesOutbound(Base):
    __tablename__ = 'sales_outbound'
    draft_id: Mapped[str] = mapped_column(ForeignKey('outreach_drafts.id'), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32))
    response_id: Mapped[str | None] = mapped_column(ForeignKey('inbound_responses.id'), unique=True)


class DailySendQuota(Base):
    __tablename__ = 'daily_send_quota'
    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class OrganizationResearch(Base):
    __tablename__ = 'organization_research'
    opportunity_id: Mapped[str] = mapped_column(ForeignKey('opportunities.id'), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default='')
    published_emails: Mapped[list] = mapped_column(JSON, default=list)
    published_phones: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str] = mapped_column(String(2048))
    evidence_status: Mapped[str] = mapped_column(String(64))
    researched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiscoverySearchState(Base):
    __tablename__ = 'discovery_search_state'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default='global')
    query_offset: Mapped[int] = mapped_column(Integer, default=0)


class SchedulerHeartbeat(Base):
    __tablename__ = 'scheduler_heartbeat'
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default='scheduler')
    observed_at: Mapped[datetime] = mapped_column(DateTime)
