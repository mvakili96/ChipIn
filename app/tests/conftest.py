import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app as flask_app


class MockRedisService:
    """Mock Redis Service for testing without real Redis.
    So we can use it in our tests without having to set up a real Redis instance.
    This class provides a simple in-memory storage and can run multiple tests simultaneously."""

    def __init__(self):
        self.data = {}  # In-memory storage

    # User Operations
    def save_user(self, user_dict):
        key = f"user:{user_dict['id']}"
        self.data[key] = user_dict
        return user_dict

    def get_user(self, user_id):
        key = f"user:{user_id}"
        return self.data.get(key)

    def get_all_users(self):
        return [v for k, v in self.data.items() if k.startswith("user:")]

    def get_user_attr(self, user_id, key):
        user = self.get_user(user_id)
        return user.get(key) if user else None

    def get_all_user_names(self):
        return [user["name"] for user in self.get_all_users()]

    # Group Operations
    def save_group(self, group_dict):
        key = f"group:{group_dict['id']}"
        self.data[key] = group_dict
        return group_dict

    def get_group(self, group_id):
        key = f"group:{group_id}"
        return self.data.get(key)

    def get_all_groups(self):
        return [v for k, v in self.data.items() if k.startswith("group:")]

    def get_group_attr(self, group_id, key):
        group = self.get_group(group_id)
        return group.get(key) if group else None

    def delete_group(self, group_id):
        key = f"group:{group_id}"
        self.data.pop(key)
        return key not in self.data.keys()


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
    import routes.groups as groups_module

    mock_service = MockRedisService()

    # Patch in all modules that import redis_service
    monkeypatch.setattr(redis_module, "redis_service", mock_service)
    monkeypatch.setattr(users_module, "redis_service", mock_service)
    monkeypatch.setattr(groups_module, "redis_service", mock_service)

    yield mock_service

    # Cleanup after test
    mock_service.data.clear()
