import json


def post_expense(client, payload):
    return client.post(
        "/expenses/",
        data=json.dumps(payload),
        content_type="application/json",
    )


def test_create_expense_with_explicit_sharers(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob", "Carol"])

    response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["saved_expense"]["name"] == "Dinner"
    assert data["saved_expense"]["group"] == "Calgary"
    assert data["saved_expense"]["amount"] == 30
    assert data["saved_expense"]["payer"] == "Alice"
    assert data["saved_expense"]["sharers"] == ["Alice", "Bob"]
    assert "id" in data["saved_expense"]
    assert "created_at" in data["saved_expense"]
    assert data["group_settlement"] == [[1, 0, 15.0]]


def test_create_expense_defaults_sharers_to_group_users(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob", "Carol"])

    response = post_expense(
        client,
        {
            "name": "Groceries",
            "group": "Calgary",
            "amount": 60,
            "payer": "Alice",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["saved_expense"]["sharers"] == ["Alice", "Bob", "Carol"]
    assert data["group_settlement"] == [[1, 0, 20.0], [2, 0, 20.0]]


def test_create_expense_missing_required_fields(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])

    required_payload = {
        "name": "Dinner",
        "group": "Calgary",
        "amount": 30,
        "payer": "Alice",
    }

    for field in required_payload:
        payload = required_payload.copy()
        payload.pop(field)

        response = post_expense(client, payload)

        assert response.status_code == 400
        assert response.get_json() == {"error": f"Invalid request: missing {field}"}


def test_create_expense_group_not_found(client):
    response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Missing Group",
            "amount": 30,
            "payer": "Alice",
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Group linked to this expense is not found"
    }


def test_create_expense_payer_not_in_group(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])

    response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Carol",
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Payer is not found in the linked Group"}


def test_create_expense_sharer_not_in_group(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])

    response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Carol"],
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "One or more sharers not found in the linked Group"
    }


def test_get_expenses(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )
    post_expense(
        client,
        {
            "name": "Coffee",
            "group": "Calgary",
            "amount": 8,
            "payer": "Bob",
            "sharers": ["Alice", "Bob"],
        },
    )

    response = client.get("/expenses/")

    assert response.status_code == 200
    data = response.get_json()
    expenses_by_name = {expense["name"]: expense for expense in data}
    assert set(expenses_by_name) == {"Dinner", "Coffee"}
    assert expenses_by_name["Dinner"]["payer"] == "Alice"
    assert expenses_by_name["Coffee"]["payer"] == "Bob"


def test_get_expense_and_attr(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])
    create_response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )
    expense = create_response.get_json()["saved_expense"]

    response = client.get(f"/expenses/{expense['id']}/")

    assert response.status_code == 200
    assert response.get_json() == expense

    response = client.get(f"/expenses/{expense['id']}/payer/")
    assert response.status_code == 200
    assert response.get_json() == "Alice"


def test_get_expense_not_found(client):
    response = client.get("/expenses/999/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Expense not found"}


def test_get_expense_attr_not_found(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])
    create_response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )
    expense = create_response.get_json()["saved_expense"]

    response = client.get(f"/expenses/{expense['id']}/missing/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Expense or key not found"}


def test_get_group_expenses(client, create_group):
    group = create_group(name="Calgary", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )

    response = client.get(f"/expenses/group/{group['id']}/")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data == [
        {
            "id": data[0]["id"],
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        }
    ]


def test_get_group_expenses_group_not_found(client):
    response = client.get("/expenses/group/999/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Group not found"}


def test_get_user_paid_expenses(client, create_group, mock_redis_service):
    create_group(name="Calgary", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )
    alice = next(
        user
        for user in mock_redis_service.get_all_users()
        if user["name"] == "Alice"
    )

    response = client.get(f"/expenses/user/paid/{alice['id']}/")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Dinner"
    assert data[0]["payer"] == "Alice"


def test_get_user_paid_expenses_user_not_found(client):
    response = client.get("/expenses/user/paid/999/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}


def test_delete_expense(client, create_group):
    create_group(name="Calgary", users=["Alice", "Bob"])
    create_response = post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 30,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )
    expense = create_response.get_json()["saved_expense"]

    response = client.delete(f"/expenses/{expense['id']}/")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": f"Expense {expense['id']} deleted successfully"
    }

    response = client.get(f"/expenses/{expense['id']}/")
    assert response.status_code == 404


def test_delete_expense_not_found(client):
    response = client.delete("/expenses/999/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Expense not found"}
