def test_admin_panel_served(client):
    response = client.get("/admin/")

    assert response.status_code == 200
    assert b"ChipIn Admin" in response.data


def test_admin_panel_adds_trailing_slash(client):
    response = client.get("/admin")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/admin/")


def test_admin_panel_assets_served(client):
    response = client.get("/static/admin/app.js")

    assert response.status_code == 200
    assert b"refreshData" in response.data


def test_client_route_removed(client):
    response = client.get("/client")

    assert response.status_code == 404
