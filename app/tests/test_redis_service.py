from services.redis_service import RedisService


def test_escape_tag_value_escapes_redisearch_special_characters():
    assert RedisService._escape_tag_value("Alice Bob") == "Alice\\ Bob"
    assert RedisService._escape_tag_value("a,b@example.com") == (
        "a\\,b\\@example\\.com"
    )
    assert RedisService._escape_tag_value("Group-1") == "Group\\-1"


def test_expense_summary_returns_public_expense_fields_only():
    expense = {
        "id": "expense-1",
        "name": "Dinner",
        "group": "Calgary",
        "amount": 30,
        "payer": "Alice",
        "sharers": ["Alice", "Bob"],
        "created_at": "2026-06-21T00:00:00",
        "internal": "ignored",
    }

    assert RedisService._expense_summary(expense) == {
        "id": "expense-1",
        "name": "Dinner",
        "group": "Calgary",
        "amount": 30,
        "payer": "Alice",
        "sharers": ["Alice", "Bob"],
    }


def test_expense_summary_uses_none_for_missing_public_fields():
    assert RedisService._expense_summary({"id": "expense-1"}) == {
        "id": "expense-1",
        "name": None,
        "group": None,
        "amount": None,
        "payer": None,
        "sharers": None,
    }
