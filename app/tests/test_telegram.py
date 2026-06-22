import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, urlencode, urlparse


BOT_TOKEN = "123456:test-token"


def make_init_data(user, chat=None, auth_date=None, bot_token=BOT_TOKEN):
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "user": json.dumps(user, separators=(",", ":")),
    }
    if chat is not None:
        fields["chat"] = json.dumps(chat, separators=(",", ":"))

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    fields["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return urlencode(fields)


def auth_headers(init_data):
    return {"X-Telegram-Init-Data": init_data}


def test_telegram_client_served(client):
    response = client.get("/telegram/")

    assert response.status_code == 200
    assert b"ChipIn" in response.data


def test_telegram_client_adds_trailing_slash(client):
    response = client.get("/telegram")

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/telegram/")


def test_telegram_auth_valid_init_data_upserts_user(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    init_data = make_init_data(
        {"id": 1001, "first_name": "Moein", "username": "moein"}
    )

    response = client.post(
        "/telegram/auth/",
        data=json.dumps({"init_data": init_data}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["name"] == "Moein"
    assert data["user"]["telegram_id"] == "1001"
    assert data["groups"] == []


def test_telegram_auth_links_existing_user_by_display_name(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    existing_user = mock_redis_service.save_user(
        {
            "name": "Moein",
            "email": "moein@example.com",
            "id": "existing-user-id",
            "created_at": "2026-06-21T00:00:00",
        }
    )
    init_data = make_init_data(
        {"id": 1001, "first_name": "Moein", "username": "moein"}
    )

    response = client.post(
        "/telegram/auth/",
        data=json.dumps({"init_data": init_data}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    linked_user = mock_redis_service.get_user(existing_user["id"])
    assert data["user"]["id"] == "existing-user-id"
    assert linked_user["telegram_id"] == "1001"
    assert linked_user["telegram_username"] == "moein"
    assert linked_user["email"] == "moein@example.com"
    assert "telegram_linked_at" in linked_user


def test_telegram_auth_does_not_duplicate_matching_existing_user(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    mock_redis_service.save_user(
        {
            "name": "Moein",
            "email": "moein@example.com",
            "id": "existing-user-id",
            "created_at": "2026-06-21T00:00:00",
        }
    )
    init_data = make_init_data(
        {"id": 1001, "first_name": "Moein", "username": "moein"}
    )

    response = client.post(
        "/telegram/auth/",
        data=json.dumps({"init_data": init_data}),
        content_type="application/json",
    )

    assert response.status_code == 200
    users = mock_redis_service.get_all_users()
    assert len(users) == 1
    assert users[0]["id"] == "existing-user-id"
    assert users[0]["telegram_id"] == "1001"


def test_telegram_auth_rejects_tampered_init_data(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    init_data = make_init_data({"id": 1001, "first_name": "Moein"})
    tampered = init_data.replace("Moein", "Other")

    response = client.post(
        "/telegram/auth/",
        data=json.dumps({"init_data": tampered}),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid Telegram hash"


def test_telegram_auth_creates_group_from_chat_and_self_joins(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    init_data = make_init_data(
        {"id": 1001, "first_name": "Moein"},
        {"id": -2001, "type": "group", "title": "Calgary Trip"},
    )

    response = client.post(
        "/telegram/auth/",
        data=json.dumps({"init_data": init_data}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["launch_group"]["name"] == "Calgary Trip"
    assert data["launch_group"]["source"] == "telegram"
    assert data["launch_group"]["telegram_chat_id"] == "-2001"
    assert data["launch_group"]["users"] == ["Moein"]
    assert data["groups"][0]["id"] == data["launch_group"]["id"]


def test_telegram_expense_creation_uses_authenticated_user(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    init_data = make_init_data(
        {"id": 1001, "first_name": "Moein"},
        {"id": -2001, "type": "group", "title": "Calgary Trip"},
    )
    auth_response = client.post(
        "/telegram/auth/",
        data=json.dumps({"init_data": init_data}),
        content_type="application/json",
    )
    group = auth_response.get_json()["launch_group"]

    bob = mock_redis_service.save_user(
        {
            "name": "Bob",
            "email": "bob@example.com",
            "id": "bob-id",
            "created_at": "2026-06-21T00:00:00",
        }
    )
    mock_redis_service.add_user_to_group(group["id"], bob["name"])

    response = client.post(
        "/telegram/api/expenses/",
        data=json.dumps(
            {
                "group_id": group["id"],
                "name": "Dinner",
                "amount": 20,
                "sharers": ["Moein", "Bob"],
            }
        ),
        content_type="application/json",
        headers=auth_headers(init_data),
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["saved_expense"]["payer"] == "Moein"
    assert data["saved_expense"]["group"] == "Calgary Trip"
    assert data["group_settlement"] == [["Bob", "Moein", 10.0]]


def test_telegram_webhook_requires_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": 1}),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_telegram_webhook_links_group_and_sends_button(client, monkeypatch):
    import routes.telegram as telegram_module

    class FakeBot:
        def __init__(self):
            self.messages = []

        def send_message(self, chat_id, text, reply_markup=None):
            self.messages.append(
                {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
            )

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://chipin.example")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "chipin_test_bot")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps(
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": -2001, "type": "group", "title": "Calgary Trip"},
                    "from": {"id": 1001, "first_name": "Moein"},
                    "text": "/chipin",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert len(fake_bot.messages) == 1
    assert fake_bot.messages[0]["chat_id"] == -2001
    button = fake_bot.messages[0]["reply_markup"]["inline_keyboard"][0][0]
    parsed_url = urlparse(button["url"])
    assert f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}" == (
        "https://t.me/chipin_test_bot"
    )
    assert parse_qs(parsed_url.query)["start"][0].startswith("group_")


def test_telegram_private_start_payload_joins_group_and_sends_web_app(
    client, monkeypatch, mock_redis_service
):
    import routes.telegram as telegram_module

    class FakeBot:
        def __init__(self):
            self.messages = []

        def send_message(self, chat_id, text, reply_markup=None):
            self.messages.append(
                {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
            )

    fake_bot = FakeBot()
    group = mock_redis_service.ensure_telegram_group(
        {"id": -2001, "type": "group", "title": "Calgary Trip"}
    )
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://chipin.example")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps(
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 1001, "type": "private", "first_name": "Moein"},
                    "from": {"id": 1001, "first_name": "Moein"},
                    "text": f"/start group_{group['id']}",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    linked_group = mock_redis_service.get_group(group["id"])
    assert linked_group["users"] == ["Moein"]
    button = fake_bot.messages[0]["reply_markup"]["inline_keyboard"][0][0]
    parsed_url = urlparse(button["web_app"]["url"])
    assert f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}" == (
        "https://chipin.example/telegram/"
    )
    assert parse_qs(parsed_url.query)["group_id"] == [group["id"]]
