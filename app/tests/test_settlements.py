import json


def post_expense(client, payload):
    return client.post(
        "/expenses/",
        data=json.dumps(payload),
        content_type="application/json",
    )


def user_by_name(mock_redis_service, name):
    return next(
        user
        for user in mock_redis_service.get_all_users()
        if user["name"] == name
    )


def test_get_all_group_settlements(client, create_group):
    group = create_group(name="Calgary", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 20,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )

    response = client.get("/settlements/group/")

    assert response.status_code == 200
    assert response.get_json() == {
        f"settlement-group:{group['id']}": [["Bob", "Alice", 10.0]]
    }


def test_get_group_settlements_from_stored_history(client, create_group):
    group = create_group(name="Calgary", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 20,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )

    response = client.get(f"/settlements/group/{group['id']}/")

    assert response.status_code == 200
    assert response.get_json() == {
        "settlements_this_group": [["Bob", "Alice", 10.0]]
    }


def test_get_group_settlements_computes_from_expenses_without_history(
    client, create_group, mock_redis_service
):
    group = create_group(name="Calgary", users=["Alice", "Bob"])
    mock_redis_service.save_expense(
        {
            "id": "expense-1",
            "name": "Dinner",
            "group": "Calgary",
            "amount": 20,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
            "created_at": "2026-06-21T00:00:00",
        }
    )

    response = client.get(f"/settlements/group/{group['id']}/")

    assert response.status_code == 200
    assert response.get_json() == {
        "settlements_this_group": [["Bob", "Alice", 10.0]]
    }


def test_get_group_settlements_with_no_expenses(client, create_group):
    group = create_group(name="Calgary", users=["Alice", "Bob"])

    response = client.get(f"/settlements/group/{group['id']}/")

    assert response.status_code == 404
    assert response.get_json() == {
        "warning": "There are no expenses linked to this group"
    }


def test_get_group_settlements_group_not_found(client):
    response = client.get("/settlements/group/999/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Group and its settlements not found"}


def test_get_user_settlements_merges_across_groups(
    client, create_group, mock_redis_service
):
    create_group(name="Calgary", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Dinner",
            "group": "Calgary",
            "amount": 20,
            "payer": "Alice",
            "sharers": ["Alice", "Bob"],
        },
    )
    create_group(name="Vancouver", users=["Alice", "Bob"])
    post_expense(
        client,
        {
            "name": "Coffee",
            "group": "Vancouver",
            "amount": 8,
            "payer": "Bob",
            "sharers": ["Alice", "Bob"],
        },
    )
    alice = user_by_name(mock_redis_service, "Alice")

    response = client.get(f"/settlements/user/{alice['id']}/")

    assert response.status_code == 200
    assert response.get_json() == {
        "settlements_this_user": [["Bob", "Alice", 6.0]]
    }


def test_get_user_settlements_user_not_found(client):
    response = client.get("/settlements/user/999/")

    assert response.status_code == 404
    assert response.get_json() == {"error": "User not found"}
