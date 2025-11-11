import json


def test_create_group(client):
    """Test creating a new group"""
    # Create 2 users
    client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "Moein", "email": "moe@example.com"}),
        content_type="application/json",
    )

    # Create a group
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "users": ["agha vakili", "Moein"]}),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["name"] == "Calgary"
    assert data["users"] == ["agha vakili", "Moein"]
    assert "id" in data
    assert "created_at" in data


def test_create_group_missing_fields(client):
    """Test creating group with missing fields"""
    # Create 2 users
    client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "Moein", "email": "moe@example.com"}),
        content_type="application/json",
    )

    # Create a group
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_create_group_missing_users(client):
    """Test creating a new group when users/name are missing"""

    # Create a group with name missing in data
    response = client.post(
        "/groups/",
        data=json.dumps({"users": ["unregistered", "Moein"]}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Invalid request: missing name or users"

    # Create a group with users missing in data
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "use": ["Moein"]}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Invalid request: missing name or users"


def test_create_group_user_not_found(client):
    """Test creating a new group when a user is not found"""
    # Create a user
    client.post(
        "/users/",
        data=json.dumps({"name": "Moein", "email": "moe@example.com"}),
        content_type="application/json",
    )

    # Create a group
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "users": ["unregistered", "Moein"]}),
        content_type="application/json",
    )

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "One or more names not found"


def test_get_groups(client):
    """Test getting all groups"""
    # Create 5 users
    client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "Moein", "email": "moe@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "User 2", "email": "user2@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "User 3", "email": "user3@example.com"}),
        content_type="application/json",
    )

    # Create a group
    # Create multiple groups
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "users": ["agha vakili", "Moein"]}),
        content_type="application/json",
    )
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Vancouver", "users": ["User 1", "User 2", "User 3"]}),
        content_type="application/json",
    )
    response = client.get("/groups/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "Calgary"
    assert data[0]["users"] == ["agha vakili", "Moein"]
    assert "id" in data[0]
    assert "created_at" in data[0]
    assert data[1]["name"] == "Vancouver"
    assert data[1]["users"] == ["User 1", "User 2", "User 3"]
    assert "id" in data[1]
    assert "created_at" in data[1]


def test_get_group(client):
    """Test getting a single group"""
    # Create 2 users
    client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "Moein", "email": "moe@example.com"}),
        content_type="application/json",
    )

    # Create a group
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "users": ["agha vakili", "Moein"]}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)

    # Get the group
    response = client.get(f"/groups/{data['id']}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "Calgary"
    assert data["users"] == ["agha vakili", "Moein"]
    assert "id" in data
    assert "created_at" in data


def test_get_group_not_found(client):
    """Test getting a single group that does not exist"""

    # Get the group
    response = client.get("/groups/999")
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data


def test_get_group_attr(client):
    """Test getting a single group's attributes"""
    # Create 2 users
    client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )
    client.post(
        "/users/",
        data=json.dumps({"name": "Moein", "email": "moe@example.com"}),
        content_type="application/json",
    )

    # Create a group
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "users": ["agha vakili", "Moein"]}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)

    # Get the group's attributes
    for k in ["name", "users"]:
        response = client.get(f"/groups/{data['id']}/{k}")
        assert response.status_code == 200

        this_data = response.get_json()
        assert this_data == data[k]
