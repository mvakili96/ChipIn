import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app as flask_app
from services.redis_service import RedisService


class MockRedisService:
    """Mock Redis Service for testing without real Redis.
    So we can use it in our tests without having to set up a real Redis instance.
    This class provides a simple in-memory storage and can run multiple testssimultaneously."""

    def __init__(self):
        self.data = {}  # In-memory storage

    def save_user(self, user_dict):
        key = f"user:{user_dict['id']}"
        self.data[key] = user_dict
        return user_dict


@pytest.fixture
def app():
    """Create Flask app for testing"""
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_redis_service(monkeypatch):
    """Replace redis_service with mock for all tests"""
    import services.redis_service as redis_module
    import routes.users as users_module

    mock_service = MockRedisService()

    # Patch in all modules that import redis_service
    monkeypatch.setattr(redis_module, "redis_service", mock_service)
    monkeypatch.setattr(users_module, "redis_service", mock_service)

    yield mock_service

    # Cleanup after test
    mock_service.data.clear()
