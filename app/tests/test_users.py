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
