"""Native always-on scheduler worker. Sales sends are governed by persisted owner policy."""
from app.models import entities, platform, intelligence, sales_followup, sales_agent
from app.core.config import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from app.services.workflow_scheduler import scheduler_tick

if __name__=='__main__':
    if settings.initialize_schema:
        from app.models.db import Base, engine
        Base.metadata.create_all(engine)
    scheduler=BlockingScheduler()
    scheduler.add_job(scheduler_tick,'interval',minutes=1,max_instances=1,coalesce=True)
    scheduler.start()
