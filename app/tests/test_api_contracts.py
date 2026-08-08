from datetime import datetime
from uuid import UUID


def assert_iso_datetime(value):
    assert isinstance(value, str)
    datetime.fromisoformat(value)


def assert_uuid(value):
    assert isinstance(value, str)
    UUID(value)


def assert_number(value):
    assert isinstance(value, (int, float))
    assert not isinstance(value, bool)


def assert_user_contract(user, *, name=None, email=None):
    assert set(user) >= {"id", "name", "email", "created_at"}
    assert_uuid(user["id"])
    assert isinstance(user["name"], str)
    assert isinstance(user["email"], str)
    assert_iso_datetime(user["created_at"])

    if name is not None:
        assert user["name"] == name
    if email is not None:
        assert user["email"] == email


def assert_group_contract(group, *, name=None, users=None):
    assert set(group) >= {"id", "name", "users", "created_at"}
    assert_uuid(group["id"])
    assert isinstance(group["name"], str)
    assert isinstance(group["users"], list)
    assert all(isinstance(user_name, str) for user_name in group["users"])
    assert_iso_datetime(group["created_at"])

    if name is not None:
        assert group["name"] == name
    if users is not None:
        assert group["users"] == users


def assert_expense_contract(expense, *, name=None, group=None, payer=None):
    assert set(expense) >= {
        "id",
        "name",
        "group",
        "amount",
        "payer",
        "sharers",
    }
    assert_uuid(expense["id"])
    assert isinstance(expense["name"], str)
    assert isinstance(expense["group"], str)
    assert_number(expense["amount"])
    assert isinstance(expense["payer"], str)
    assert isinstance(expense["sharers"], list)
    assert all(isinstance(sharer, str) for sharer in expense["sharers"])

    if "created_at" in expense:
        assert_iso_datetime(expense["created_at"])
    if "group_id" in expense:
        assert expense["group_id"] is None or isinstance(expense["group_id"], str)

    if name is not None:
        assert expense["name"] == name
    if group is not None:
        assert expense["group"] == group
    if payer is not None:
        assert expense["payer"] == payer


def assert_settlement_contract(settlements, *, named):
    assert isinstance(settlements, list)

    for settlement in settlements:
        assert isinstance(settlement, list)
        assert len(settlement) == 3

        debtor, creditor, amount = settlement
        if named:
            assert isinstance(debtor, str)
            assert isinstance(creditor, str)
        else:
            assert isinstance(debtor, int)
            assert isinstance(creditor, int)
        assert_number(amount)


def assert_error_contract(response, expected_status):
    assert response.status_code == expected_status
    data = response.get_json()

    assert set(data) == {"error"}
    assert isinstance(data["error"], str)
    assert data["error"]


def create_expense(client, payload):
    response = client.post("/expenses/", json=payload)
    assert response.status_code == 201
    return response.get_json()


def test_root_response_contract(client):
    response = client.get("/")

    assert response.status_code == 200
    data = response.get_json()

    assert set(data) == {"message", "version", "status", "endpoints"}
    assert data["message"] == "ChipIn API"
    assert isinstance(data["version"], str)
    assert data["status"] == "running"
    assert data["endpoints"] == {
        "users": "/users/",
        "groups": "/groups/",
        "expenses": "/expenses/",
        "settlements": "/settlements/",
        "admin": "/admin/",
        "telegram_client": "/telegram/",
        "telegram_webhook": "/telegram/webhook/",
    }


def test_user_and_group_response_contracts(client):
    alice_response = client.post(
        "/users/",
        json={"name": "Alice", "email": "alice@example.com"},
    )
    bob_response = client.post(
        "/users/",
        json={"name": "Bob", "email": "bob@example.com"},
    )

    assert alice_response.status_code == 201
    assert bob_response.status_code == 201
    alice = alice_response.get_json()
    bob = bob_response.get_json()
    assert_user_contract(alice, name="Alice", email="alice@example.com")
    assert_user_contract(bob, name="Bob", email="bob@example.com")

    users_response = client.get("/users/")
    assert users_response.status_code == 200
    users = users_response.get_json()
    assert isinstance(users, list)
    assert len(users) == 2
    for user in users:
        assert_user_contract(user)

    user_detail_response = client.get(f"/users/{alice['id']}/")
    assert user_detail_response.status_code == 200
    assert_user_contract(
        user_detail_response.get_json(),
        name="Alice",
        email="alice@example.com",
    )

    user_attr_response = client.get(f"/users/{alice['id']}/name/")
    assert user_attr_response.status_code == 200
    assert user_attr_response.get_json() == "Alice"

    user_names_response = client.get("/users/user-names/")
    assert user_names_response.status_code == 200
    assert user_names_response.get_json() == ["Alice", "Bob"]

    group_response = client.post(
        "/groups/",
        json={"name": "Trip", "users": ["Alice", "Bob"]},
    )
    assert group_response.status_code == 201
    group = group_response.get_json()
    assert_group_contract(group, name="Trip", users=["Alice", "Bob"])

    groups_response = client.get("/groups/")
    assert groups_response.status_code == 200
    groups = groups_response.get_json()
    assert isinstance(groups, list)
    assert len(groups) == 1
    assert_group_contract(groups[0], name="Trip", users=["Alice", "Bob"])

    group_detail_response = client.get(f"/groups/{group['id']}/")
    assert group_detail_response.status_code == 200
    assert_group_contract(
        group_detail_response.get_json(),
        name="Trip",
        users=["Alice", "Bob"],
    )

    group_attr_response = client.get(f"/groups/{group['id']}/name/")
    assert group_attr_response.status_code == 200
    assert group_attr_response.get_json() == "Trip"


