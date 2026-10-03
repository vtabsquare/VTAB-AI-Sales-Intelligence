from datetime import datetime, timedelta, timezone
from time import perf_counter
from zoneinfo import ZoneInfo
from app.models.db import SessionLocal
from app.models.platform import ScheduledWorkflow, WorkflowRunHistory

def execute(db,w):
    if w.action_type=='DISCOVERY':
        from app.services.global_discovery import run_discovery; return run_discovery(db)
    if w.action_type=='INBOX_SYNC':
        from app.services.response_intelligence import sync_inbox; return sync_inbox(db)
    if w.action_type=='REPROCESS':
        from app.services.response_intelligence import reprocess_existing; return reprocess_existing(db)
    raise ValueError('Unsupported workflow action')

def next_run(w, now=None):
    now=now or datetime.utcnow()
    if w.interval_minutes < 1440: return now+timedelta(minutes=max(60,w.interval_minutes))
    try: tz=ZoneInfo(w.timezone or 'UTC')
    except Exception: tz=timezone.utc
    local=now.replace(tzinfo=timezone.utc).astimezone(tz)
    try: hh,mm=[int(x) for x in (w.run_at_time or '09:00').split(':')]
    except Exception: hh,mm=9,0
    candidate=local.replace(hour=hh,minute=mm,second=0,microsecond=0)
    if candidate<=local: candidate += timedelta(minutes=w.interval_minutes)
    return candidate.astimezone(timezone.utc).replace(tzinfo=None)

def run_and_record(db,w):
    start=datetime.utcnow(); tick=perf_counter()
    h=WorkflowRunHistory(workflow_id=w.id,workflow_name=w.name,action_type=w.action_type,status='RUNNING',started_at=start)
    db.add(h); db.commit(); db.refresh(h)
    try:
        result=execute(db,w); h.status='SUCCESS'; h.result=result if isinstance(result,dict) else {'result':str(result)}; w.last_status='SUCCESS'; w.last_result=h.result
    except Exception as e:
        db.rollback()
        h = db.get(WorkflowRunHistory, h.id)
        w = db.get(ScheduledWorkflow, w.id)
        h.status='FAILED'; h.error=str(e)[:4000]; h.result={'error':str(e)[:500]}; w.last_status='FAILED'; w.last_result=h.result
    h.finished_at=datetime.utcnow(); h.duration_ms=int((perf_counter()-tick)*1000); w.last_run_at=start; w.next_run_at=next_run(w,start); db.commit(); db.refresh(h)
    return h

def scheduler_tick():
    db=SessionLocal(); now=datetime.utcnow()
    try:
        for w in db.query(ScheduledWorkflow).filter(ScheduledWorkflow.enabled==True).all():
            if w.next_run_at and w.next_run_at>now: continue
            run_and_record(db,w)
    finally: db.close()
