"""
Test configuration and fixtures for pytest
"""

import os
import warnings

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Suppress SQLAlchemy warning about circular foreign key dependencies
# This is expected with SQLite testing database
warnings.filterwarnings("ignore", message=".*Can't sort tables for DROP.*", category=SAWarning)

# Set test environment variables before importing app
os.environ["TESTING"] = "true"  # Indicate we're in test mode
os.environ["MEILISEARCH_URL"] = "http://localhost:7700"
os.environ["MEILISEARCH_API_KEY"] = "change-this-secure-key-min-32-chars"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["RATE_LIMIT_STORAGE_URL"] = "redis://localhost:6379/1"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # Disable rate limiting for tests
os.environ["MAIL_SUPPRESS_SEND"] = "1"  # Disable email sending in tests
os.environ["STORAGE_BACKEND"] = "local"  # Use local storage for tests to avoid AWS config issues
os.environ["UPLOAD_DIR"] = "test_uploads"  # Use separate directory for test uploads
os.environ["SKIP_EMAIL_VERIFICATION"] = "true"  # Skip email verification for tests

from backend.core.dependencies import get_db
from backend.db.base import Base
from backend.main import app

# Import all models so they are registered with Base.metadata


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

    # Seed default permissions for tests
    from backend.core.seed_permissions import seed_default_permissions

    seed_default_permissions(session)

    try:
        yield session
    finally:
        session.close()
        # Suppress SAWarning about circular FK dependencies during DROP
        # This is expected with SQLite testing database (organizations <-> users)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=SAWarning)
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
        "organization_name": "Test Org",
    }


@pytest.fixture
def test_content_type_data():
    """Sample content type data for testing"""
    return {
        "name": "Blog Post",
        "api_id": "blog_post",
        "description": "Blog article content type",
        "fields": [
            {"name": "title", "type": "text", "required": True, "help_text": "Blog post title"},
            {
                "name": "body",
                "type": "textarea",
                "required": True,
                "help_text": "Blog post content",
            },
            {"name": "author", "type": "text", "required": False, "help_text": "Author name"},
        ],
    }


@pytest.fixture
def test_content_data(test_content_type_data, authenticated_client):
    """Sample content data for testing"""
    # Create content type first to get its ID
    ct_response = authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    content_type_id = ct_response.json()["id"]

    return {
        "content_type_id": content_type_id,
        "slug": "test-post",
        "status": "published",
        "data": {
            "title": "Test Blog Post",
            "body": "<p>This is test content</p>",
            "author": "Test Author",
        },
    }


@pytest.fixture
def authenticated_client(client, test_user_data):
    """Create an authenticated test client"""
    from backend.db.session import get_db
    from backend.models.user import User

    # Register user
    client.post("/api/v1/auth/register", json=test_user_data)

    # Verify email in database (bypass email verification for tests)
    # Get the db session from the app's dependency override
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = db.query(User).filter(User.email == test_user_data["email"]).first()
        if user:
            user.is_email_verified = True
            db.commit()
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass

    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )

    token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    return client
