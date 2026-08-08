import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from uuid import uuid4

from playwright.sync_api import Page, expect


DEFAULT_BOT_TOKEN = "123456:e2e-test-token"


def test_telegram_expense_lifecycle(page: Page, app_url: str):
    suffix = uuid4().hex[:8]
    telegram_user = f"E2E Telegram {suffix}"
    partner = f"E2E Partner {suffix}"
    group_name = f"E2E Telegram Group {suffix}"
    expense_name = f"E2E Coffee {suffix}"
    updated_expense_name = f"E2E Brunch {suffix}"

    _post_json(
        page,
        f"{app_url}/users/",
        {"name": telegram_user, "email": f"telegram-{suffix}@example.com"},
    )
    _post_json(
        page,
        f"{app_url}/users/",
        {"name": partner, "email": f"partner-{suffix}@example.com"},
    )
    group = _post_json(
        page,
        f"{app_url}/groups/",
        {"name": group_name, "users": [telegram_user, partner]},
    )

    telegram_id = int(suffix, 16)
    init_data = _make_init_data(
        {
            "id": telegram_id,
            "first_name": "E2E Telegram",
            "last_name": suffix,
            "username": f"e2e_{suffix}",
        },
        os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_BOT_TOKEN),
    )
    _mock_telegram_web_app(page, init_data)

    page.goto(f"{app_url}/telegram/?group_id={group['id']}")

    expect(page.locator("#dashboard")).to_be_visible()
    expect(page.locator("#user-pill")).to_have_text(telegram_user)
    expect(page.locator("#groups-list")).to_contain_text(group_name)
    expect(page.locator("#group-detail")).to_be_visible()
    expect(page.locator("#group-detail h2")).to_have_text(group_name)

    detail = page.locator("#group-detail")
    detail.locator("#expense-name").fill(expense_name)
    detail.locator("#expense-amount").fill("24")
    detail.get_by_role("button", name="Add Expense").click()

    expect(page.locator("#toast")).to_have_text("Expense added")
    expense_row = detail.locator(".row", has_text=expense_name)
    expect(expense_row).to_contain_text("$24.00")
    expect(expense_row).to_contain_text(telegram_user)
    settlement_row = detail.locator(".row", has_text=f"{partner} to {telegram_user}")
    expect(settlement_row).to_contain_text("$12.00")

    expense_row.get_by_role("button", name="Edit").click()
    detail.locator("#expense-name").fill(updated_expense_name)
    detail.locator("#expense-amount").fill("30")
    detail.get_by_role("button", name="Save Expense").click()

    expect(page.locator("#toast")).to_have_text("Expense updated")
    updated_row = detail.locator(".row", has_text=updated_expense_name)
    expect(updated_row).to_contain_text("$30.00")
    expect(detail.locator(".row", has_text=f"{partner} to {telegram_user}")).to_contain_text(
        "$15.00"
    )

    page.once("dialog", lambda dialog: dialog.accept())
    updated_row.get_by_role("button", name="Delete").click()

    expect(page.locator("#toast")).to_have_text("Expense deleted")
    expect(detail.locator(".row", has_text=updated_expense_name)).to_have_count(0)
    expect(detail.locator(".list", has_text="No expenses")).to_be_visible()


def _post_json(page: Page, url: str, payload: dict):
    response = page.request.post(url, data=payload)
    assert response.status == 201, f"POST {url} failed: {response.status} {response.text()}"
    return response.json()


def _make_init_data(user: dict, bot_token: str):
    fields = {
        "auth_date": str(int(time.time())),
        "user": json.dumps(user, separators=(",", ":")),
    }
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


def _mock_telegram_web_app(page: Page, init_data: str):
    script = f"""
      window.Telegram = {{
        WebApp: {{
          initData: {json.dumps(init_data)},
          ready() {{}},
          expand() {{}},
          openTelegramLink() {{}},
          HapticFeedback: {{
            notificationOccurred() {{}},
            selectionChanged() {{}},
          }},
        }},
      }};
    """
    page.route(
        "https://telegram.org/js/telegram-web-app.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=script,
        ),
    )
