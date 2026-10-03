"""Single-replica scheduler worker. No customer-send jobs are registered."""
from apscheduler.schedulers.blocking import BlockingScheduler
from app.services.workflow_scheduler import scheduler_tick

if __name__=='__main__':
    scheduler=BlockingScheduler()
    scheduler.add_job(scheduler_tick,'interval',minutes=1,max_instances=1,coalesce=True)
    scheduler.start()
