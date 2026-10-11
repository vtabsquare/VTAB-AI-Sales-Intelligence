from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.models.web_agent import AgentActivity, AgentApproval, WebAgentRun, WebSource
from app.services.web_agent import browse_source, dashboard

r = APIRouter(prefix="/api/web-agent", tags=["web-agent"])


class SourceCreate(BaseModel):
    name: str
    url: str
    country: Optional[str] = None
    category: str = "open_web"
    auth_required: bool = False
    scan_frequency_minutes: int = Field(default=360, ge=15, le=10080)
    priority: int = Field(default=50, ge=0, le=100)


class RunRequest(BaseModel):
    source_id: int
    mission: str = "Discover global opportunities matching VTAB Square services"
    keywords: list[str] | None = None


class ApprovalDecision(BaseModel):
    decision: str


@r.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    return dashboard(db)


@r.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(WebSource).order_by(WebSource.priority.desc(), WebSource.id.desc()).all()
    return [{
        "id": x.id, "name": x.name, "url": x.url, "country": x.country,
        "category": x.category, "enabled": x.enabled, "trusted": x.trusted,
        "auth_required": x.auth_required, "priority": x.priority,
        "scan_frequency_minutes": x.scan_frequency_minutes,
        "success_rate": x.success_rate, "opportunities_found": x.opportunities_found,
        "failure_count": x.failure_count,
        "last_scan_at": x.last_scan_at, "next_scan_at": x.next_scan_at,
    } for x in rows]


@r.post("/sources")
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    if db.query(WebSource).filter(WebSource.url == payload.url).first():
        raise HTTPException(status_code=409, detail="Source already exists")
    row = WebSource(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "status": "created"}


@r.post("/sources/{source_id}/toggle")
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    row = db.get(WebSource, source_id)
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    row.enabled = not row.enabled
    db.commit()
    return {"id": row.id, "enabled": row.enabled}


@r.post("/run")
def start_run(payload: RunRequest, db: Session = Depends(get_db)):
    source = db.get(WebSource, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    result = asyncio.run(browse_source(db, source, payload.mission, payload.keywords))
    return result


@r.get("/runs")
def list_runs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(WebAgentRun).order_by(WebAgentRun.id.desc()).limit(min(limit, 200)).all()
    return [{
        "id": x.id, "source_id": x.source_id, "mission": x.mission, "status": x.status,
        "current_url": x.current_url, "current_action": x.current_action,
        "pages_visited": x.pages_visited, "items_extracted": x.items_extracted,
        "opportunities_created": x.opportunities_created, "error_code": x.error_code,
        "error_message": x.error_message, "started_at": x.started_at,
        "finished_at": x.finished_at, "created_at": x.created_at,
    } for x in rows]


@r.get("/activity")
def list_activity(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(AgentActivity).order_by(AgentActivity.id.desc()).limit(min(limit, 300)).all()
    return [{"id": x.id, "run_id": x.run_id, "level": x.level, "phase": x.phase, "action": x.action, "detail": x.detail, "created_at": x.created_at} for x in rows]


@r.get("/approvals")
def list_approvals(db: Session = Depends(get_db)):
    rows = db.query(AgentApproval).order_by(AgentApproval.id.desc()).all()
    return [{"id": x.id, "run_id": x.run_id, "risk": x.risk, "action_type": x.action_type, "title": x.title, "payload_json": x.payload_json, "status": x.status, "created_at": x.created_at, "decided_at": x.decided_at} for x in rows]


@r.post("/approvals/{approval_id}")
def decide_approval(approval_id: int, payload: ApprovalDecision, db: Session = Depends(get_db)):
    if payload.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")
    row = db.get(AgentApproval, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    row.status = payload.decision
    row.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": row.id, "status": row.status}
