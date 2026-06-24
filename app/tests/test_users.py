import json


def test_create_user(client):
    """Test creating a new user"""
    response = client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "agha vakili"
    assert data["email"] == "mjvk@example.com"
    assert "id" in data
    assert "created_at" in data


def test_create_user_missing_fields(client):
    """Test creating user with missing fields"""
    response = client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data == {"error": "Invalid request: missing name or email"}


def test_get_users(client):
    """Test getting all users"""
    # Create multiple users
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
    response = client.get("/users/")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    users_by_name = {user["name"]: user for user in data}
    assert set(users_by_name) == {"User 1", "User 2"}
    assert users_by_name["User 1"]["email"] == "user1@example.com"
    assert "id" in users_by_name["User 1"]
    assert "created_at" in users_by_name["User 1"]
    assert users_by_name["User 2"]["email"] == "user2@example.com"
    assert "id" in users_by_name["User 2"]
    assert "created_at" in users_by_name["User 2"]


def test_get_user(client):
    """Test getting a single user"""
    # Create a user
    response = client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()

    # Get the user
    response = client.get(f"/users/{data['id']}/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "User 1"
    assert data["email"] == "user1@example.com"
    assert "id" in data
    assert "created_at" in data


def test_get_user_adds_trailing_slash(client):
    """Test user detail URLs redirect to their trailing-slash form"""
    response = client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()

    response = client.get(f"/users/{data['id']}")

    assert response.status_code == 308
    assert response.headers["Location"].endswith(f"/users/{data['id']}/")


def test_get_user_not_found(client):
    """Test getting a single user that does not exist"""

    # Get the user
    response = client.get("/users/999/")
    assert response.status_code == 404
    data = response.get_json()
    assert data == {"error": "User not found"}


def test_get_user_names(client):
    """Test getting a single user's names"""
    # Create a user
    response = client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201

    # Get the user's names
    response = client.get("/users/user-names/")
    assert response.status_code == 200
    data = response.get_json()
    assert type(data) is list
    assert data[0] == "User 1"


def test_get_user_attr(client):
    """Test getting a single user's attributes"""
    # Create a user
    response = client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()

    # Get the user's attributes
    for k in ["name", "email"]:
        response = client.get(f"/users/{data['id']}/{k}/")
        this_data = response.get_json()
        assert response.status_code == 200
        assert this_data == data[k]
