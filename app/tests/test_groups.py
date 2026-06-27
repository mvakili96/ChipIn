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
    data = response.get_json()
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
    data = response.get_json()
    assert data == {"error": "Invalid request: missing name or users"}


def test_create_group_missing_users(client):
    """Test creating a new group when users/name are missing"""

    # Create a group with name missing in data
    response = client.post(
        "/groups/",
        data=json.dumps({"users": ["unregistered", "Moein"]}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Invalid request: missing name or users"

    # Create a group with users missing in data
    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "use": ["Moein"]}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.get_json()
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
    data = response.get_json()
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
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    groups_by_name = {group["name"]: group for group in data}
    assert set(groups_by_name) == {"Calgary", "Vancouver"}
    assert groups_by_name["Calgary"]["users"] == ["agha vakili", "Moein"]
    assert "id" in groups_by_name["Calgary"]
    assert "created_at" in groups_by_name["Calgary"]
    assert groups_by_name["Vancouver"]["users"] == ["User 1", "User 2", "User 3"]
    assert "id" in groups_by_name["Vancouver"]
    assert "created_at" in groups_by_name["Vancouver"]


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
    data = response.get_json()

    # Get the group
    response = client.get(f"/groups/{data['id']}/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Calgary"
    assert data["users"] == ["agha vakili", "Moein"]
    assert "id" in data
    assert "created_at" in data


def test_get_group_adds_trailing_slash(client):
    """Test group detail URLs redirect to their trailing-slash form"""
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

    response = client.post(
        "/groups/",
        data=json.dumps({"name": "Calgary", "users": ["agha vakili", "Moein"]}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()

    response = client.get(f"/groups/{data['id']}")

    assert response.status_code == 308
    assert response.headers["Location"].endswith(f"/groups/{data['id']}/")


def test_get_group_not_found(client):
    """Test getting a single group that does not exist"""

    # Get the group
    response = client.get("/groups/999/")
    assert response.status_code == 404
    data = response.get_json()
    assert data == {"error": "Group not found"}


def test_delete_group(client, create_group):
    """Test deleting an existing group"""
    group = create_group(name="Calgary", users=["agha vakili", "Moein"])

    response = client.delete(f"/groups/{group['id']}/")

    assert response.status_code == 200
    data = response.get_json()
    assert data == {"message": f"Group {group['id']} deleted successfully"}

    response = client.get(f"/groups/{group['id']}/")
    assert response.status_code == 404


def test_delete_group_not_found(client):
    """Test deleting a group that does not exist"""
    response = client.delete("/groups/999/")

    assert response.status_code == 404
    data = response.get_json()
    assert data == {"error": "Group not found"}


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
    data = response.get_json()

    # Get the group's attributes
    for k in ["name", "users"]:
        response = client.get(f"/groups/{data['id']}/{k}/")
        assert response.status_code == 200

        this_data = response.get_json()
        assert this_data == data[k]
