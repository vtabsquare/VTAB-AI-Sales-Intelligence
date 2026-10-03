from sqlalchemy import inspect,text
from app.models.db import engine

def ensure_platform_schema():
    """Small non-destructive compatibility patch for existing SQL Server dev databases."""
    i=inspect(engine)
    if 'scheduled_workflows' not in i.get_table_names(): return
    cols={c['name'] for c in i.get_columns('scheduled_workflows')}
    statements=[]
    if 'timezone' not in cols: statements.append("ALTER TABLE scheduled_workflows ADD timezone VARCHAR(100) NOT NULL CONSTRAINT DF_scheduled_workflows_timezone DEFAULT 'Asia/Kolkata'")
    if 'run_at_time' not in cols: statements.append("ALTER TABLE scheduled_workflows ADD run_at_time VARCHAR(5) NOT NULL CONSTRAINT DF_scheduled_workflows_run_at DEFAULT '09:00'")
    if statements:
        with engine.begin() as c:
            for q in statements: c.execute(text(q))
