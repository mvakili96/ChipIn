def test_web_client_served(client):
    response = client.get("/client")

    assert response.status_code == 200
    assert b"ChipIn Client" in response.data


def test_web_client_assets_served(client):
    response = client.get("/static/client/app.js")

    assert response.status_code == 200
    assert b"refreshData" in response.data
