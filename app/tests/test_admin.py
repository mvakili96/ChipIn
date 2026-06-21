def test_admin_panel_served(client):
    response = client.get("/admin/")

    assert response.status_code == 200
    assert b"ChipIn Admin" in response.data


def test_admin_panel_references_static_assets(client):
    response = client.get("/admin/")

    assert response.status_code == 200
    assert b'href="/static/admin/chipin-mark.svg"' in response.data
    assert b'href="/static/admin/styles.css"' in response.data
    assert b'src="/static/admin/app.js"' in response.data


def test_admin_panel_adds_trailing_slash(client):
    response = client.get("/admin")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/admin/")


def test_admin_panel_assets_served(client):
    response = client.get("/static/admin/app.js")

    assert response.status_code == 200
    assert b"refreshData" in response.data


def test_admin_stylesheet_served(client):
    response = client.get("/static/admin/styles.css")

    assert response.status_code == 200
    assert b".app-shell" in response.data


def test_admin_mark_served(client):
    response = client.get("/static/admin/chipin-mark.svg")

    assert response.status_code == 200
    assert b"<svg" in response.data


def test_admin_script_references_api_routes(client):
    response = client.get("/static/admin/app.js")

    assert response.status_code == 200
    assert b'"/users/"' in response.data
    assert b'"/groups/"' in response.data
    assert b'"/expenses/"' in response.data
    assert b'"/settlements/group/"' in response.data


def test_client_route_removed(client):
    response = client.get("/client")

    assert response.status_code == 404
