from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db import Base


class WebSource(Base):
    __tablename__ = "web_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    country: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(120), default="open_web")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    scan_frequency_minutes: Mapped[int] = mapped_column(Integer, default=360)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class WebAgentRun(Base):
    __tablename__ = "web_agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("web_sources.id"), nullable=True)
    mission: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    current_url: Mapped[str | None] = mapped_column(String(1200))
    current_action: Mapped[str | None] = mapped_column(String(500))
    pages_visited: Mapped[int] = mapped_column(Integer, default=0)
    items_extracted: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_created: Mapped[int] = mapped_column(Integer, default=0)
    screenshots_json: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("web_agent_runs.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(30), default="info")
    phase: Mapped[str] = mapped_column(String(80), default="browser")
    action: Mapped[str] = mapped_column(String(300), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AgentApproval(Base):
    __tablename__ = "agent_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("web_agent_runs.id"), nullable=True)
    risk: Mapped[str] = mapped_column(String(20), default="amber")
    action_type: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
