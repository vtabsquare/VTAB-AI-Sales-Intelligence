from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings
kwargs={'connect_args':{'check_same_thread':False}} if settings.database_url.startswith('sqlite') else {}
if settings.database_url.startswith('mssql+pymssql'):
    kwargs['connect_args'] = {'encryption': 'require', 'login_timeout': 15, 'timeout': 30}
if settings.database_url.startswith('postgresql'):
    kwargs.update(poolclass=NullPool, connect_args={'connect_timeout': 15})
engine=create_engine(settings.database_url, pool_pre_ping=True, **kwargs)
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
