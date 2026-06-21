import pytest
import sys
import os
import json

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
        if key not in self.data:
            return False

        self.data.pop(key)
        return True


@pytest.fixture
def app():
    """Create Flask app for testing"""
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def create_user(client):
    """Create a user through the API and return the JSON response."""

    def _create_user(name="User 1", email="user1@example.com"):
        response = client.post(
            "/users/",
            data=json.dumps({"name": name, "email": email}),
            content_type="application/json",
        )
        assert response.status_code == 201
        return response.get_json()

    return _create_user


@pytest.fixture
def create_group(client, create_user):
    """Create a group through the API and return the JSON response."""

    def _create_group(name="Group 1", users=None):
        members = users or ["User 1", "User 2"]
        for index, member_name in enumerate(members, start=1):
            create_user(name=member_name, email=f"user{index}@example.com")

        response = client.post(
            "/groups/",
            data=json.dumps({"name": name, "users": members}),
            content_type="application/json",
        )
        assert response.status_code == 201
        return response.get_json()

    return _create_group


@pytest.fixture(autouse=True)
def mock_redis_service(monkeypatch):
    """Replace redis_service with mock for all tests"""
    import services.redis_service as redis_module
    import routes.users as users_module
    import routes.groups as groups_module
    import routes.expenses as expenses_module
    import routes.settlements as settlements_module

    mock_service = MockRedisService()

    # Patch in all modules that import redis_service
    monkeypatch.setattr(redis_module, "redis_service", mock_service)
    monkeypatch.setattr(users_module, "redis_service", mock_service)
    monkeypatch.setattr(groups_module, "redis_service", mock_service)
    monkeypatch.setattr(expenses_module, "redis_service", mock_service)
    monkeypatch.setattr(settlements_module, "redis_service", mock_service)

    yield mock_service

    # Cleanup after test
    mock_service.data.clear()
