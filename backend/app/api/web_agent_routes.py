from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.models.web_agent import AgentActivity, AgentApproval, WebAgentRun, WebAgentSettings, WebSource
from app.services.web_agent import agent_settings, browse_source, dashboard, queue_sources, validate_public_url

r = APIRouter(prefix="/api/web-agent", tags=["web-agent"])


RECOMMENDED_SOURCES = [
    {"name":"UNGM Procurement Opportunities","url":"https://www.ungm.org/Public/Notice","country":"Global","category":"UN / International","priority":100,"scan_frequency_minutes":360},
    {"name":"EU TED","url":"https://ted.europa.eu/en/","country":"European Union","category":"Government Procurement","priority":95,"scan_frequency_minutes":360},
    {"name":"World Bank Procurement","url":"https://projects.worldbank.org/en/projects-operations/procurement","country":"Global","category":"Development Bank","priority":95,"scan_frequency_minutes":360},
    {"name":"Asian Development Bank","url":"https://www.adb.org/work-with-us/business-opportunities","country":"Asia Pacific","category":"Development Bank","priority":90,"scan_frequency_minutes":480},
    {"name":"African Development Bank","url":"https://www.afdb.org/en/projects-and-operations/procurement","country":"Africa","category":"Development Bank","priority":90,"scan_frequency_minutes":480},
    {"name":"UK Contracts Finder","url":"https://www.contractsfinder.service.gov.uk/Search","country":"United Kingdom","category":"Government Procurement","priority":90,"scan_frequency_minutes":360},
    {"name":"Ireland eTenders","url":"https://www.etenders.gov.ie/","country":"Ireland","category":"Government Procurement","priority":90,"scan_frequency_minutes":360},
    {"name":"Singapore GeBIZ","url":"https://www.gebiz.gov.sg/","country":"Singapore","category":"Government Procurement","priority":90,"scan_frequency_minutes":360},
    {"name":"SAM.gov Contract Opportunities","url":"https://sam.gov/content/opportunities","country":"United States","category":"Government Procurement","priority":85,"scan_frequency_minutes":360},
    {"name":"AusTender","url":"https://www.tenders.gov.au/","country":"Australia","category":"Government Procurement","priority":85,"scan_frequency_minutes":480},
    {"name":"CanadaBuys","url":"https://canadabuys.canada.ca/en/tender-opportunities","country":"Canada","category":"Government Procurement","priority":85,"scan_frequency_minutes":480},
    {"name":"New Zealand GETS","url":"https://www.gets.govt.nz/","country":"New Zealand","category":"Government Procurement","priority":80,"scan_frequency_minutes":480},
    {"name":"UNDP Procurement Notices","url":"https://procurement-notices.undp.org/","country":"Global","category":"UN / International","priority":80,"scan_frequency_minutes":480},
    {"name":"EBRD Procurement","url":"https://ecepp.ebrd.com/","country":"Global","category":"Development Bank","priority":75,"scan_frequency_minutes":720},
]


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    url: str
    country: Optional[str] = None
    category: str = "Open Web"
    auth_required: bool = False
    scan_frequency_minutes: int = Field(default=360, ge=15, le=10080)
    priority: int = Field(default=50, ge=0, le=100)
    trusted: bool = False
    enabled: bool = True


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    url: str | None = None
    country: str | None = None
    category: str | None = None
    auth_required: bool | None = None
    scan_frequency_minutes: int | None = Field(default=None, ge=15, le=10080)
    priority: int | None = Field(default=None, ge=0, le=100)
    trusted: bool | None = None
    enabled: bool | None = None


class RunRequest(BaseModel):
    source_id: int
    mission: str = "Discover global opportunities matching VTAB Square services"
    keywords: list[str] | None = None


class ApprovalDecision(BaseModel):
    decision: str


@r.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    return dashboard(db)


@r.get("/health")
def health(db: Session = Depends(get_db)):
    state = dashboard(db)
    return {"status":"ok","agent_status":state["status"],"database":"connected","browser_concurrency":1,
            "sources":state["sources"],"pending_approvals":state["pending_approvals"]}


@r.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(WebSource).order_by(WebSource.priority.desc(), WebSource.id.desc()).all()
    return [{
        "id": x.id, "name": x.name, "url": x.url, "country": x.country,
        "category": x.category, "enabled": x.enabled, "trusted": x.trusted,
        "auth_required": x.auth_required, "priority": x.priority,
        "scan_frequency_minutes": x.scan_frequency_minutes, "success_rate": x.success_rate,
        "opportunities_found": x.opportunities_found, "failure_count": x.failure_count,
        "health_status": x.health_status, "last_error": x.last_error,
        "last_scan_at": x.last_scan_at, "next_scan_at": x.next_scan_at,
    } for x in rows]


@r.post("/sources")
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    try: validate_public_url(payload.url)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    if db.query(WebSource).filter(WebSource.url == payload.url).first():
        raise HTTPException(status_code=409, detail="Source already exists")
    row = WebSource(**payload.model_dump(), health_status="READY", updated_at=datetime.now(timezone.utc))
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "status": "created", "message": f"{row.name} added to the source registry."}


@r.post("/sources/seed-recommended")
def seed_recommended(db: Session = Depends(get_db)):
    added, skipped = 0, 0
    existing = {x[0] for x in db.query(WebSource.url).all()}
    for item in RECOMMENDED_SOURCES:
        if item["url"] in existing:
            skipped += 1; continue
        db.add(WebSource(**item, trusted=True, enabled=True, auth_required=False, health_status="READY", updated_at=datetime.now(timezone.utc)))
        existing.add(item["url"]); added += 1
    db.commit()
    return {"status":"completed","added":added,"skipped":skipped,"message":f"{added} recommended source(s) added; {skipped} duplicate(s) skipped."}