def test_expense_and_settlement_response_contracts(client, create_group):
    group = create_group(name="Trip", users=["Alice", "Bob"])
    expense_data = create_expense(
        client,
        {
            "name": "Dinner",
            "group": "Trip",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )

    assert set(expense_data) == {"saved_expense", "group_settlement"}
    expense = expense_data["saved_expense"]
    assert_expense_contract(expense, name="Dinner", group="Trip", payer="Alice")
    assert_settlement_contract(expense_data["group_settlement"], named=False)
    assert expense_data["group_settlement"] == [[1, 0, 15.0]]

    expense_detail_response = client.get(f"/expenses/{expense['id']}/")
    assert expense_detail_response.status_code == 200
    assert_expense_contract(
        expense_detail_response.get_json(),
        name="Dinner",
        group="Trip",
        payer="Alice",
    )

    expenses_response = client.get("/expenses/")
    assert expenses_response.status_code == 200
    expenses = expenses_response.get_json()
    assert isinstance(expenses, list)
    assert len(expenses) == 1
    assert_expense_contract(expenses[0], name="Dinner", group="Trip", payer="Alice")

    group_expenses_response = client.get(f"/expenses/group/{group['id']}/")
    assert group_expenses_response.status_code == 200
    group_expenses = group_expenses_response.get_json()
    assert isinstance(group_expenses, list)
    assert len(group_expenses) == 1
    assert_expense_contract(
        group_expenses[0],
        name="Dinner",
        group="Trip",
        payer="Alice",
    )
    assert "group_id" in group_expenses[0]

    paid_expenses_response = client.get(f"/expenses/user/paid/{group['id']}/")
    assert paid_expenses_response.status_code == 404

    alice_id = next(
        user["id"]
        for user in client.get("/users/").get_json()
        if user["name"] == "Alice"
    )
    paid_expenses_response = client.get(f"/expenses/user/paid/{alice_id}/")
    assert paid_expenses_response.status_code == 200
    paid_expenses = paid_expenses_response.get_json()
    assert isinstance(paid_expenses, list)
    assert len(paid_expenses) == 1
    assert_expense_contract(paid_expenses[0], name="Dinner", group="Trip", payer="Alice")

    group_settlement_response = client.get(f"/settlements/group/{group['id']}/")
    assert group_settlement_response.status_code == 200
    group_settlement_data = group_settlement_response.get_json()
    assert set(group_settlement_data) == {"settlements_this_group"}
    assert_settlement_contract(
        group_settlement_data["settlements_this_group"],
        named=True,
    )
    assert group_settlement_data["settlements_this_group"] == [["Bob", "Alice", 15.0]]

    all_settlements_response = client.get("/settlements/group/")
    assert all_settlements_response.status_code == 200
    all_settlements = all_settlements_response.get_json()
    assert set(all_settlements) == {f"settlement-group:{group['id']}"}
    assert_settlement_contract(
        all_settlements[f"settlement-group:{group['id']}"],
        named=True,
    )


def test_common_error_response_contracts(client, create_group):
    create_group(name="Trip", users=["Alice", "Bob"])

    error_cases = [
        (client.get("/users/not-found/"), 404),
        (client.get("/groups/not-found/"), 404),
        (client.get("/expenses/not-found/"), 404),
        (client.get("/expenses/group/not-found/"), 404),
        (client.get("/expenses/user/paid/not-found/"), 404),
        (client.get("/settlements/group/not-found/"), 404),
        (client.get("/settlements/user/not-found/"), 404),
        (client.post("/users/", json={"name": "Missing Email"}), 400),
        (client.post("/groups/", json={"name": "Missing Users"}), 400),
        (
            client.post(
                "/expenses/",
                json={"name": "Missing Payer", "group": "Trip", "amount": 30},
            ),
            400,
        ),
        (
            client.post(
                "/expenses/",
                json={
                    "name": "Bad Sharer",
                    "group": "Trip",
                    "amount": 30,
                    "payer": "Alice",
                    "sharers": ["Alice", "Charlie"],
                },
            ),
            404,
        ),
    ]

    for response, expected_status in error_cases:
        assert_error_contract(response, expected_status)
