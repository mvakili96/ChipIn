def test_admin_panel_served(client):
    response = client.get("/admin")

    assert response.status_code == 200
    assert b"ChipIn Admin" in response.data


def test_admin_panel_assets_served(client):
    response = client.get("/static/admin/app.js")

    assert response.status_code == 200
    assert b"refreshData" in response.data


def test_legacy_web_client_redirects_to_admin(client):
    response = client.get("/client")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/admin")
