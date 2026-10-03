import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.db import Base

def uid(): return str(uuid.uuid4())

class ServicePortfolio(Base):
    __tablename__='service_portfolios'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(255),index=True,unique=True)
    category:Mapped[str]=mapped_column(String(120),default='Digital Services')
    description:Mapped[str]=mapped_column(Text,default='')
    keywords:Mapped[list]=mapped_column(JSON,default=list)
    target_buyers:Mapped[list]=mapped_column(JSON,default=list)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class DiscoverySource(Base):
    __tablename__='discovery_sources'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(255),index=True)
    source_type:Mapped[str]=mapped_column(String(50),default='WEB_SEARCH')
    base_url:Mapped[str]=mapped_column(String(2048),default='')
    countries:Mapped[list]=mapped_column(JSON,default=list)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class ResourceLink(Base):
    __tablename__='resource_links'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    title:Mapped[str]=mapped_column(String(255),index=True)
    resource_type:Mapped[str]=mapped_column(String(100),default='PRESENTATION')
    url:Mapped[str]=mapped_column(Text)
    description:Mapped[str]=mapped_column(Text,default='')
    tags:Mapped[list]=mapped_column(JSON,default=list)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class EmailTemplate(Base):
    __tablename__='email_templates'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(255),index=True)
    subject:Mapped[str]=mapped_column(String(500))
    body_html:Mapped[str]=mapped_column(Text)
    purpose:Mapped[str]=mapped_column(String(100),default='OUTREACH')
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class CompanyAsset(Base):
    __tablename__='company_assets'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(255),index=True)
    asset_type:Mapped[str]=mapped_column(String(100),default='COMPANY_WEBSITE')
    url:Mapped[str]=mapped_column(Text)
    description:Mapped[str]=mapped_column(Text,default='')
    active:Mapped[bool]=mapped_column(Boolean,default=True)

class ScheduledWorkflow(Base):
    __tablename__='scheduled_workflows'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(255),index=True)
    action_type:Mapped[str]=mapped_column(String(100))
    interval_minutes:Mapped[int]=mapped_column(Integer,default=1440)
    timezone:Mapped[str]=mapped_column(String(100),default='Asia/Kolkata')
    run_at_time:Mapped[str]=mapped_column(String(5),default='09:00')
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    last_run_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    next_run_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    last_status:Mapped[str]=mapped_column(String(100),default='NEVER_RUN')
    last_result:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class WorkflowRunHistory(Base):
    __tablename__='workflow_run_history'
    id:Mapped[str]=mapped_column(String(64),primary_key=True,default=uid)
    workflow_id:Mapped[str]=mapped_column(String(64),ForeignKey('scheduled_workflows.id'),index=True)
    workflow_name:Mapped[str]=mapped_column(String(255))
    action_type:Mapped[str]=mapped_column(String(100))
    status:Mapped[str]=mapped_column(String(50),index=True)
    started_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
    finished_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    duration_ms:Mapped[int]=mapped_column(Integer,default=0)
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    error:Mapped[str]=mapped_column(Text,default='')

class AuthOtpChallenge(Base):
    __tablename__ = "auth_otp_challenges"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=uid
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True
    )

    otp_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )


class AuthSession(Base):
    """Opaque token fingerprints allow durable logout without storing bearer tokens."""
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
