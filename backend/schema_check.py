"""Read-only by default. Optional additive session table, never recreates a database."""
import argparse,json
from sqlalchemy import inspect
from app.models.db import engine,Base
from app.models import entities,sales_followup,platform,intelligence
parser=argparse.ArgumentParser();parser.add_argument('--add-auth-session',action='store_true');args=parser.parse_args()
try:
 if args.add_auth_session:platform.AuthSession.__table__.create(engine,checkfirst=True)
 inspector=inspect(engine);tables=set(inspector.get_table_names());missing={};details={}
 for name,table in Base.metadata.tables.items():
  if name not in tables:missing[name]=['TABLE MISSING'];continue
  actual={c['name']:c for c in inspector.get_columns(name)}
  absent=[c.name for c in table.columns if c.name not in actual]
  if absent:missing[name]=absent
  details[name]=[{'name':c['name'],'type':str(c['type']),'nullable':c.get('nullable')} for c in actual.values()]
 print(json.dumps({'status':'PASS' if not missing else 'FAIL','missing':missing,'existing_columns':details},indent=2))
 raise SystemExit(1 if missing else 0)
except Exception:
 print('FAIL: Database schema could not be inspected. Verify SQL Server connectivity and installed ODBC driver. Credentials are not displayed.');raise SystemExit(2)
