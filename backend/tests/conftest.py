import os, tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app, _rate_buckets

@pytest.fixture()
def client():
    _rate_buckets.clear()
    test_url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    engine = create_engine(test_url, **({"connect_args":{"check_same_thread": False}, "poolclass":StaticPool} if test_url.startswith("sqlite") else {}))
    if not test_url.startswith("sqlite"):
        from sqlalchemy import text
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    def override_get_db():
        db = TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"X-SmartFind-Request":"1"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
