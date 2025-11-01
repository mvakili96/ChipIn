import json


def test_create_user(client):
    """Test creating a new user"""
    response = client.post(
        "/users/",
        data=json.dumps({"name": "agha vakili", "email": "mjvk@example.com"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
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
    data = json.loads(response.data)
    assert "error" in data


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
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "User 1"
    assert data[0]["email"] == "user1@example.com"
    assert "id" in data[0]
    assert "created_at" in data[0]
    assert data[1]["name"] == "User 2"
    assert data[1]["email"] == "user2@example.com"
    assert "id" in data[1]
    assert "created_at" in data[1]


def test_get_user(client):
    """Test getting a single user"""
    # Create a user
    response = client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)

    # Get the user
    response = client.get(f"/users/{data['id']}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "User 1"
    assert data["email"] == "user1@example.com"
    assert "id" in data
    assert "created_at" in data


def test_get_user_not_found(client):
    """Test getting a single user that does not exist"""

    # Get the user
    response = client.get("/users/999")
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data


def test_get_user_names(client):
    """Test getting a single user's names"""
    # Create a user
    response = client.post(
        "/users/",
        data=json.dumps({"name": "User 1", "email": "user1@example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)

    # Get the user's names
    response = client.get("/users/user-names")
    assert response.status_code == 200
    data = json.loads(response.data)
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
    data = json.loads(response.data)

    # Get the user's attributes
    for k in ["name", "email"]:
        response = client.get(f"/users/{data['id']}/{k}")
        assert response.status_code == 200
        this_data = response.data.decode("utf-8")
        assert this_data == data[k]
