import pytest

from models.settlement import Settlement


def test_settlement_with_no_expenses_returns_empty_list():
    assert Settlement([], ["Alice", "Bob"]) == []


def test_settlement_splits_one_expense_between_two_users():
    expenses = [
        {
            "amount": 20,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        }
    ]

    assert Settlement(expenses, ["Alice", "Bob"]) == [(1, 0, pytest.approx(10))]


def test_settlement_splits_one_expense_among_three_users():
    expenses = [
        {
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob", "Carol"],
        }
    ]

    assert Settlement(expenses, ["Alice", "Bob", "Carol"]) == [
        (1, 0, pytest.approx(10)),
        (2, 0, pytest.approx(10)),
    ]


def test_settlement_offsets_multiple_expenses():
    expenses = [
        {
            "amount": 20,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
        {
            "amount": 8,
            "payer": "Bob",
            "sharers": ["Alice", "Bob"],
        },
    ]

    assert Settlement(expenses, ["Alice", "Bob"]) == [(1, 0, pytest.approx(6))]


def test_settlement_applies_existing_transaction_history():
    expenses = [
        {
            "amount": 8,
            "payer": "Bob",
            "sharers": ["Alice", "Bob"],
        }
    ]
    tx_hist = [(1, 0, 10)]

    assert Settlement(expenses, ["Alice", "Bob"], tx_hist) == [
        (1, 0, pytest.approx(6))
    ]
