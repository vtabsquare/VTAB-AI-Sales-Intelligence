from datetime import datetime, timedelta, timezone
from time import perf_counter
from zoneinfo import ZoneInfo
from app.models.db import SessionLocal
from app.models.platform import ScheduledWorkflow, WorkflowRunHistory
from app.models.sales_agent import WorkflowLease
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
from threading import Event, Thread


def _renew_lease(stop, lease_id, token, scheduler_owned=False):
    while not stop.wait(30):
        session=SessionLocal()
        try:
            session.execute(update(WorkflowLease).where(WorkflowLease.workflow_id==lease_id,
                WorkflowLease.token==token).values(expires_at=datetime.utcnow()+timedelta(hours=1)))
            if scheduler_owned:
                from app.models.sales_agent import SchedulerHeartbeat
                session.execute(update(SchedulerHeartbeat).where(SchedulerHeartbeat.id=='scheduler').values(observed_at=datetime.utcnow()))
            session.commit()
        except Exception: session.rollback()
        finally: session.close()

def execute(db,w):
    if w.action_type=='SALES_CYCLE':
        from app.services.sales_manager import run_sales_cycle; return run_sales_cycle(db)
    if w.action_type=='RESOURCE_SYNC':
        from app.services.company_sources import sync_company_sources; return sync_company_sources(db)
    if w.action_type=='DISCOVERY':
        from app.services.global_discovery import run_discovery; return run_discovery(db)
    if w.action_type=='INBOX_SYNC':
        from app.services.response_intelligence import sync_inbox; return sync_inbox(db)
    if w.action_type=='REPROCESS':
        from app.services.response_intelligence import reprocess_existing; return reprocess_existing(db)
    raise ValueError('Unsupported workflow action')

def next_run(w, now=None):
    now=now or datetime.utcnow()
    if w.interval_minutes < 1440: return now+timedelta(minutes=max(5,w.interval_minutes))
    try: tz=ZoneInfo(w.timezone or 'UTC')
    except Exception: tz=timezone.utc
    local=now.replace(tzinfo=timezone.utc).astimezone(tz)
    try: hh,mm=[int(x) for x in (w.run_at_time or '09:00').split(':')]
    except Exception: hh,mm=9,0
    candidate=local.replace(hour=hh,minute=mm,second=0,microsecond=0)
    if candidate<=local: candidate += timedelta(minutes=w.interval_minutes)
    return candidate.astimezone(timezone.utc).replace(tzinfo=None)

def run_and_record(db,w,scheduler_owned=False):
    start=datetime.utcnow(); tick=perf_counter()
    # A shared database lease prevents duplicate execution across web/worker replicas.
    # Crash recovery is bounded by expiry; outbound SENDING attempts are never auto-retried.
    workflow_id=w.id; lease_id='action:'+w.action_type if w.action_type in {'SALES_CYCLE','RESOURCE_SYNC'} else workflow_id
    token=str(uuid4())
    if not db.get(WorkflowLease,lease_id):
        try:
            with db.begin_nested():
                db.add(WorkflowLease(workflow_id=lease_id,token='',expires_at=start))
                db.flush()
        except IntegrityError: pass
    claimed=db.execute(update(WorkflowLease).where(WorkflowLease.workflow_id==lease_id,
        WorkflowLease.expires_at<=start).values(token=token,expires_at=start+timedelta(hours=1)))
    if claimed.rowcount != 1:
        db.rollback();return None
    db.commit()
    for stale in db.query(WorkflowRunHistory).filter_by(workflow_id=workflow_id,status='RUNNING').all():
        stale.status='INTERRUPTED';stale.finished_at=start;stale.error='Worker stopped before completion. Review ambiguous send attempts before retrying.'
    h=WorkflowRunHistory(workflow_id=w.id,workflow_name=w.name,action_type=w.action_type,status='RUNNING',started_at=start)
    db.add(h); db.commit(); db.refresh(h)
    stop=Event();heartbeat=Thread(target=_renew_lease,args=(stop,lease_id,token,scheduler_owned),daemon=True);heartbeat.start()
    try:
        result=execute(db,w); h.status='PARTIAL' if isinstance(result,dict) and (result.get('status')=='PARTIAL' or result.get('errors')) else 'SUCCESS'; h.result=result if isinstance(result,dict) else {'result':str(result)}; w.last_status=h.status; w.last_result=h.result
    except Exception as e:
        db.rollback()
        h = db.get(WorkflowRunHistory, h.id)
        w = db.get(ScheduledWorkflow, w.id)
        h.status='FAILED'; h.error='Workflow failed. Check connector configuration and application logs.'; h.result={'error':h.error}; w.last_status='FAILED'; w.last_result=h.result
    finally:
        stop.set();heartbeat.join(timeout=1)
    h.finished_at=datetime.utcnow(); h.duration_ms=int((perf_counter()-tick)*1000); w.last_run_at=start; w.next_run_at=next_run(w,h.finished_at)
    db.execute(update(WorkflowLease).where(WorkflowLease.workflow_id==lease_id,WorkflowLease.token==token).values(expires_at=h.finished_at))
    db.commit(); db.refresh(h)
    return h

def scheduler_tick():
    db=SessionLocal(); now=datetime.utcnow()
    try:
        from app.models.sales_agent import SchedulerHeartbeat
        heartbeat=db.get(SchedulerHeartbeat,'scheduler') or SchedulerHeartbeat(id='scheduler')
        heartbeat.observed_at=now;db.add(heartbeat);db.commit()
        for w in db.query(ScheduledWorkflow).filter(ScheduledWorkflow.enabled==True).all():
            if w.next_run_at and w.next_run_at>now: continue
            try: run_and_record(db,w,scheduler_owned=True)
            except Exception: db.rollback()  # One broken schedule must not stop other jobs.
    finally: db.close()
