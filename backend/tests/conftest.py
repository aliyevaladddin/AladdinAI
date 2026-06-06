"""Test configuration and fixtures."""
import os
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet

# Set up test environment variables before importing app
if not os.environ.get("FERNET_KEY"):
    os.environ["FERNET_KEY"] = Fernet.generate_key().decode()
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

import sys
from pathlib import Path

# Add backend directory to path so pytest can find app module
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
import uuid

from app.main import app
from app.database import Base, get_db

# Test database - use aiosqlite for async
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Setup database once for all tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(setup_database):
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Don't use context manager to avoid event loop issues
    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(client):
    """Create a test user and return auth token."""
    # Use unique email for each test to avoid conflicts
    unique_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    
    response = client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "name": "Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    
    # Get user_id from /me endpoint
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/auth/me", headers=headers)
    user_data = me_response.json()
    
    return {
        "user_id": user_data["id"],
        "token": token,
        "email": unique_email
    }


@pytest.fixture
def auth_headers(test_user):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {test_user['token']}"}
