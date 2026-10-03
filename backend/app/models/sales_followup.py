from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.db import Base

def utcnow(): return datetime.now(timezone.utc)

class MailSyncState(Base):
    __tablename__ = "mail_sync_states"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mailbox: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    delta_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

class InboundResponse(Base):
    __tablename__ = "inbound_responses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    graph_message_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    internet_message_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    outreach_draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_email: Mapped[str] = mapped_column(String(320), index=True)
    subject: Mapped[str] = mapped_column(String(1000))
    body_text: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classification: Mapped[str] = mapped_column(String(64), default="NEEDS_REVIEW", index=True)
    sentiment: Mapped[str] = mapped_column(String(32), default="NEUTRAL")
    summary: Mapped[str] = mapped_column(Text, default="")
    suggested_action: Mapped[str] = mapped_column(Text, default="")
    suggested_reply: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id: Mapped[str] = mapped_column(String(36), index=True)
    outreach_draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    response_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    action_type: Mapped[str] = mapped_column(String(64), default="FOLLOW_UP")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    draft_subject: Mapped[str] = mapped_column(String(1000), default="")
    draft_body: Mapped[str] = mapped_column(Text, default="")
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
