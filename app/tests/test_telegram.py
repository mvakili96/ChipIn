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


class FakeBot:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text, reply_markup=None):
        self.messages.append(
            {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        )


def save_manual_group(
    mock_redis_service,
    users=None,
    group_id="p2-group-id",
    name="P2 Trip",
    source="manual",
    telegram_chat_id=None,
):
    return mock_redis_service.save_group(
        {
            "name": name,
            "users": ["Moein", "Bob"] if users is None else users,
            "id": group_id,
            "created_at": "2026-06-21T00:00:00",
            "source": source,
            "telegram_chat_id": telegram_chat_id,
        }
    )


def create_telegram_expense(
    client,
    init_data,
    group_id,
    amount=20,
    sharers=None,
):
    response = client.post(
        "/telegram/api/expenses/",
        data=json.dumps(
            {
                "group_id": group_id,
                "name": "Dinner",
                "amount": amount,
                "sharers": sharers or ["Moein", "Bob"],
            }
        ),
        content_type="application/json",
        headers=auth_headers(init_data),
    )
    assert response.status_code == 201
    return response.get_json()["saved_expense"]


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


def test_telegram_create_group_from_chat_rejects_forged_body_chat(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    init_data = make_init_data({"id": 1001, "first_name": "Moein"})

    response = client.post(
        "/telegram/api/groups/from-chat/",
        data=json.dumps(
            {
                "chat": {
                    "id": -2001,
                    "type": "group",
                    "title": "Forged Group",
                }
            }
        ),
        content_type="application/json",
        headers=auth_headers(init_data),
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Telegram group chat context is required"
    assert mock_redis_service.get_all_groups() == []


def test_telegram_join_group_requires_verified_group_context(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    group = save_manual_group(
        mock_redis_service,
        users=[],
        group_id="telegram-group-id",
        name="Calgary Trip",
        source="telegram",
        telegram_chat_id="-2001",
    )
    private_init_data = make_init_data({"id": 1001, "first_name": "Moein"})

    response = client.post(
        f"/telegram/api/groups/{group['id']}/join/",
        headers=auth_headers(private_init_data),
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Verified Telegram group context is required"
    assert mock_redis_service.get_group(group["id"])["users"] == []


def test_telegram_join_group_accepts_verified_group_launch(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    group = save_manual_group(
        mock_redis_service,
        users=[],
        group_id="telegram-group-id",
        name="Calgary Trip",
        source="telegram",
        telegram_chat_id="-2001",
    )
    group_init_data = make_init_data(
        {"id": 1001, "first_name": "Moein"},
        {"id": -2001, "type": "group", "title": "Calgary Trip"},
    )

    response = client.post(
        f"/telegram/api/groups/{group['id']}/join/",
        headers=auth_headers(group_init_data),
    )

    assert response.status_code == 200
    assert response.get_json()["group"]["users"] == ["Moein"]


def test_telegram_expense_creation_uses_authenticated_user(
    client, monkeypatch, mock_redis_service
):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "chipin_test_bot")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)
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
    assert data["saved_expense"]["group_id"] == group["id"]
    assert data["group_settlement"] == [["Bob", "Moein", 10.0]]
    assert mock_redis_service.get_group_settlements(group["id"]) == [[1, 0, 10.0]]
    assert len(fake_bot.messages) == 1
    assert fake_bot.messages[0]["chat_id"] == "-2001"
    assert "Moein added <b>Dinner</b>" in fake_bot.messages[0]["text"]
    button = fake_bot.messages[0]["reply_markup"]["inline_keyboard"][0][0]
    assert button["url"].startswith("https://t.me/chipin_test_bot?start=group_")


def test_telegram_expense_update_requires_payer_and_recomputes_settlements(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    group = save_manual_group(mock_redis_service)
    moein_init_data = make_init_data({"id": 1001, "first_name": "Moein"})
    bob_init_data = make_init_data({"id": 1002, "first_name": "Bob"})
    expense = create_telegram_expense(client, moein_init_data, group["id"])

    forbidden_response = client.put(
        f"/telegram/api/expenses/{expense['id']}/",
        data=json.dumps({"amount": 30}),
        content_type="application/json",
        headers=auth_headers(bob_init_data),
    )

    assert forbidden_response.status_code == 403

    response = client.put(
        f"/telegram/api/expenses/{expense['id']}/",
        data=json.dumps(
            {
                "name": "Updated Dinner",
                "amount": 30,
                "sharers": ["Moein", "Bob"],
            }
        ),
        content_type="application/json",
        headers=auth_headers(moein_init_data),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["saved_expense"]["name"] == "Updated Dinner"
    assert data["saved_expense"]["amount"] == 30.0
    assert "updated_at" in data["saved_expense"]
    assert data["group_settlement"] == [["Bob", "Moein", 15.0]]
    assert mock_redis_service.get_group_settlements(group["id"]) == [[1, 0, 15.0]]


def test_telegram_expense_access_uses_group_id_with_duplicate_group_names(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    save_manual_group(
        mock_redis_service,
        users=["Moein", "Bob"],
        group_id="same-name-a",
        name="Same Name",
    )
    group = save_manual_group(
        mock_redis_service,
        users=["Moein", "Cara"],
        group_id="same-name-b",
        name="Same Name",
    )
    moein_init_data = make_init_data({"id": 1001, "first_name": "Moein"})
    expense = create_telegram_expense(
        client,
        moein_init_data,
        group["id"],
        sharers=["Moein", "Cara"],
    )

    response = client.put(
        f"/telegram/api/expenses/{expense['id']}/",
        data=json.dumps(
            {
                "amount": 40,
                "sharers": ["Moein", "Cara"],
            }
        ),
        content_type="application/json",
        headers=auth_headers(moein_init_data),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["saved_expense"]["group_id"] == "same-name-b"
    assert data["detail"]["group"]["id"] == "same-name-b"
    assert data["group_settlement"] == [["Cara", "Moein", 20.0]]


def test_telegram_expense_delete_requires_payer_and_recomputes_settlements(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    group = save_manual_group(mock_redis_service)
    moein_init_data = make_init_data({"id": 1001, "first_name": "Moein"})
    bob_init_data = make_init_data({"id": 1002, "first_name": "Bob"})
    expense = create_telegram_expense(client, moein_init_data, group["id"])

    forbidden_response = client.delete(
        f"/telegram/api/expenses/{expense['id']}/",
        headers=auth_headers(bob_init_data),
    )

    assert forbidden_response.status_code == 403
    assert mock_redis_service.get_expense(expense["id"]) is not None

    response = client.delete(
        f"/telegram/api/expenses/{expense['id']}/",
        headers=auth_headers(moein_init_data),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert mock_redis_service.get_expense(expense["id"]) is None
    assert data["group_settlement"] == []
    assert mock_redis_service.get_group_settlements(group["id"]) == []


def test_telegram_mark_settlement_paid_records_history_and_closes_balance(
    client, monkeypatch, mock_redis_service
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    group = save_manual_group(mock_redis_service)
    moein_init_data = make_init_data({"id": 1001, "first_name": "Moein"})
    bob_init_data = make_init_data({"id": 1002, "first_name": "Bob"})
    create_telegram_expense(client, moein_init_data, group["id"])

    response = client.post(
        f"/telegram/api/groups/{group['id']}/settlements/paid/",
        data=json.dumps({"debtor": "Bob", "creditor": "Moein", "amount": 10}),
        content_type="application/json",
        headers=auth_headers(bob_init_data),
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["payment"]["debtor"] == "Bob"
    assert data["payment"]["creditor"] == "Moein"
    assert data["payment"]["recorded_by"] == "Bob"
    assert data["group_settlement"] == []
    assert data["detail"]["payment_history"] == [data["payment"]]
    assert mock_redis_service.get_group_settlement_payments(group["id"]) == [
        data["payment"]
    ]
    assert mock_redis_service.get_group_settlements(group["id"]) == []

    duplicate_response = client.post(
        f"/telegram/api/groups/{group['id']}/settlements/paid/",
        data=json.dumps({"debtor": "Bob", "creditor": "Moein", "amount": 10}),
        content_type="application/json",
        headers=auth_headers(bob_init_data),
    )

    assert duplicate_response.status_code == 400
    assert duplicate_response.get_json()["error"] == "Settlement is not open"

    detail_response = client.get(
        f"/telegram/api/groups/{group['id']}/",
        headers=auth_headers(moein_init_data),
    )

    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["settlements"] == []
    assert detail["payment_history"][0]["amount"] == 10.0


def test_telegram_help_command_lists_commands(client, monkeypatch):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
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
                    "text": "/help",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert "/groups" in fake_bot.messages[0]["text"]
    assert "/settlements" in fake_bot.messages[0]["text"]


def test_telegram_groups_command_lists_private_groups(
    client, monkeypatch, mock_redis_service
):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://chipin.example")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)

    user = mock_redis_service.upsert_telegram_user(
        {"id": 1001, "first_name": "Moein"}
    )
    group = mock_redis_service.ensure_telegram_group(
        {"id": -2001, "type": "group", "title": "Calgary Trip"}
    )
    mock_redis_service.add_user_to_group(group["id"], user["name"])

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps(
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 1001, "type": "private", "first_name": "Moein"},
                    "from": {"id": 1001, "first_name": "Moein"},
                    "text": "/groups",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert "Your ChipIn groups:" in fake_bot.messages[0]["text"]
    assert "Calgary Trip" in fake_bot.messages[0]["text"]


def test_telegram_balance_command_reports_private_balance(
    client, monkeypatch, mock_redis_service
):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://chipin.example")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)

    user = mock_redis_service.upsert_telegram_user(
        {"id": 1001, "first_name": "Moein"}
    )
    group = mock_redis_service.ensure_telegram_group(
        {"id": -2001, "type": "group", "title": "Calgary Trip"}
    )
    mock_redis_service.add_user_to_group(group["id"], user["name"])
    mock_redis_service.add_user_to_group(group["id"], "Bob")
    mock_redis_service.save_group_settlements(
        [[1, 0, 10.0]],
        f"settlement-group:{group['id']}",
    )

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps(
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 1001, "type": "private", "first_name": "Moein"},
                    "from": {"id": 1001, "first_name": "Moein"},
                    "text": "/balance",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert "Your ChipIn balance:" in fake_bot.messages[0]["text"]
    assert "Bob owes you $10.00" in fake_bot.messages[0]["text"]


def test_telegram_balance_command_in_group_uses_private_handoff(
    client, monkeypatch
):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
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
                    "text": "/balance",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert fake_bot.messages[0]["chat_id"] == -2001
    assert "Open ChipIn privately" in fake_bot.messages[0]["text"]
    button = fake_bot.messages[0]["reply_markup"]["inline_keyboard"][0][0]
    assert button["url"].startswith("https://t.me/chipin_test_bot?start=group_")


def test_telegram_settlements_command_lists_private_settlements(
    client, monkeypatch, mock_redis_service
):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://chipin.example")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)

    user = mock_redis_service.upsert_telegram_user(
        {"id": 1001, "first_name": "Moein"}
    )
    group = mock_redis_service.ensure_telegram_group(
        {"id": -2001, "type": "group", "title": "Calgary Trip"}
    )
    mock_redis_service.add_user_to_group(group["id"], user["name"])
    mock_redis_service.add_user_to_group(group["id"], "Bob")
    mock_redis_service.save_group_settlements(
        [[1, 0, 10.0]],
        f"settlement-group:{group['id']}",
    )

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps(
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 1001, "type": "private", "first_name": "Moein"},
                    "from": {"id": 1001, "first_name": "Moein"},
                    "text": "/settlements",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert "Your open settlements:" in fake_bot.messages[0]["text"]
    assert "Calgary Trip" in fake_bot.messages[0]["text"]
    assert "Bob pays Moein $10.00" in fake_bot.messages[0]["text"]


def test_telegram_webhook_requires_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": 1}),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_telegram_webhook_rejects_missing_secret_configuration(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": 1}),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_telegram_webhook_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": 1}),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )

    assert response.status_code == 403


def test_telegram_webhook_accepts_correct_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": 1}),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200


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


def test_telegram_group_start_command_is_ignored(client, monkeypatch):
    import routes.telegram as telegram_module

    fake_bot = FakeBot()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secret")
    monkeypatch.setattr(telegram_module, "telegram_bot_client", fake_bot)

    response = client.post(
        "/telegram/webhook/",
        data=json.dumps(
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": -2001, "type": "group", "title": "Calgary Trip"},
                    "from": {"id": 1001, "first_name": "Moein"},
                    "text": "/start",
                },
            }
        ),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )

    assert response.status_code == 200
    assert fake_bot.messages == []


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
    mock_redis_service.add_user_to_group(group["id"], "Moein")
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


def test_telegram_private_start_payload_does_not_join_unlinked_user(
    client, monkeypatch, mock_redis_service
):
    import routes.telegram as telegram_module

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
    assert mock_redis_service.get_group(group["id"])["users"] == []
    assert "I could not find that ChipIn group" in fake_bot.messages[0]["text"]
