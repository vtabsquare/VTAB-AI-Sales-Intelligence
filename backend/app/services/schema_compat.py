from sqlalchemy import inspect,text
from app.models.db import engine

def ensure_platform_schema():
    """Small additive compatibility patch for development databases."""
    i=inspect(engine)
    if 'scheduled_workflows' not in i.get_table_names(): return
    cols={c['name'] for c in i.get_columns('scheduled_workflows')}
    statements=[]
    for name,kind,value in [('timezone','VARCHAR(100)','Asia/Kolkata'),('run_at_time','VARCHAR(5)','09:00')]:
        if name not in cols:
            named_default=f'CONSTRAINT DF_scheduled_workflows_{name} ' if engine.dialect.name=='mssql' else ''
            statements.append(f"ALTER TABLE scheduled_workflows ADD {name} {kind} NOT NULL {named_default}DEFAULT '{value}'")
    if statements:
        with engine.begin() as c:
            for q in statements: c.execute(text(q))
