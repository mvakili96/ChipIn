import pytest
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app as flask_app
from models.settlement import Settlement


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
        group = self.data.get(key)
        if not group:
            return False

        expense_keys = [
            stored_key
            for stored_key, expense in self.data.items()
            if stored_key.startswith("expense:") and expense["group"] == group["name"]
        ]
        for expense_key in expense_keys:
            self.data.pop(expense_key)

        self.data.pop(f"settlement-group:{group_id}", None)
        self.data.pop(key)
        return True

    def get_group_by_name(self, name):
        for group in self.get_all_groups():
            if group["name"] == name:
                return group

        return None

    # Expense Operations
    @staticmethod
    def _expense_summary(expense):
        return {
            "id": expense.get("id"),
            "name": expense.get("name"),
            "group": expense.get("group"),
            "amount": expense.get("amount"),
            "payer": expense.get("payer"),
            "sharers": expense.get("sharers"),
        }

    def save_expense(self, expense_dict):
        key = f"expense:{expense_dict['id']}"
        self.data[key] = expense_dict
        return expense_dict

    def get_all_expenses(self):
        return [v for k, v in self.data.items() if k.startswith("expense:")]

    def get_expense(self, expense_id):
        key = f"expense:{expense_id}"
        return self.data.get(key)

    def get_expense_attr(self, expense_id, key):
        expense = self.get_expense(expense_id)
        return expense.get(key) if expense else None

    def delete_expense(self, expense_id):
        key = f"expense:{expense_id}"
        expense = self.data.get(key)
        if not expense:
            return False

        group = self.get_group_by_name(expense["group"])
        if not group:
            return False

        self.data.pop(key)

        group_expenses = self.get_group_expenses(group["id"])
        tx = Settlement(group_expenses, group["users"])
        self.save_group_settlements(
            [list(settlement) for settlement in tx],
            f"settlement-group:{group['id']}",
        )
        return True

    def get_group_expenses(self, group_id):
        group = self.get_group(group_id)
        if not group:
            return []

        return [
            self._expense_summary(expense)
            for key, expense in self.data.items()
            if key.startswith("expense:") and expense["group"] == group["name"]
        ]

    def get_user_paid_expenses(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return []

        return [
            self._expense_summary(expense)
            for key, expense in self.data.items()
            if key.startswith("expense:") and expense["payer"] == user["name"]
        ]

    # Settlement Operations
    def save_group_settlements(self, settlement, key):
        self.data[key] = settlement
        return settlement

    def get_all_group_settlements(self):
        return {
            key: value
            for key, value in self.data.items()
            if key.startswith("settlement-group:") and value
        }

    def get_group_settlements(self, group_id):
        return self.data.get(f"settlement-group:{group_id}")


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