@r.put("/sources/{source_id}")
def update_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)):
    row = db.get(WebSource, source_id)
    if not row: raise HTTPException(status_code=404, detail="Source not found")
    values = payload.model_dump(exclude_unset=True)
    if "url" in values:
        try: validate_public_url(values["url"])
        except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
        duplicate = db.query(WebSource).filter(WebSource.url == values["url"], WebSource.id != source_id).first()
        if duplicate: raise HTTPException(status_code=409, detail="Another source already uses this URL")
    for key, value in values.items(): setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc); db.commit(); db.refresh(row)
    return {"id":row.id,"status":"updated","message":f"{row.name} updated."}


@r.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    row = db.get(WebSource, source_id)
    if not row: raise HTTPException(status_code=404, detail="Source not found")
    db.query(WebAgentRun).filter(WebAgentRun.source_id == source_id).update({WebAgentRun.source_id: None}, synchronize_session=False)
    name = row.name; db.delete(row); db.commit()
    return {"status":"deleted","message":f"{name} removed from the source registry."}


@r.post("/sources/{source_id}/toggle")
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    row = db.get(WebSource, source_id)
    if not row: raise HTTPException(status_code=404, detail="Source not found")
    row.enabled = not row.enabled; row.updated_at = datetime.now(timezone.utc); db.commit()
    return {"id": row.id, "enabled": row.enabled, "message":f"{row.name} {'enabled' if row.enabled else 'paused'}."}


@r.post("/run")
def start_run(payload: RunRequest, db: Session = Depends(get_db)):
    source = db.get(WebSource, payload.source_id)
    if not source: raise HTTPException(status_code=404, detail="Source not found")
    result = asyncio.run(browse_source(db, source, payload.mission, payload.keywords))
    return result


@r.post("/run-due")
def run_due(db: Session = Depends(get_db)):
    settings = agent_settings(db)
    if not settings.enabled: raise HTTPException(status_code=409, detail="Agent is paused. Resume it before queuing scheduled runs.")
    count = queue_sources(db, True)
    return {"status":"queued","sources_queued":count,"message":f"{count} due source(s) queued for the autonomous worker."}


@r.post("/run-all")
def run_all(db: Session = Depends(get_db)):
    settings = agent_settings(db)
    if not settings.enabled: raise HTTPException(status_code=409, detail="Agent is paused. Resume it before queuing runs.")
    active = db.query(WebAgentRun).filter(WebAgentRun.status.in_(["queued","running"])).count()
    if active: raise HTTPException(status_code=409, detail="A browser run is already active. Wait for it to finish before Run All.")
    count = queue_sources(db, False)
    return {"status":"queued","sources_queued":count,"message":f"{count} enabled source(s) queued. The 1 GB server processes them serially."}


@r.post("/pause")
def pause_agent(db: Session = Depends(get_db)):
    settings = agent_settings(db); settings.enabled = False; settings.updated_at = datetime.now(timezone.utc); db.commit()
    return {"status":"paused","message":"Autonomous scheduled scans are paused. Existing browser sessions are not force-stopped."}


@r.post("/resume")
def resume_agent(db: Session = Depends(get_db)):
    settings = agent_settings(db); settings.enabled = True; settings.updated_at = datetime.now(timezone.utc); db.commit()
    return {"status":"ready","message":"Autonomous scheduled scans resumed."}


@r.get("/runs")
def list_runs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(WebAgentRun).order_by(WebAgentRun.id.desc()).limit(min(limit, 200)).all()
    source_names = {s.id:s.name for s in db.query(WebSource).all()}
    return [{
        "id": x.id, "source_id": x.source_id, "source_name": source_names.get(x.source_id, "Removed source"),
        "mission": x.mission, "status": x.status, "current_url": x.current_url, "current_action": x.current_action,
        "pages_visited": x.pages_visited, "items_extracted": x.items_extracted, "opportunities_created": x.opportunities_created,
        "error_code": x.error_code, "error_message": x.error_message, "started_at": x.started_at,
        "finished_at": x.finished_at, "created_at": x.created_at,
    } for x in rows]


@r.get("/activity")
def list_activity(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(AgentActivity).order_by(AgentActivity.id.desc()).limit(min(limit, 300)).all()
    return [{"id": x.id, "run_id": x.run_id, "level": x.level, "phase": x.phase, "action": x.action, "detail": x.detail, "created_at": x.created_at} for x in rows]


@r.get("/approvals")
def list_approvals(db: Session = Depends(get_db)):
    rows = db.query(AgentApproval).order_by(AgentApproval.id.desc()).all()
    return [{"id": x.id, "run_id": x.run_id, "risk": x.risk, "action_type": x.action_type, "title": x.title,
             "payload_json": x.payload_json, "status": x.status, "created_at": x.created_at, "decided_at": x.decided_at} for x in rows]


@r.post("/approvals/{approval_id}")
def decide_approval(approval_id: int, payload: ApprovalDecision, db: Session = Depends(get_db)):
    if payload.decision not in {"approved", "rejected"}: raise HTTPException(status_code=400, detail="decision must be approved or rejected")
    row = db.get(AgentApproval, approval_id)
    if not row: raise HTTPException(status_code=404, detail="Approval not found")
    row.status = payload.decision; row.decided_at = datetime.now(timezone.utc); db.commit()
    return {"id": row.id, "status": row.status, "message":f"Approval {payload.decision}."}
