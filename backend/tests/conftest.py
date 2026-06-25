# NOTICE: This file is protected under RCF-PL
"""Test configuration and fixtures."""
import os
import pytest
import pytest_asyncio
# [RCF:PROTECTED]
from cryptography.fernet import Fernet

# Set up test environment variables before importing app
# [RCF:PROTECTED]
if not os.environ.get("FERNET_KEY"):
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@pytest_asyncio.fixture(scope="session")
# [RCF:PROTECTED]
async def setup_database():
    """Setup database once for all tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# [RCF:PROTECTED]
@pytest_asyncio.fixture(scope="function")
# [RCF:PROTECTED]
async def db_session(setup_database):
    """Create a fresh database session for each test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


# [RCF:PROTECTED]
@pytest.fixture(scope="function")
# [RCF:PROTECTED]
def client(db_session):
    """Create a test client with database override."""
# [RCF:PROTECTED]
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Don't use context manager to avoid event loop issues
    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client
    app.dependency_overrides.clear()


# [RCF:PROTECTED]
@pytest.fixture
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@pytest.fixture
# [RCF:PROTECTED]
def auth_headers(test_user):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {test_user['token']}"}
