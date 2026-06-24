def test_home_api_metadata(client):
    response = client.get("/")

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "ChipIn API"
    assert data["status"] == "running"
    assert data["endpoints"] == {
        "users": "/users",
        "groups": "/groups",
        "expenses": "/expenses",
        "settlements": "/settlements",
        "admin": "/admin/",
    }
