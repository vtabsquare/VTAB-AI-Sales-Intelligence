"""Tests never load or connect to the supplied SQL Server or live Graph credentials."""
import os
import tempfile
from pathlib import Path
TEST_DB = Path(tempfile.mkdtemp(prefix='vtab-tests-')) / 'test.db'
os.environ.update(DATABASE_URL=f'sqlite:///{TEST_DB}', INITIALIZE_SCHEMA='true',SCHEDULER_ENABLED='false',DEMO_MODE='true',APP_ENV='test',LOGIN_EMAIL='qa@example.com',LOGIN_PASSWORD='test-only-password',JWT_SECRET='test-only-private-signing-key',MICROSOFT_TENANT_ID='',MICROSOFT_CLIENT_ID='',MICROSOFT_CLIENT_SECRET='',MICROSOFT_SENDER_EMAIL='',OPENAI_API_KEY='',SERPER_API_KEY='')
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.db import Base,engine
from app.api.auth_routes import make_token
@pytest.fixture
def client():
    assert engine.url.get_backend_name()=="sqlite" and engine.url.database==str(TEST_DB), "Refusing to reset a non-test database"
    Base.metadata.drop_all(engine)
    with TestClient(app,raise_server_exceptions=False) as c:
        yield c
@pytest.fixture
def authorized(client):
    client.headers['Authorization']='Bearer '+make_token('qa@example.com')
    return client

@pytest.fixture(autouse=True)
def source_evidence_offline(monkeypatch):
    monkeypatch.setattr('app.services.source_evidence.fetch_evidence',lambda url:{'status':'UNAVAILABLE','source_url':url,'text':'','emails':[]})
