"""
Test configuration and fixtures for pytest
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db.base import Base
from backend.core.dependencies import get_db

# Import all models so they are registered with Base.metadata
from backend.models.user import User
from backend.models.organization import Organization
from backend.models.user_organization import UserOrganization
from backend.models.rbac import Role, Permission
from backend.models.content import ContentType, ContentEntry
from backend.models.relationship import ContentRelationship
from backend.models.translation import Locale, Translation
from backend.models.media import Media
from backend.models.api_key import APIKey
from backend.models.audit_log import AuditLog
from backend.models.notification import Notification, EmailLog
from backend.models.webhook import Webhook, WebhookDelivery
from backend.models.theme import Theme
from backend.models.content_template import ContentTemplate
from backend.models.schedule import ContentSchedule


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "full_name": "Test User",
        "organization_name": "Test Org"
    }


@pytest.fixture
def test_content_type_data():
    """Sample content type data for testing"""
    return {
        "name": "Blog Post",
        "slug": "blog_post",
        "description": "Blog article content type",
        "schema": {
            "title": {
                "type": "text",
                "label": "Title",
                "required": True
            },
            "body": {
                "type": "richtext",
                "label": "Body",
                "required": True
            },
            "author": {
                "type": "text",
                "label": "Author"
            }
        }
    }


@pytest.fixture
def test_content_data():
    """Sample content data for testing"""
    return {
        "content_type": "blog_post",
        "slug": "test-post",
        "status": "published",
        "fields": {
            "title": "Test Blog Post",
            "body": "<p>This is test content</p>",
            "author": "Test Author"
        }
    }


@pytest.fixture
def authenticated_client(client, test_user_data):
    """Create an authenticated test client"""
    # Register user
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client
