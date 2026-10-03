"""Adopt an existing schema only after a strict metadata comparison and backup."""
import argparse
from sqlalchemy import MetaData
from alembic.config import Config
from alembic import command
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from app.models.db import Base,engine
from app.models import entities,platform,sales_followup,intelligence
parser=argparse.ArgumentParser()
parser.add_argument('--stamp-reviewed-baseline',action='store_true')
args=parser.parse_args()
extra={'qualification_assessments','discovery_occurrences','intelligence_workflows','knowledge_chunks','country_targets'}
metadata=MetaData()
for table in Base.metadata.sorted_tables:
    if table.name not in extra:table.to_metadata(metadata)
with engine.connect() as connection:
    differences=compare_metadata(MigrationContext.configure(connection,opts={'include_object':lambda obj,name,type_,reflected,compare_to:name not in extra if type_=='table' else True}),metadata)
if differences:
    raise SystemExit('Schema differs from the frozen baseline. Refusing to stamp. Review with your DBA; no data was changed.')
if args.stamp_reviewed_baseline:
    command.stamp(Config('alembic.ini'),'0001_baseline')
    print('Reviewed matching baseline recorded. Run alembic upgrade head for additive tables.')
else:
    print('Baseline matches. Back up the database before explicitly recording the reviewed baseline.')
