from models.expense import Expense
from models.group import Group
from models.user import User


def test_user_to_dict_includes_expected_fields():
    user = User(name="Alice", email="alice@example.com", uid="user-1")

    data = user.to_dict()

    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert data["id"] == "user-1"
    assert "created_at" in data


def test_user_from_dict_preserves_identity_fields():
    user = User.from_dict(
        {
            "name": "Alice",
            "email": "alice@example.com",
            "id": "user-1",
        }
    )

    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.uid == "user-1"


def test_group_to_dict_includes_expected_fields():
    group = Group(name="Calgary", users=["Alice", "Bob"], uid="group-1")

    data = group.to_dict()

    assert data["name"] == "Calgary"
    assert data["users"] == ["Alice", "Bob"]
    assert data["id"] == "group-1"
    assert "created_at" in data


def test_group_from_dict_preserves_identity_fields():
    group = Group.from_dict(
        {
            "name": "Calgary",
            "users": ["Alice", "Bob"],
            "id": "group-1",
        }
    )

    assert group.name == "Calgary"
    assert group.users == ["Alice", "Bob"]
    assert group.uid == "group-1"


def test_expense_to_dict_includes_expected_fields():
    expense = Expense(
        name="Dinner",
        group="Calgary",
        amount=30,
        payer="Alice",
        sharers=["Alice", "Bob"],
        uid="expense-1",
    )

    data = expense.to_dict()

    assert data["name"] == "Dinner"
    assert data["group"] == "Calgary"
    assert data["amount"] == 30
    assert data["payer"] == "Alice"
    assert data["sharers"] == ["Alice", "Bob"]
    assert data["id"] == "expense-1"
    assert "created_at" in data


def test_expense_from_dict_preserves_identity_fields():
    expense = Expense.from_dict(
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
            "id": "expense-1",
        }
    )

    assert expense.name == "Dinner"
    assert expense.group == "Calgary"
    assert expense.amount == 30
    assert expense.payer == "Alice"
    assert expense.sharers == ["Alice", "Bob"]
    assert expense.uid == "expense-1"
