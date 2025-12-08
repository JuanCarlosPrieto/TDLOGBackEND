import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import engine
from app.api.deps import get_db

SQLALCHEMY_DATAengine_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATAengine_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    engine.metadata.drop_all(bind=engine)
    engine.metadata.create_all(bind=engine)
    yield
    engine.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)
