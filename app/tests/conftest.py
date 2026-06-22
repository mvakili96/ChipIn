import pytest
import sys
import os
import uuid
from datetime import datetime

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

    def get_user_by_telegram_id(self, telegram_id):
        target_id = str(telegram_id)
        for user in self.get_all_users():
            if str(user.get("telegram_id")) == target_id:
                return user
        return None

    def get_user_by_name(self, name):
        target_name = name.strip()
        for user in self.get_all_users():
            if user.get("name") == target_name:
                return user
        return None

    def upsert_telegram_user(self, telegram_user):
        telegram_id = str(telegram_user["id"])
        existing = self.get_user_by_telegram_id(telegram_id)

        fields = {
            "source": "telegram",
            "telegram_id": telegram_id,
            "telegram_username": telegram_user.get("username"),
            "telegram_first_name": telegram_user.get("first_name"),
            "telegram_last_name": telegram_user.get("last_name"),
            "telegram_photo_url": telegram_user.get("photo_url"),
            "telegram_language_code": telegram_user.get("language_code"),
        }

        if existing:
            existing.update(fields)
            existing["updated_at"] = datetime.now().isoformat()
            return self.save_user(existing)

        first_name = (telegram_user.get("first_name") or "").strip()
        last_name = (telegram_user.get("last_name") or "").strip()
        username = (telegram_user.get("username") or "").strip()
        base_name = " ".join(part for part in [first_name, last_name] if part)
        if not base_name:
            base_name = f"@{username}" if username else f"Telegram User {telegram_id}"

        matching_user = self.get_user_by_name(base_name)
        if matching_user and not matching_user.get("telegram_id"):
            return self.link_telegram_user(matching_user["id"], telegram_user)

        existing_names = set(self.get_all_user_names())
        name = base_name if base_name not in existing_names else f"{base_name} ({telegram_id})"

        return self.save_user(
            {
                "name": name,
                "email": f"telegram-{telegram_id}@telegram.local",
                "id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(),
                **fields,
            }
        )

    def link_telegram_user(self, user_id, telegram_user):
        user = self.get_user(user_id)
        if not user:
            return None

        telegram_id = str(telegram_user["id"])
        existing = self.get_user_by_telegram_id(telegram_id)
        if existing and existing.get("id") != user_id:
            return existing

        user.update(
            {
                "telegram_id": telegram_id,
                "telegram_username": telegram_user.get("username"),
                "telegram_first_name": telegram_user.get("first_name"),
                "telegram_last_name": telegram_user.get("last_name"),
                "telegram_photo_url": telegram_user.get("photo_url"),
                "telegram_language_code": telegram_user.get("language_code"),
                "telegram_linked_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        )
        return self.save_user(user)

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
        existed = key in self.data
        self.data.pop(key, None)
        return existed and key not in self.data.keys()

    def get_group_by_name(self, name):
        for group in self.get_all_groups():
            if group["name"] == name:
                return group
        return None

    def get_group_by_telegram_chat_id(self, telegram_chat_id):
        target_id = str(telegram_chat_id)
        for group in self.get_all_groups():
            if str(group.get("telegram_chat_id")) == target_id:
                return group
        return None

    def ensure_telegram_group(self, chat):
        chat_id = str(chat["id"])
        existing = self.get_group_by_telegram_chat_id(chat_id)
        if existing:
            existing["telegram_chat_title"] = chat.get("title") or existing.get("telegram_chat_title")
            existing["telegram_chat_type"] = chat.get("type") or existing.get("telegram_chat_type")
            existing["updated_at"] = datetime.now().isoformat()
            return self.save_group(existing)

        title = chat.get("title") or chat.get("username") or f"Telegram Group {chat_id}"
        name = title
        existing_names = {group["name"] for group in self.get_all_groups()}
        if name in existing_names:
            name = f"{title} ({chat_id})"

        return self.save_group(
            {
                "name": name,
                "users": [],
                "id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(),
                "source": "telegram",
                "telegram_chat_id": chat_id,
                "telegram_chat_title": chat.get("title"),
                "telegram_chat_type": chat.get("type"),
            }
        )

    def add_user_to_group(self, group_id, user_name):
        group = self.get_group(group_id)
        if not group:
            return None

        users = group.get("users") or []
        if user_name not in users:
            users.append(user_name)
            group["users"] = users
            group["updated_at"] = datetime.now().isoformat()
            self.save_group(group)

        return group

    def get_groups_for_user(self, user_name):
        return [
            group
            for group in self.get_all_groups()
            if user_name in (group.get("users") or [])
        ]

    # Expense Operations
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
        existed = key in self.data
        self.data.pop(key, None)
        return existed and key not in self.data.keys()

    def delete_expense_record(self, expense_id):
        key = f"expense:{expense_id}"
        existed = key in self.data
        self.data.pop(key, None)
        return existed and key not in self.data.keys()

    def get_group_expenses(self, group_id):
        group = self.get_group(group_id)
        if not group:
            return []

        return [
            {
                "id": expense.get("id"),
                "name": expense.get("name"),
                "group": expense.get("group"),
                "amount": expense.get("amount"),
                "payer": expense.get("payer"),
                "sharers": expense.get("sharers"),
            }
            for expense in self.get_all_expenses()
            if expense.get("group") == group["name"]
        ]

    def get_user_paid_expenses(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return []

        return [
            expense
            for expense in self.get_all_expenses()
            if expense.get("payer") == user["name"]
        ]

    # Settlement Operations
    def save_group_settlements(self, settlement, key):
        self.data[key] = settlement
        return settlement

    def get_all_group_settlements(self):
        return {
            key: value
            for key, value in self.data.items()
            if key.startswith("settlement-group:")
        }

    def get_group_settlements(self, group_id):
        return self.data.get(f"settlement-group:{group_id}")

    def save_settlement_payment(self, group_id, payment_dict):
        key = f"settlement-payment-group:{group_id}"
        payments = self.data.get(key, [])
        payment_dict = dict(payment_dict)
        if "id" not in payment_dict:
            payment_dict["id"] = str(uuid.uuid4())
        if "created_at" not in payment_dict:
            payment_dict["created_at"] = datetime.now().isoformat()
        payments.append(payment_dict)
        self.data[key] = payments
        return payment_dict

    def get_group_settlement_payments(self, group_id):
        return self.data.get(f"settlement-payment-group:{group_id}", [])


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
    import routes.expenses as expenses_module
    import routes.settlements as settlements_module
    import routes.telegram as telegram_module

    mock_service = MockRedisService()

    # Patch in all modules that import redis_service
    monkeypatch.setattr(redis_module, "redis_service", mock_service)
    monkeypatch.setattr(users_module, "redis_service", mock_service)
    monkeypatch.setattr(groups_module, "redis_service", mock_service)
    monkeypatch.setattr(expenses_module, "redis_service", mock_service)
    monkeypatch.setattr(settlements_module, "redis_service", mock_service)
    monkeypatch.setattr(telegram_module, "redis_service", mock_service)

    yield mock_service

    # Cleanup after test
    mock_service.data.clear()
